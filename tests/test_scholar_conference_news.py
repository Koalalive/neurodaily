from datetime import date
from unittest.mock import Mock, patch
import unittest

from neurodaily.config import DEFAULT_CONFIG
from neurodaily.models import Item
from neurodaily.search import compile_search
from neurodaily.sources import conferences, google_news


class ScholarConferenceNewsTests(unittest.TestCase):
    def test_author_tracking_combines_with_topic(self):
        plan = compile_search({"query": "depression", "authors": ["Nolan Williams"],
                               "author_mode": "intersect"})
        self.assertIn('AU="Nolan Williams"', plan.expression)
        paper = Item("Paper", authors=["Nolan Williams"], summary="depression")
        self.assertEqual(plan.match(paper).status, "match")
        other = Item("Paper", authors=["Someone Else"], summary="depression")
        self.assertNotEqual(plan.match(other).status, "match")

    def test_conference_calendar_has_upcoming_items(self):
        cfg = DEFAULT_CONFIG()
        cfg.sources["conferences"] = {"enabled": True, "max_results": 50}
        items = conferences.fetch(cfg)
        self.assertTrue(items)
        self.assertTrue(all(item.kind == "conference" for item in items))
        self.assertTrue(any(date.fromisoformat(item.date) >= date.today() for item in items))

    def test_google_news_chinese_source_parses_rss(self):
        response = Mock()
        response.content = b'''<rss version="2.0"><channel><title>Google News</title>
        <item><title>Brain news - Example</title><link>https://example.test/a</link>
        <pubDate>Mon, 23 Nov 2026 00:00:00 GMT</pubDate><description>Summary</description>
        <source url="https://example.test">Example</source></item></channel></rss>'''
        cfg = DEFAULT_CONFIG()
        cfg.sources["google_news_zh"] = {"enabled": True, "max_results": 10, "lookback_days": 30}
        with patch("neurodaily.sources.google_news.get", return_value=response):
            items = google_news.fetch(cfg)
        self.assertEqual(items[0].title, "Brain news")
        self.assertEqual(items[0].source, "google_news_zh")


if __name__ == "__main__":
    unittest.main()
