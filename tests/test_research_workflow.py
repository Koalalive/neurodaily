"""Offline regression tests through the settings and search entry points."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from neurodaily.config import Config, DEFAULT_CONFIG
from neurodaily.search import compile_search
from neurodaily.models import Item
from neurodaily.webapp import create_app


class ResearchWorkflowTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)
        self.path = str(self.folder / "config.json")
        self.config = DEFAULT_CONFIG()
        self.config.output.update(dir=str(self.folder), open_on_finish=False)
        self.config.scheduled.update(enabled=True, hour=13, minute=24)
        self.config.save(self.path)
        self.client = TestClient(create_app(self.path))

    def test_profile_round_trip_preserves_local_settings(self):
        self.config.sources["custom"] = {"type": "rss", "kind": "paper", "enabled": True,
                                         "url": "https://someone:private@example.test/feed?q=memory&token=secret",
                                         "headers": {"Authorization": "private"}}
        self.config.search = {"query": "#1 AND NOT AB=mouse", "sets": {"1": "TI=memory"}}
        self.config.save(self.path)
        response = self.client.get("/api/config/export")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["Content-Disposition"])
        exported = response.json()
        source = exported["config"]["sources"]["custom"]
        self.assertEqual(source["url"], "https://example.test/feed?q=memory")
        self.assertEqual(exported["config"]["search"], self.config.search)
        for key in ("scheduled", "output", "email", "webhooks"):
            self.assertNotIn(key, exported["config"])
        self.assertNotIn("private", json.dumps(exported))
        exported["config"]["profile"] = "oncology"
        preview = self.client.post("/api/config/import", json=exported).json()
        self.assertEqual(preview["summary"]["profile"], "oncology")
        self.assertEqual(Config.load(self.path).profile, self.config.profile)
        imported = self.client.post("/api/config/import?apply=true", json=exported)
        self.assertEqual(imported.status_code, 200, imported.text)
        applied = Config.load(self.path)
        self.assertEqual(applied.profile, "oncology")
        self.assertEqual(applied.scheduled, self.config.scheduled)
        self.assertEqual(applied.output, self.config.output)
        self.assertEqual(applied.sources["custom"]["url"], source["url"])

    def test_import_rejects_invalid_rule_without_a_write(self):
        original = Path(self.path).read_bytes()
        legacy = self.config.to_dict()
        legacy.update(version=1, search={"query": "#1", "sets": {"1": "#1"}})
        response = self.client.post("/api/config/import?apply=true", json=legacy)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Path(self.path).read_bytes(), original)
        legacy.pop("search")
        self.assertEqual(self.client.post("/api/config/import", json=legacy).status_code, 200)

    def test_preview_uses_custom_paper_sources_without_writing_history_or_reports(self):
        from neurodaily.sources import http

        self.config.sources = {key: {**opts, "enabled": False} for key, opts in self.config.sources.items()}
        self.config.sources["research_feed"] = {"type": "rss", "kind": "paper", "lookback_days": 1,
                                                "url": "https://example.test/feed"}
        self.config.search = {"query": 'TI=(memory NEAR/2 circuit) AND PY=2020'}
        rss = """<rss version="2.0"><channel><title>Test</title><item>
        <title>Memory and circuit</title><link>https://example.test/paper</link>
        <pubDate>Tue, 03 Mar 2020 08:00:00 GMT</pubDate></item></channel></rss>"""
        transport = httpx.MockTransport(lambda _: httpx.Response(200, text=rss))
        with httpx.Client(transport=transport) as network, patch.object(http, "_client", network):
            response = self.client.post("/api/search/preview", json=self.config.to_dict())
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        source, = result["sources"]
        self.assertEqual((source["source"], source["status"], source["count"]), ("research_feed", "ok", 1))
        self.assertEqual(result["unique_candidates"], {"match": 1, "unknown": 0, "miss": 0})
        self.assertEqual(list(self.folder.iterdir()), [Path(self.path)])

    def test_unsupported_branch_must_not_narrow_upstream_and_unknown_is_not_a_match(self):
        plan = compile_search({"query": "TI=memory OR MH=Neoplasms"})
        self.assertEqual(plan.remote_query("arxiv"), "")
        plan = compile_search({"query": "TI=memory AND NOT AB=mouse"})
        result = plan.match(Item(title="Memory circuits", url="https://example.test/paper", source="pubmed"))
        self.assertEqual(result.status, "unknown")
        self.assertEqual(result.missing_fields, ("AB",))

    def test_incremental_delivery_retries_only_the_failed_destination(self):
        from neurodaily.delivery import deliver_report
        from neurodaily.digest import DigestResult

        paper = Item(title="Fixture paper", url="https://example.test/paper", source="pubmed",
                     doi="10.1234/fixture")
        result = DigestResult(items=[paper], sections={"papers": [paper]}, health=[],
                              generated_at="2026-11-20T08:00:00", config_profile=self.config.profile,
                              config=self.config)
        hooks = {"feishu": "https://example.test/feishu", "wecom": "https://example.test/wecom"}
        acknowledgements = [{"feishu": "ok"}, {"wecom": "failed"}, {"wecom": "ok"}]
        with patch("neurodaily.history.db_path", return_value=str(self.folder / "history.db")), \
             patch("neurodaily.mailer.load_cfg", return_value={"enabled": False}), \
             patch("neurodaily.mailer.render_email", return_value=("", "", "")), \
             patch("neurodaily.mailer.save_last"), \
             patch("neurodaily.webhooks.load_cfg", return_value=hooks), \
             patch("neurodaily.webhooks.send_all", side_effect=acknowledgements) as send:
            self.assertEqual(deliver_report(result, "report.html"), {"feishu": "ok", "wecom": "failed"})
            self.assertEqual(deliver_report(result, "report.html"), {"wecom": "ok"})
            self.assertEqual(deliver_report(result, "report.html"), {})
        self.assertEqual(send.call_count, 3)

    def test_history_comparison_uses_cross_source_identifiers(self):
        from neurodaily.history import record_run, search_snapshot

        stamp = "2026-11-20T08:00:00"
        first = Item(title="Same paper from journal", url="https://example.test/paper", source="journal",
                     doi="10.1234/fixture")
        second = Item(title="Same paper from PubMed", url="https://pubmed.ncbi.nlm.nih.gov/123/",
                      source="pubmed", doi="https://doi.org/10.1234/fixture")
        new = Item(title="New paper", url="https://example.test/new", source="journal")
        profile = self.config.profile
        with patch("neurodaily.history.db_path", return_value=str(self.folder / "history.db")):
            ids = []
            for items in ([first], [second, new]):
                snapshot = search_snapshot(self.config, "manual", [], items, {"paper": 36})
                ids.append(record_run("fixture", profile, "completed", stamp, stamp, snapshot=snapshot))
            response = self.client.get("/api/history/compare", params={"before": ids[0], "after": ids[1]})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["in_both"], 1)
        self.assertEqual(result["removed"], [])
        self.assertEqual([row["title"] for row in result["added"]], ["New paper"])


if __name__ == "__main__":
    unittest.main()
