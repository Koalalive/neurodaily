import unittest

from neurodaily.demo import build_result
from neurodaily.desktop_page import render_workspace
from neurodaily.research_activity import report_activity
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
