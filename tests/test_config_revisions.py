from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from neurodaily import api_billing, config_revisions, history
from neurodaily.config import Config, DEFAULT_CONFIG, DEFAULT_DIRS, revision_for
from neurodaily.config_ops import apply_patch
from neurodaily.webapp import create_app


class ConfigRevisionTests(unittest.TestCase):
    def setUp(self):
        home = TemporaryDirectory()
        self.addCleanup(home.cleanup)
        directory = Path(home.name)
        self.path = str(directory / "config.json")
        self.config = DEFAULT_CONFIG()
        folders = patch.dict(DEFAULT_DIRS, {"output": str(directory / "output")})
        folders.start()
        self.addCleanup(folders.stop)
        self.client = TestClient(create_app(self.path))

    def test_migrates_existing_file_and_restores_a_revision_with_current_etag(self):
        Path(self.path).write_text(json.dumps(self.config.to_dict()), encoding="utf-8")
        legacy = self.client.get("/api/config/revisions").json()["revisions"]
        self.assertEqual(len(legacy), 1)
        initial = legacy[0]
        self.assertEqual(initial["origin"], "existing")
        current = self.client.get("/api/config")
        self.assertEqual(initial["revision"], current.headers["x-profile-revision"])
        self.assertEqual(initial["revision"], revision_for(self.config))

        draft = current.json()
        query = "TI=working"
        draft["search"]["query"] = query
        updated = self.client.post("/api/config", json=draft, headers={"If-Match": current.headers["etag"]})
        self.assertEqual(updated.status_code, 200)
        self.assertNotEqual(updated.headers["x-profile-revision"], initial["revision"])
        endpoint = f'/api/config/revisions/{initial["id"]}'
        reviewed = self.client.get(endpoint)
        self.assertIn(query, reviewed.json()["diff"])

        app_settings = Config.load(self.path)
        app_settings.output["dir"] = "/private/independent"
        app_settings.scheduled["hour"] = 21
        app_settings.save(self.path)
        failed = self.client.post(endpoint + "/restore", headers={"If-Match": reviewed.headers["etag"]})
        self.assertEqual(failed.status_code, 412)
        self.assertEqual(self.client.post(endpoint + "/restore").status_code, 428)
        latest = self.client.get(endpoint)
        restored = self.client.post(endpoint + "/restore", headers={"If-Match": latest.headers["etag"]})
        self.assertEqual(restored.status_code, 200)
        after = Config.load(self.path)
        self.assertEqual(after.search, self.config.search)
        self.assertEqual(after.output["dir"], "/private/independent")
        self.assertEqual(after.scheduled["hour"], 21)
        timeline = self.client.get("/api/config/revisions").json()["revisions"]
        self.assertEqual([row["origin"] for row in timeline], ["restore", "settings", "existing"])
        self.assertEqual(timeline[0]["provenance"], {"restored_revision": initial["id"]})
        self.assertEqual(timeline[0]["revision"], initial["revision"])
        self.assertNotEqual(timeline[0]["id"], initial["id"])

    def test_cli_patch_and_optimizer_provenance_share_revision_history(self):
        self.config.save(self.path)
        ok, errors, _ = apply_patch(self.path, {"search": {"query": "TI=memory"}})
        self.assertTrue(ok, errors)
        changed = Config.load(self.path)
        changed.search["query"] = "TI=consciousness"
        changed.save(self.path, origin="optimization", provenance={"optimization_run_id": "a" * 32,
                      "candidate_id": "selected", "snapshot_id": "b" * 64, "round": 2, "private_key": "ignored"})
        rows = self.client.get("/api/config/revisions").json()["revisions"]
        self.assertEqual([row["origin"] for row in rows], ["optimization", "cli_patch", "save"])
        self.assertEqual(rows[0]["provenance"]["snapshot_id"], "b" * 64)
        self.assertNotIn("private_key", rows[0]["provenance"])

    def test_an_interrupted_journal_commit_reconciles_the_committed_write(self):
        self.config.save(self.path)
        original = Path(self.path).read_bytes()
        changed = Config.load(self.path)
        changed.search["query"] = "TI=working"
        connection = config_revisions._connection
        count = 0

        @contextmanager
        def interrupt(fail_step):
            nonlocal count
            count += 1
            step = count
            with connection() as conn:
                yield conn
                if step == fail_step:
                    raise sqlite3.OperationalError("simulated commit failure")

        with patch.object(config_revisions, "_connection", side_effect=lambda: interrupt(1)):
            with self.assertRaises(sqlite3.OperationalError):
                changed.save(self.path)
        self.assertEqual(Path(self.path).read_bytes(), original)
        count = 0
        with patch.object(config_revisions, "_connection", side_effect=lambda: interrupt(2)):
            with self.assertLogs(config_revisions.LOG, level="WARNING"):
                changed.save(self.path, origin="optimization", provenance={"snapshot_id": "f" * 64})
        self.assertEqual(Config.load(self.path).search["query"], "TI=working")
        for _ in range(2):
            rows = self.client.get("/api/config/revisions").json()["revisions"]
            self.assertEqual([entry["origin"] for entry in rows], ["optimization", "save"])
            self.assertEqual(rows[0]["provenance"], {"snapshot_id": "f" * 64})

    def test_restore_keeps_current_local_source_options_for_the_same_endpoint(self):
        keys = {"headers": {"Authorization": "placeholder-local-only"}, "download_dir": "/private/local"}
        self.config.sources["personal"] = {"type": "rss", "url": "https://example.org/feed?token=older", "enabled": True}
        self.config.sources["changed_endpoint"] = {"type": "rss", "url": "https://old.example.org/rss?token=older", "enabled": True}
        self.config.save(self.path)
        first = self.client.get("/api/config/revisions").json()["revisions"][0]
        changed = Config.load(self.path)
        changed.sources["personal"].update({**keys, "url": "https://example.org/feed?token=current", "enabled": False})
        changed.sources["changed_endpoint"].update({**keys, "url": "https://new.example.org/rss?token=current"})
        changed.save(self.path)
        endpoint = f'/api/config/revisions/{first["id"]}'
        inspection = self.client.get(endpoint)
        self.assertNotIn("token=", inspection.json()["diff"])
        result = self.client.post(endpoint + "/restore", headers={"If-Match": inspection.headers["etag"]})
        self.assertEqual(result.status_code, 200, result.text)
        sources = Config.load(self.path).sources
        self.assertEqual(sources["personal"], {**keys, "type": "rss", "url": "https://example.org/feed?token=current", "enabled": True})
        self.assertEqual(sources["changed_endpoint"], {"type": "rss", "url": "https://old.example.org/rss", "enabled": True})

    def test_search_lint_uses_adapter_capability_and_known_record_metadata(self):
        self.config.search = {"query": "TI=working AND MH=Brain"}
        self.config.save(self.path)
        history.record_run("known", self.config.profile, "completed", "2026-11-25T00:00:00", "2026-11-25T01:00:00",
                           snapshot={"records": [
                               {"ids": ["doi:10.4321/known"], "kind": "paper", "title": "working memory", "source": "pubmed"},
                               {"ids": ["doi:10.4321/excluded"], "kind": "paper", "title": "visual perception", "source": "arxiv"},
                           ]})
        outcome = self.client.post("/api/config/lint", json=self.config.to_dict()).json()
        self.assertIn("MH", next(row for row in outcome["sources"] if row["source"] == "arxiv")["metadata_gaps"])
        self.assertIn("[mh:noexp]", next(row for row in outcome["sources"] if row["source"] == "pubmed")["query_preview"])
        self.assertEqual(outcome["known_records"]["missed"], 1)
        self.assertEqual(outcome["known_records"]["unknown"], 1)
        self.config.search["query"] = "TI=working AND ("
        self.assertEqual(self.client.post("/api/config/lint", json=self.config.to_dict()).status_code, 400)

    def test_billing_attributes_real_calls_to_optimizer_rounds(self):
        optimizer = "1" * 32
        revision = revision_for(self.config)
        usage = {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6}
        for round_number in (1, 2, 2, None):
            context = {"run_id": optimizer, "round": round_number, "profile_revision": revision} if round_number else None
            api_billing.record_call(purpose="search_optimization", base_url="https://example.org/v1", model="fixture",
                                    status="success", usage=usage, optimization_context=context)
        result = self.client.get("/api/billing", params={"optimization_run_id": optimizer}).json()
        self.assertEqual(result["total_calls"], 3)
        self.assertEqual([row["total_tokens"] for row in result["rounds"]], [6, 12])
        self.assertTrue(all(row["profile_revision"] == revision for row in result["calls"]))
        self.assertEqual(self.client.get("/api/billing").json()["total_calls"], 4)
