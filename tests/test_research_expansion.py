"""Offline checks for scoped discovery, evidence cards, and the map layout."""
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
import httpx

from neurodaily.config import DEFAULT_CONFIG
from neurodaily.demo import build_result
from neurodaily.digest import _filter_by_windows, preview_search
from neurodaily.models import Item
from neurodaily.records import merge_records
from neurodaily.render import refresh_saved_research_map, render_html
from neurodaily.research_events import link_records, track_trial_changes
from neurodaily.sources import crossref, http
from neurodaily.webapp import create_app


class ResearchExpansionTests(unittest.TestCase):
    def test_map_follows_summary_and_legacy_cloud_is_removed(self):
        result = build_result()
        result.ai_summary = "Fixture summary."
        result.geography = {"places": [], "unknown": []}
        soup = BeautifulSoup(render_html(result), "html.parser")
        self.assertEqual([node.get("id") for node in soup.main.find_all("section", recursive=False)][:2],
                         ["ai-summary", "research-activity"])
        payload = json.loads(soup.select_one("#nd-research-data").string)
        self.assertNotIn("keywords", payload)
        self.assertIsNone(soup.select_one(".ra-cloud"))

        payload["keywords"] = [{"term": "fixture"}]
        legacy = ('<main><section id="ai-summary">Summary</section><section id="papers">Papers</section>'
                  '<section id="research-activity"><div class="ra-cloud"></div>'
                  '<script type="application/json" id="nd-research-data">'
                  + json.dumps(payload) + '</script></section></main>')
        migrated = BeautifulSoup(refresh_saved_research_map(legacy, "zh"), "html.parser")
        self.assertEqual([section["id"] for section in migrated.main.find_all("section", recursive=False)],
                         ["ai-summary", "research-activity", "papers"])
        self.assertIsNone(migrated.select_one(".ra-cloud"))
        self.assertNotIn("keywords", json.loads(migrated.select_one("#nd-research-data").string))

        result.ai_summary = ""
        result.geography = None
        plain = BeautifulSoup(render_html(result), "html.parser")
        self.assertIsNone(plain.select_one("#research-activity"))

    def test_scoped_preview_classifies_news_policy_and_papers_independently(self):
        cfg = DEFAULT_CONFIG()
        cfg.sources = {key: {**opts, "enabled": False} for key, opts in cfg.sources.items()}
        cfg.policy_feeds = ["https://example.test/journal", "https://example.test/news", "https://example.test/policy"]
        cfg.sources["policy"].update(enabled=True, feed_kinds={
            cfg.policy_feeds[0]: "paper", cfg.policy_feeds[2]: "policy"
        })
        cfg.search = {"query": "TI=EEG", "sets": {"1": "TI=implant"},
                      "rules": {"news": "#1", "policy": "TI=rules"}}
        titles = {"journal": ["EEG fixture"], "news": ["New implant", "Another story"], "policy": ["Funding rules"]}
        stamp = datetime.now().strftime("%a, %d %b %Y 12:00:00 GMT")

        def reply(request):
            feed = request.url.path.split("/")[-1]
            entries = "".join(f"<item><title>{title}</title><link>https://example.test/{feed}/{i}</link>"
                              f"<pubDate>{stamp}</pubDate></item>" for i, title in enumerate(titles[feed]))
            return httpx.Response(200, text='<rss version="2.0"><channel><title>Fixture</title>'
                                  + entries + "</channel></rss>")

        with httpx.Client(transport=httpx.MockTransport(reply)) as client, patch.object(http, "_source_client", client):
            output = preview_search(cfg)
        self.assertEqual(output["unique_candidates"], {"match": 3, "unknown": 0, "miss": 1})
        self.assertEqual(set(output["by_kind"]), {"paper", "news", "policy"})
        self.assertEqual(output["sources"][0]["excluded"], 1)
        self.assertEqual(len(output["sources"]), 1, "Optional sources must stay disabled for old profiles")

    def test_late_index_keeps_original_publication_date(self):
        old = (date.today() - timedelta(days=60)).isoformat()
        paper = Item("Late record", date=old, extra={"source_discovered_at": date.today().isoformat()})
        self.assertEqual(_filter_by_windows([paper], {"paper": 24}), [paper])
        self.assertEqual(paper.date, old)
        paper.extra["source_discovered_at"] = old
        self.assertEqual(_filter_by_windows([paper], {"paper": 24}), [])

    def test_evidence_preserves_news_even_when_it_mentions_paper_doi(self):
        doi = "10.1234/fixture"
        paper = Item("Implant in the cortex for speech recovery", doi=doi, url=f"https://doi.org/{doi}")
        story = Item("University reports study", kind="news", doi=doi,
                     url="https://news.example.test/headline")
        close = Item("Implant in the cortex for speech recovery today", kind="policy",
                     url="https://news.example.test/notice")
        trial = Item("Speech study", kind="trial", url="https://clinicaltrials.gov/study/NCT01234567")
        other = Item("Trial update", kind="news", summary="See NCT01234567.",
                     url="https://news.example.test/trial")
        items = merge_records([paper, story, close, trial, other])
        self.assertEqual(len(items), 5)
        link_records(items)
        self.assertEqual(story.extra["related_evidence"][0]["method"], "verified")
        self.assertEqual(close.extra["related_evidence"][0]["method"], "possible")
        self.assertEqual(other.extra["related_evidence"][0]["kind"], "trial")

    def test_crossref_preserves_semantics_of_deposited_notices(self):
        cfg = DEFAULT_CONFIG()
        cfg.sources["crossref"] = {"enabled": True, "max_results": 1}
        paper = Item("Preprint", doi="10.1234/test")
        response = httpx.Response(200, json={"message": {
            "relation": {"is-preprint-of": [{"id-type": "doi", "id": "10.1234/published"}]},
            "update-to": [{"DOI": "10.1234/target", "type": "correction"}],
        }})
        notices = httpx.Response(200, json={"message": {"items": [
            {"DOI": "10.1234/retraction", "update-to": [{"DOI": paper.doi, "type": "retraction"}]}
        ]}})
        with patch.object(crossref, "get", side_effect=[response, notices]):
            self.assertEqual(crossref.enrich([paper], cfg), 1)
        self.assertEqual(paper.extra["related_versions"][0]["doi"], "10.1234/published")
        self.assertEqual(paper.extra["publication_updates"][0]["direction"], "notice_for")
        self.assertEqual(paper.extra["publication_updates"][1]["doi"], "10.1234/retraction")

    def test_trial_status_change_uses_previous_registry_observation(self):
        with TemporaryDirectory() as directory, patch.dict("neurodaily.history.DEFAULT_DIRS", {"output": directory}):
            previous = Item("Fixture", kind="trial", extra={"nct": "NCT01234567", "status": "RECRUITING",
                                                            "trial_dates": {"last_update_posted": "2026-11-20"}})
            track_trial_changes([previous], "neuro")
            current = Item("Fixture", kind="trial", extra={"nct": "NCT01234567", "status": "COMPLETED",
                                                           "trial_dates": {"last_update_posted": "2026-11-21"}})
            track_trial_changes([current], "neuro")
            track_trial_changes([current], "neuro")
            self.assertEqual(current.extra["trial_events"], [
                {"kind": "status_changed", "date": "2026-11-21", "from": "RECRUITING", "to": "COMPLETED"}
            ])

    def test_existing_tasks_can_be_indexed_and_searched_through_archive_api(self):
        with TemporaryDirectory() as directory:
            cfg = DEFAULT_CONFIG()
            config_path = Path(directory, "config.json")
            cfg.save(str(config_path))
            result = build_result(cfg)
            result.config_profile = cfg.profile
            result.history_id = 42
            app = create_app(str(config_path))
            client = TestClient(app)
            with patch("neurodaily.archive_search._db_path", return_value=Path(directory, "archive.db")), \
                    patch("neurodaily.task_runs.archived_run_ids", return_value=[42]), \
                    patch("neurodaily.task_runs.load_result", return_value=result):
                self.assertEqual(client.post("/api/archive/import", json={}).json(), {"reports": 1})
                response = client.get("/api/archive/search", params={"q": "thrombectomy", "kind": "trial"})
            self.assertEqual(response.status_code, 200)
            row, = response.json()["results"]
            self.assertEqual((row["kind"], row["run_id"]), ("trial", 42))
            self.assertIn("历史条目检索", client.get("/archive").text)
