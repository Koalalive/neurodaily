import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from neurodaily import demo, journal_metrics
from neurodaily.config import Config, DEFAULT_CONFIG, Journal
from neurodaily.models import Item
from neurodaily.records import merge_records
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

    def test_rejects_nonfinite_and_negative_impact_factors_but_reads_legacy_config(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            self.config.save(str(path))
            client = TestClient(create_app(str(path)), raise_server_exceptions=False)
            original = path.read_bytes()
            for field in ("impact_factor", "if"):
                for value in ("NaN", "Infinity", -1):
                    with self.subTest(field=field, value=value):
                        data = self.config.to_dict()
                        data["journals"] = [{"name": "A journal", field: value}]
                        self.assertEqual(client.post("/api/config", json=data).status_code, 400)
                        self.assertEqual(client.post("/api/config/import?apply=true", json=data).status_code, 400)
                        self.assertEqual(path.read_bytes(), original)
            data["journals"] = [{"name": "A journal", "impact_factor": float("nan"), "jcr": "Q3"}]
            path.write_text(json.dumps(data), encoding="utf-8")
            row = client.get("/api/config").json()["journals"][0]
            exported = client.get("/api/config/export").json()["config"]["journals"][0]
            self.assertIsNone(row["impact_factor"])
            self.assertEqual(row["jcr"], "Q3")
            self.assertEqual(row, exported)

    def test_conflicting_journal_abbreviation_does_not_apply_profile_badges(self):
        self.config.journals = [Journal("Alpha Clinical Journal", aliases=["J Clin Med"],
                                       issns=["2345-6789"], tags=["国产期刊"], impact_factor=1.1)]
        with patch.object(journal_metrics, "load_official", return_value={}), \
                patch.object(journal_metrics, "load_auto", return_value={}):
            other = Item("Unrelated paper", source="pubmed", extra={"journal": "Separate Clinical Journal",
                         "journal_abbreviation": "J Clin Med", "issn": "7890-1234"})
            self.assertIsNone(journal_metrics.for_item(other, self.config))
            exact = Item("Related paper", source="pubmed", extra={"journal": "Alpha Clinical Journal",
                         "issn": "7890-1234"})
            self.assertEqual(journal_metrics.for_item(exact, self.config)["if"], 1.1)
            self.config.journals.append(Journal("Separate Clinical Journal", issns=["7890-1234"], impact_factor=2.0))
            cache = ({"Alpha Clinical Journal": {"if": 1.1}}, {})
            self.assertIsNone(journal_metrics.for_item(exact, self.config, snapshot=cache))

    def test_deduplicated_papers_keep_matching_journal_identifiers(self):
        self.config.journals = [Journal("Demo Journal", issns=["2345-6789"], impact_factor=12.1)]
        complete = Item("Same title", url="https://example.org/epmc/42", doi="10.4321/fixture",
                        source="europe_pmc", extra={"journal": "Demo Journal", "issns": ["2345-6789"]})
        richer = Item("Same title", url="https://example.org/openalex/42", doi="10.4321/fixture",
                      source="openalex", summary="A substantially richer abstract.",
                      extra={"journal": "", "issns": []})
        record, = merge_records([complete, richer])
        with patch.object(journal_metrics, "load_official", return_value={}), \
                patch.object(journal_metrics, "load_auto", return_value={}):
            self.assertEqual(record.source, "openalex")
            self.assertEqual(journal_metrics.for_item(record, self.config)["if"], 12.1)

    def test_same_venue_merges_print_and_online_issns_but_rejects_a_conflicting_venue(self):
        records = [Item("Same title", doi="10.4321/fixture", source=source, summary=summary,
                        extra={"journal": name, "issns": [identifier]}) for source, summary, name, identifier in (
            ("openalex", "A substantially richer abstract.", "Demo Journal", "2345-6789"),
            ("europe_pmc", "", "Demo Journal", "9876-5432"),
            ("pubmed", "", "Other Journal", "4321-567X"),
        )]
        record, = merge_records(records)
        self.assertEqual(record.extra["journal"], "Demo Journal")
        self.assertEqual(set(record.extra["issns"]), {"2345-6789", "9876-5432"})

    def test_invalid_optional_metrics_file_keeps_full_report_and_profile_values(self):
        self.config.journals = [Journal("Neuron", impact_factor=12.1)]
        result = demo.build_result(self.config)
        with TemporaryDirectory() as tmp:
            official = Path(tmp) / "official.json"
            auto = Path(tmp) / "auto.json"
            official.write_text('[]', encoding="utf-8")
            auto.write_text('{"journals":{"Neuron":"invalid"}}', encoding="utf-8")
            with patch.object(journal_metrics, "OFFICIAL_PATH", str(official)), \
                    patch.object(journal_metrics, "AUTO_PATH", str(auto)):
                report = BeautifulSoup(render_html(result, self.config), "html.parser")
            self.assertIn("IF 12.1", report.select_one("#journals").get_text(" ", strip=True))

    def test_profile_writes_reject_a_stale_form_and_stale_import_preview(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            self.config.save(str(path))
            client = TestClient(create_app(str(path)))
            first = client.get("/api/config")
            stale = {"If-Match": first.headers["etag"]}
            older_form = first.json()
            profile_file = client.get("/api/config/export").json()
            preview = client.post("/api/config/import", json=profile_file)
            self.assertEqual(preview.headers["etag"], first.headers["etag"])
            updated = {**older_form, "search": {"query": "TI=memory"}}
            saved = client.post("/api/config", json=updated, headers=stale)
            self.assertEqual(saved.status_code, 200)
            self.assertNotEqual(saved.headers["etag"], first.headers["etag"])
            older_form["journals"][0]["tags"] = ["reviewed"]
            app_settings = {"format": "neurodaily.app-settings", "version": 1, "settings": {"output": {"dir": "old"}}}
            for route, payload in (("/api/config", older_form),
                                   ("/api/config/import?apply=true", profile_file),
                                   ("/api/app-settings/import", app_settings),
                                   ("/api/config/reset", None)):
                response = client.post(route, json=payload, headers=stale)
                self.assertEqual(response.status_code, 412, response.text)
                self.assertEqual(response.json()["code"], "configuration_changed")
            self.assertEqual(Config.load(str(path)).search["query"], "TI=memory")
