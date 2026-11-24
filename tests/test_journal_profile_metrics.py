from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from neurodaily import demo, journal_metrics
from neurodaily.config import Config, DEFAULT_CONFIG
from neurodaily.models import Item
from neurodaily.render import render_html
from neurodaily.webapp import create_app


class JournalProfileMetricsTests(unittest.TestCase):
    def setUp(self):
        self.config = DEFAULT_CONFIG()
        self.journal = {
            "name": "Example Journal",
            "aliases": ["Ex. Jour."],
            "issns": ["1234-567X"],
            "impact_factor": 0.0,
            "impact_factor_year": 2025,
            "jcr": "Q3",
            "jcr_year": 2024,
            "cas": "1区",
            "cas_year": 2025,
            "cas_top": True,
            "sci": True,
            "ssci": False,
            "tags": ["国产期刊", " 重点关注 ", "<script>test</script>", "国产期刊"],
            "metric_year": 2023,
        }

    def test_save_export_and_import_retain_fields(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            self.config.save(str(path))
            client = TestClient(create_app(str(path)))
            data = client.get("/api/config").json()
            data["journals"] = [self.journal]
            saved = client.post("/api/config", json=data)
            self.assertEqual(saved.status_code, 200, saved.text)
            loaded = Config.load(str(path)).journals[0].to_dict()
            self.assertEqual(loaded["tags"], ["国产期刊", "重点关注", "<script>test</script>"])
            for key in ("impact_factor_year", "jcr_year", "cas_year", "cas_top", "sci", "ssci", "metric_year"):
                self.assertEqual(loaded[key], self.journal[key])
            exported = client.get("/api/config/export").json()
            self.assertEqual(exported["config"]["journals"], [loaded])
            client.post("/api/config", json={**data, "journals": []})
            restored = client.post("/api/config/import?apply=true", json=exported)
            self.assertEqual(restored.status_code, 200, restored.text)
            self.assertEqual(Config.load(str(path)).journals[0].to_dict(), loaded)

    def test_real_journal_matching_and_dated_badges(self):
        config = Config.from_dict({**self.config.to_dict(), "journals": [self.journal]})
        fixtures = [
            Item("ISSN Example", source="pubmed", extra={"issn_linking": "1234567x"}),
            Item("Alias Example", source="europe_pmc", extra={"journal_abbreviation": "Ex Jour"}),
            Item("Different Journal", source="pubmed", extra={"journal": "Example Journal Today"}),
        ]
        with patch.object(journal_metrics, "load_official", return_value={}), \
                patch.object(journal_metrics, "load_auto", return_value={}):
            for item in fixtures:
                item.extra["metrics"] = journal_metrics.for_item(item, config)
            self.assertEqual(fixtures[0].extra["metrics"]["name"], "Example Journal")
            self.assertEqual(fixtures[0].extra["metrics"], fixtures[1].extra["metrics"])
            self.assertIsNone(fixtures[2].extra["metrics"])
            self.assertIsNone(journal_metrics.for_item(Item("Non-paper", kind="news",
                extra={"journal": "Example Journal"}), config))
            report = demo.build_result(config)
            report.items = fixtures
            report.sections = {"papers": fixtures}
            html = render_html(report, config)
        soup = BeautifulSoup(html, "html.parser")
        tags = [[tag.get_text(" ", strip=True) for tag in element.select(".meta .tag")]
                for element in soup.select("#papers .card")]
        self.assertEqual(len(tags), 3)
        expected = {"2025 IF 0.0", "2024 JCR Q3", "2025 中科院 1区 Top", "SCI",
                    "SSCI 未收录", "国产期刊", "重点关注", "<script>test</script>"}
        for item_tags in tags[:2]:
            self.assertTrue(expected.issubset(item_tags), item_tags)
        self.assertTrue(expected.isdisjoint(tags[2]))
        self.assertNotIn("<script>test</script>", html)
        self.assertIn("2025 中科院分区 1区 Top",
                      soup.select_one("#journals .journal").get_text(" ", strip=True))

    def test_shared_year_and_imported_years_remain_independent(self):
        row = {key: value for key, value in self.journal.items() if key not in
               {"impact_factor_year", "jcr", "jcr_year"}}
        config = Config.from_dict({**self.config.to_dict(), "journals": [row]})
        with patch.object(journal_metrics, "load_official",
                          return_value={"Example Journal": {"jcr": "Q4", "year": 2022}}), \
                patch.object(journal_metrics, "load_auto", return_value={}):
            metrics = journal_metrics.lookup("Example Journal", config)
        self.assertEqual(metrics["if_year"], 2023)
        self.assertEqual(metrics["jcr_year"], 2022)
        self.assertEqual(metrics["cas_year"], 2025)
