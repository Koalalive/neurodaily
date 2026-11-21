import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from threading import Event
from unittest import mock

from fastapi.testclient import TestClient

from neurodaily import demo, history, task_runs
from neurodaily.config import DEFAULT_CONFIG
from neurodaily.webapp import create_app


class SearchTaskTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.folder = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        self.cfg = DEFAULT_CONFIG()
        self.cfg.output.update(dir=str(self.folder), open_on_finish=False)
        self.config_path = self.cfg.save(str(self.folder / "config.json"))
        self.result = demo.build_result(self.cfg)
        self.result.config_profile = self.cfg.profile
        stack.enter_context(mock.patch.object(history, "db_path", return_value=str(self.folder / "history.db")))
        stack.enter_context(mock.patch.dict(os.environ, {"NEURODAILY_NO_OPEN": "1"}))
        stack.enter_context(mock.patch("neurodaily.journal_metrics.ensure_fresh", return_value=None))
        self.ai = stack.enter_context(mock.patch("neurodaily.ai_summary.generate", return_value=""))
        stack.enter_context(mock.patch("neurodaily.ai_summary.load_cfg", return_value={"model": "fixture"}))
        stack.enter_context(mock.patch("neurodaily.mailer.load_cfg", return_value={"enabled": False}))
        stack.enter_context(mock.patch("neurodaily.mailer.save_last"))
        self.hooks = stack.enter_context(mock.patch("neurodaily.webhooks.load_cfg", return_value={}))
        self.digest = stack.enter_context(mock.patch("neurodaily.webapp.run_digest", return_value=self.result))
        self.client = TestClient(create_app(self.config_path))

    def test_report_is_available_during_ai_and_exclusion_survives_app_restart(self):
        entered, release = Event(), Event()

        def summarize(_):
            entered.set()
            if not release.wait(5):
                raise AssertionError("test did not release the blocked model")
            return "Summary added after the initial report."

        self.ai.side_effect = summarize
        with ThreadPoolExecutor(max_workers=1) as executor:
            request = executor.submit(self.client.post, "/api/run?force=1")
            try:
                self.assertTrue(entered.wait(5))
                task = self.client.get("/api/search/status").json()["search"]
                self.assertEqual((task["status"], task["phase"]), ("running", "ai"))
                self.assertTrue(task["report_ready"])
                base = self.client.get(f"/history/{task['id']}/report")
                self.assertEqual(base.status_code, 200)
                self.assertNotIn("Summary added", base.text)
                with TestClient(create_app(self.config_path)) as second:
                    self.assertEqual(second.post("/api/run?force=1").status_code, 409)
                    self.assertEqual(second.get("/api/search/status").json()["search"]["status"], "running")
            finally:
                release.set()
            self.assertEqual(request.result(5).json()["task_id"], task["id"])
        with TestClient(create_app(self.config_path)) as restarted:
            self.assertIn("Summary added", restarted.get("/").text)
            status = restarted.get("/api/status").json()
            self.assertEqual(status["item_count"], len(self.result.items))
            self.assertEqual(status["search"]["report_revision"], 2)

    def test_recovery_keeps_ready_scheduled_report_and_marks_interrupted_work(self):
        due = datetime(2026, 11, 20, 8, 0)
        ready = task_runs.begin(self.cfg, "daily", due)
        report_path = self.folder / "completed.html"
        report_path.write_text("<html>Previous real report</html>", encoding="utf-8")
        ready.update(report_ready=True, report_file=str(report_path), item_count=len(self.result.items))
        task_runs.stage(ready, "delivery", "running")
        task_runs.save(ready, result=self.result)
        interrupted = task_runs.begin(self.cfg, "manual", None)
        with TestClient(create_app(self.config_path)) as restarted:
            self.assertIn("Previous real report", restarted.get("/").text)
            self.assertEqual(restarted.get("/api/search/status").json()["search"]["status"], "interrupted")
            task = restarted.get(f"/api/history/{ready['id']}").json()["task"]
            self.assertEqual(task["stages"]["delivery"]["status"], "interrupted")
            self.assertEqual(task["status"], "completed")
            self.assertEqual(history.desktop_schedule_result(self.cfg.profile, due)["status"], "completed")
            self.assertEqual(history.get_run(interrupted["id"])["status"], "interrupted")

    def test_delivery_retry_uses_checkpoint_after_restart_and_sends_to_one_target(self):
        self.hooks.return_value = {"feishu": "https://example.test/one", "wecom": "https://example.test/two"}

        def initial(_result, config):
            channel = "wecom" if "wecom" in config else "feishu"
            return {channel: "ok" if channel == "feishu" else "rejected"}

        with mock.patch("neurodaily.webhooks.send_all", side_effect=initial):
            task_id = self.client.post("/api/run?force=1").json()["task_id"]
        with TestClient(create_app(self.config_path)) as restarted:
            task = restarted.get(f"/api/history/{task_id}").json()
            failure = next(row for row in task["receipts"] if row["status"] == "failed")
            self.assertEqual(task["task"]["stages"]["delivery"]["status"], "partial")
            self.assertNotIn("checkpoint", task)
            self.assertIn("重试", restarted.get(f"/history/{task_id}").text)
            # Advancing to a new output directory must not change old report paths.
            new_dir = self.folder / "new-output"
            new_dir.mkdir()
            self.cfg.output["dir"] = str(new_dir)
            self.cfg.save(self.config_path)
            with mock.patch("neurodaily.webhooks.send_all", return_value={"wecom": "ok"}) as sender:
                url = f"/api/history/{task_id}/delivery/{failure['destination']}/retry"
                response = restarted.post(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual((response.json()["status"], response.json()["attempts"]), ("accepted", 2))
                sender.assert_called_once()
                self.assertEqual(sender.call_args.args[0].generated_at, self.result.generated_at)
                self.assertNotIn("feishu", sender.call_args.args[1])
                self.assertEqual(restarted.post(url).status_code, 409)
            self.assertEqual(restarted.get(f"/history/{task_id}/report").status_code, 200)
        self.digest.assert_called_once()

    def test_fixed_report_filename_keeps_old_report(self):
        self.cfg.output["filename_format"] = "saved.html"
        self.cfg.save(self.config_path)
        first = self.client.post("/api/run?force=1").json()["task_id"]
        self.digest.return_value = demo.build_result(self.cfg)
        self.digest.return_value.config_profile = self.cfg.profile
        second = self.client.post("/api/run?force=1").json()["task_id"]
        original = self.folder / history.get_run(first)["report_path"]
        latest = self.folder / history.get_run(second)["report_path"]
        self.assertNotEqual(original, latest)
        self.assertEqual(self.client.get(f"/history/{first}/report").status_code, 200)
        self.assertEqual(self.client.get("/report/latest").text, latest.read_text(encoding="utf-8"))

    def test_source_progress_has_initial_and_finished_states(self):
        from neurodaily.digest import _fetch_sources
        from neurodaily.models import Item
        from neurodaily.search import compile_search

        def fixture(config, logger=None):
            return [Item(title="Fixture", source="fixture", date=datetime.now().date().isoformat())]

        events = []
        with mock.patch("neurodaily.digest.registry_for", return_value={"fixture": fixture}):
            _fetch_sources(self.cfg, compile_search({}, []), {"paper": 24}, 24, progress=events.append)
        self.assertEqual(events[0], {"fixture": {"status": "pending"}})
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1]["fixture"]["fetched"], 1)
        self.assertIn(events[1]["fixture"]["status"], ("ok", "empty"))
