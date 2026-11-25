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

from neurodaily import delivery_receipts, demo, history, task_runs
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

        def summarize(_result, *_args, **_kwargs):
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
                self.assertEqual(task["report_revision"], 1)
                listing = self.client.get("/api/ui/reports?after=0").json()["reports"]
                self.assertEqual(listing[0]["report_revision"], 1)
                initial = self.client.get(f"/history/{task['id']}/report")
                self.assertEqual(initial.status_code, 200)
                self.assertNotIn("Summary added", initial.text)
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
        ready.pop("workflow")  # A pre-upgrade task remains readable but cannot be resumed.
        report_path = self.folder / "completed.html"
        report_path.write_text("<html>Previous real report</html>", encoding="utf-8")
        ready.update(report_ready=True, report_file=str(report_path), item_count=len(self.result.items))
        task_runs.stage(ready, "delivery", "running")
        task_runs.save(ready, result=self.result)
        task_id = str(ready["id"])
        delivery_receipts.prepare(task_id, self.cfg.profile,
                                  [("first", "wecom", "wecom"), ("second", "feishu", "feishu")])
        self.assertTrue(delivery_receipts.transition(task_id, self.cfg.profile, "first", "pending", "sending"))
        interrupted = task_runs.begin(self.cfg, "manual", None)
        with history.delivery_lease(self.cfg.profile, "first"), TestClient(create_app(self.config_path)) as restarted:
            self.assertIn("Previous real report", restarted.get("/").text)
            self.assertEqual(restarted.get("/api/search/status").json()["search"]["status"], "interrupted")
            detail = restarted.get(f"/api/history/{ready['id']}").json()
            task = detail["task"]
            self.assertEqual(task["stages"]["delivery"]["status"], "interrupted")
            self.assertEqual(task["status"], "completed")
            self.assertEqual({row["channel"]: row["status"] for row in detail["receipts"]},
                             {"wecom": "unknown", "feishu": "failed"})
            self.assertEqual(history.desktop_schedule_result(self.cfg.profile, due)["status"], "completed")
            self.assertEqual(history.get_run(interrupted["id"])["status"], "interrupted")

    def test_resumes_same_task_and_fetches_only_unfinished_sources(self):
        from neurodaily.digest import run
        from neurodaily.models import Item

        first = Item(title="First source already finished", source="fixture_one")
        second = Item(title="Second source finished after restart", source="fixture_two")
        attempt = task_runs.begin(self.cfg, "manual", None, force=True)
        run_id = attempt["id"]
        task_runs.save_source(run_id, "primary", first.source, [first], {
            "source": first.source, "status": "ok", "ok": True, "count": 1,
            "fetched": 1, "ms": 1, "lookback_days": 4,
        })
        self.digest.side_effect = run
        restored = mock.Mock(side_effect=AssertionError("completed source requested twice"))
        unfinished = mock.Mock(return_value=[second])
        with mock.patch("neurodaily.digest.registry_for", return_value={first.source: restored, second.source: unfinished}):
            with TestClient(create_app(self.config_path)) as restarted:
                self.assertIn("继续检索", restarted.get(f"/history/{run_id}").text)
                self.assertEqual(restarted.post(f"/api/run/{run_id}/resume").json()["task_id"], run_id)
                details = restarted.get(f"/api/history/{run_id}").json()["task"]
                self.assertEqual(details["status"], "completed")
                self.assertEqual(details["item_count"], 2)
                self.assertEqual(restarted.post(f"/api/run/{run_id}/resume").status_code, 409)
        restored.assert_not_called()
        unfinished.assert_called_once()
        self.assertEqual(history.count_runs(self.cfg.profile), 1)

    def test_resume_refuses_changed_search_inputs(self):
        attempt = task_runs.begin(self.cfg, "manual", None, force=True)
        self.cfg.global_keywords = [*self.cfg.global_keywords, "new-keyword"]
        self.cfg.save(self.config_path)
        with TestClient(create_app(self.config_path)) as restarted:
            response = restarted.post(f"/api/run/{attempt['id']}/resume")
            self.assertEqual(response.status_code, 409)
            self.assertIn("配置已更改", response.json()["error"])
        self.assertEqual(history.get_run(attempt["id"])["status"], "interrupted")
        self.digest.assert_not_called()

    def test_todays_scheduled_slot_restarts_with_new_search_inputs(self):
        due = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.cfg.scheduled.update(enabled=True, hour=0, minute=0)
        attempt = task_runs.begin(self.cfg, "daily", due, force=True)
        self.cfg.global_keywords = [*self.cfg.global_keywords, "changed-after-restart"]
        self.cfg.save(self.config_path)
        finished = Event()
        outcomes = []

        def scheduler(_stop, load, start):
            try:
                outcomes.append(start(load(), due))
            finally:
                finished.set()

        with mock.patch("neurodaily.webapp.run_schedule", side_effect=scheduler):
            with TestClient(create_app(self.config_path, desktop=True)) as restarted:
                self.assertTrue(finished.wait(5))
                self.assertEqual(outcomes, [True])
                self.assertEqual(history.count_runs(self.cfg.profile), 2)
                self.assertEqual(history.get_run(attempt["id"])["status"], "superseded")
                self.assertEqual(restarted.get("/api/launchd/status").json()["last_run"]["status"], "completed")

    def test_resumed_sources_and_report_keep_the_original_search_window(self):
        from neurodaily.digest import run
        from neurodaily.models import Item

        class NextDay(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 24, 8)

        self.cfg.windows["manual_paper_hours"] = 24
        self.cfg.save(self.config_path)
        attempt = task_runs.begin(self.cfg, "manual", None, force=True)
        attempt["started_at"] = "2026-11-23T08:00:00"
        attempt["retrieval_anchor"] = "2026-11-23T08:00:00+08:00"
        task_runs.save(attempt)
        first = Item("First source", source="fixture_one", url="https://example.test/a",
                     date="2026-11-22T18:00:00")
        second = Item("Second source", source="fixture_two", url="https://example.test/b",
                      date="2026-11-22T18:00:00")
        task_runs.save_source(attempt["id"], "primary", first.source, [first], {
            "source": first.source, "status": "ok", "ok": True, "count": 1,
            "fetched": 1, "ms": 1, "lookback_days": 2,
        })
        self.digest.side_effect = run
        with (mock.patch("neurodaily.digest.datetime", NextDay),
              mock.patch("neurodaily.digest.registry_for", return_value={
                  first.source: mock.Mock(side_effect=AssertionError("cached source was re-fetched")),
                  second.source: mock.Mock(return_value=[second]),
              }), TestClient(create_app(self.config_path)) as restarted):
            self.assertEqual(restarted.post(f"/api/run/{attempt['id']}/resume").status_code, 200)
        result = task_runs.load_result(attempt["id"])
        self.assertEqual({item.source for item in result.items}, {first.source, second.source})
        self.assertEqual(result.search_window["start"], "2026-11-22 08:00")
        self.assertEqual(result.search_window["end"], "2026-11-23 08:00")

    def test_switching_profile_does_not_show_another_profiles_latest_report(self):
        self.assertEqual(self.client.post("/api/run?force=1").status_code, 200)
        history_name = history.list_runs(profile=self.cfg.profile)[0]["report_path"]
        self.assertTrue((self.folder / history_name).is_file())
        self.cfg.profile = "empty-profile"
        self.cfg.save(self.config_path)
        restarted = TestClient(create_app(self.config_path))
        self.assertEqual(restarted.get("/report/latest").status_code, 404)
        self.assertIn("尚无已保存的日报", restarted.get("/?ui=1").text)
        self.assertEqual(restarted.get("/api/ui/reports?after=0").json()["reports"], [])

    def test_journal_priority_remains_in_the_rendered_papers_section(self):
        from neurodaily.digest import run
        from neurodaily.models import Item

        self.cfg.search = {"sort": "journal"}
        ordinary = Item("Newest ordinary paper", date="2026-11-23T09:00", source="fixture")
        top = Item("Older top journal paper", date="2026-11-22T09:00", source="fixture", tags=["top-journal"])
        with (mock.patch("neurodaily.digest.registry_for", return_value={"fixture": mock.Mock(return_value=[ordinary, top])}),
              mock.patch("neurodaily.digest._filter_by_windows", side_effect=lambda items, *_args, **_kw: items)):
            result = run(self.cfg, record=False, force=True)
        self.assertEqual([item.title for item in result.sections["papers"]], [top.title, ordinary.title])

    def test_scheduled_resume_preserves_confirmed_and_uncertain_receipts(self):
        from neurodaily.delivery import _destination

        due = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        attempt = task_runs.begin(self.cfg, "daily", due, force=True)
        run_id = attempt["id"]
        report_path = self.folder / "planned.html"
        report_path.write_text("<html>Existing complete report</html>", encoding="utf-8")
        attempt.update(report_ready=True, report_revision=2, report_file=str(report_path),
                       item_count=len(self.result.items))
        for stage in ("search", "report", "metrics", "ai", "geolocation", "topics", "index"):
            task_runs.stage(attempt, stage, "completed")
        task_runs.stage(attempt, "delivery", "running")
        task_runs.save(attempt, result=self.result)
        address = "already-sent@example.test"
        self.hooks.return_value = {"feishu": "https://example.test/one", "wecom": "https://example.test/two"}
        sent = _destination("email", address)
        uncertain = _destination("feishu", self.hooks.return_value["feishu"])
        pending = _destination("wecom", self.hooks.return_value["wecom"])
        task_id = str(run_id)
        profile = self.cfg.profile
        delivery_receipts.prepare(task_id, profile, [(sent, "email", "email 1"),
                                                     (uncertain, "feishu", "feishu"),
                                                     (pending, "wecom", "wecom")])
        delivery_receipts.transition(task_id, profile, sent, "pending", "sending")
        delivery_receipts.transition(task_id, profile, sent, "sending", "accepted")
        delivery_receipts.transition(task_id, profile, uncertain, "pending", "sending")
        finished = Event()

        def run_schedule_once(_stop, load, start):
            try:
                start(load(), due)
            finally:
                finished.set()

        with (mock.patch("neurodaily.webapp.run_schedule", side_effect=run_schedule_once),
              mock.patch("neurodaily.mailer.load_cfg", return_value={"enabled": True, "to": [address]}),
              mock.patch("neurodaily.delivery._send_email") as mail,
              mock.patch("neurodaily.webhooks.send_all", return_value={"wecom": "ok"}) as sender,
              TestClient(create_app(self.config_path, desktop=True)) as restarted):
            self.assertTrue(finished.wait(5))
            detail = restarted.get(f"/api/history/{run_id}").json()
            self.assertEqual(detail["status"], "completed")
            self.assertEqual(detail["task"]["stages"]["delivery"]["status"], "partial")
            self.assertEqual({row["channel"]: row["status"] for row in detail["receipts"]},
                             {"email": "accepted", "feishu": "unknown", "wecom": "accepted"})
            mail.assert_not_called()
            sender.assert_called_once()
            self.assertNotIn("feishu", sender.call_args.args[1])
        self.digest.assert_not_called()
        self.ai.assert_not_called()
        self.assertEqual(history.count_runs(profile), 1)
        self.assertEqual(history.desktop_schedule_result(profile, due)["status"], "completed")

    def test_cancel_running_task_before_report_or_delivery(self):
        entered, release = Event(), Event()

        def search(*_args, **_kwargs):
            entered.set()
            if not release.wait(5):
                raise AssertionError("test did not release the active search")
            return self.result

        self.digest.side_effect = search
        with ThreadPoolExecutor(max_workers=1) as executor:
            request = executor.submit(self.client.post, "/api/run?force=1")
            try:
                self.assertTrue(entered.wait(5))
                run_id = self.client.get("/api/search/status").json()["search"]["id"]
                self.assertEqual(self.client.post(f"/api/run/{run_id}/cancel").status_code, 202)
            finally:
                release.set()
            self.assertEqual(request.result(5).status_code, 200)
        detail = self.client.get(f"/api/history/{run_id}").json()
        self.assertEqual(detail["status"], "cancelled")
        self.assertFalse(detail["task"]["report_ready"])
        self.assertEqual(detail["receipts"], [])
        self.assertEqual(self.client.post(f"/api/run/{run_id}/cancel").status_code, 409)

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
        response = self.client.get("/report/latest")
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'name="nd-report-run-id" content="{second}"', response.text)
        self.assertNotIn(f'name="nd-report-run-id" content="{first}"', response.text)

    def test_workspace_persists_language_and_opens_only_new_ready_reports(self):
        self.assertEqual(self.client.get("/api/ui/preferences").json(), {"language": "zh"})
        self.assertIn("尚无已保存的日报", self.client.get("/?ui=1").text)
        self.assertEqual(self.client.post("/api/ui/preferences", json={"language": "fr"}).status_code, 400)
        self.assertEqual(self.client.post("/api/ui/preferences", json={"language": "ru"}).status_code, 200)
        with TestClient(create_app(self.config_path)) as restarted:
            self.assertEqual(restarted.get("/api/ui/preferences").json(), {"language": "ru"})
            self.assertIn('<html lang="ru">', restarted.get("/desktop").text)
            self.assertIn('let scanAfter = 0', restarted.get("/desktop").text)
            new = restarted.post("/api/run?force=1").json()["task_id"]
            self.assertEqual(restarted.get("/api/ui/reports?after=0").json()["reports"],
                             [{"id": new, "status": "completed", "report_ready": True, "report_revision": 2}])
            self.assertIn(f'let scanAfter = {new}', restarted.get("/desktop").text)
            self.assertEqual(restarted.get(f"/api/ui/reports?after={new}").json(), {"reports": []})
            self.assertIn('lang="ru"', restarted.get(f"/history/{new}/report?ui=1").text)

    def test_transient_source_failure_is_retried_three_rounds(self):
        from neurodaily.digest import _fetch_sources
        from neurodaily.models import Item
        from neurodaily.search import compile_search

        calls = []

        def fixture(config, logger=None):
            calls.append(1)
            if len(calls) <= 3:
                raise TimeoutError("temporary source outage")
            return [Item(title="Recovered", source="fixture", date=datetime.now().date().isoformat())]

        with mock.patch("neurodaily.digest.registry_for", return_value={"fixture": fixture}):
            items, health = _fetch_sources(self.cfg, compile_search({}, []), {"paper": 24}, 24)
        self.assertEqual(len(calls), 4)
        self.assertEqual(items[0].title, "Recovered")
        self.assertEqual(health[0]["status"], "ok")

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
