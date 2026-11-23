import unittest
from unittest.mock import Mock

from neurodaily.config import DEFAULT_CONFIG
from neurodaily.demo import build_result
from neurodaily.desktop_page import render_workspace
from neurodaily.geography import locate_items
from neurodaily.models import Item
from neurodaily.research_activity import report_activity
from neurodaily.sources import conferences
from neurodaily.task_page import render_task


class DesktopTabsTests(unittest.TestCase):
    def test_tabs_use_date_report_titles_and_sort(self):
        html = render_workspace("zh", 0, "2026-11-22")
        self.assertIn("function sortTabs()", html)
        self.assertIn("return word('report')", html)
        self.assertNotIn("#${run[1]}", html)
        self.assertIn("html,body{height:100%;overflow:hidden}", html)

    def test_task_page_exposes_report_date(self):
        task = {"id": 10, "status": "running", "stages": {}, "sources": {},
                "scheduled_for": None, "started_at": "2026-11-22T09:00:00",
                "finished_at": "", "error": "", "report_ready": False,
                "profile": "neuro", "item_count": 0}
        html = render_task(task, [], "")
        self.assertIn("name='nd-report-date' content='2026-11-22'", html)


class ResearchMapContractTests(unittest.TestCase):
    def test_curated_conferences_use_metadata_without_model_calls(self):
        items = {item.title: item for item in conferences.fetch(DEFAULT_CONFIG())}
        chat = Mock()
        points = locate_items(items, chat=chat)["places"]
        self.assertTrue(items)
        self.assertEqual({point["id"] for point in points}, set(items))
        self.assertEqual({point["role"] for point in points}, {"conference_venue"})
        self.assertEqual({point["precision"] for point in points}, {"city"})
        chat.assert_not_called()

    def test_includes_conferences_and_funding_without_promoting_regulatory_releases(self):
        result = build_result()
        result.items = [
            Item("Curated venue", kind="conference"),
            Item("RSS financing item", kind="funding"),
            Item("Alpha closes Series A round", kind="news"),
            Item("FDA approval", kind="funding", source="policy",
                 extra={"source_url": "https://www.fda.gov/press/rss.xml"}),
            Item("Medical device", kind="device"),
        ]
        result.geography = {"places": [], "unknown": []}
        activity = report_activity(result, lambda url: url or "")
        self.assertEqual({record["title"]: record["kind"] for record in activity["records"].values()}, {
            "Curated venue": "conference", "RSS financing item": "funding",
            "Alpha closes Series A round": "funding", "FDA approval": "policy",
        })
        self.assertEqual(set(activity["unknown"]), set(activity["records"]))
        self.assertEqual(result.items[2].kind, "news")

    def test_map_disabled_without_llm_geography(self):
        result = build_result()
        result.geography = None
        activity = report_activity(result, lambda url: url or "")
        self.assertFalse(activity["enabled"])

    def test_map_uses_journal_and_never_pubmed_for_papers(self):
        result = build_result()
        result.geography = {"places": [], "unknown": []}
        paper = next(item for item in result.items if item.kind == "paper")
        paper.extra["journal"] = "Fixture Journal"
        activity = report_activity(result, lambda url: url or "")
        self.assertTrue(activity["enabled"])
        record = activity["records"][next(iter(activity["records"]))]
        self.assertIn("journal", record)
        self.assertNotEqual(record.get("venue"), "pubmed")
