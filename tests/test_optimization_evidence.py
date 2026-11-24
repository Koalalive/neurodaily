from datetime import date
from unittest import TestCase
from unittest.mock import patch

from neurodaily.config import Config, DEFAULT_CONFIG, OPTIONAL_SOURCES
from neurodaily.optimization_evidence import capture_evidence, evaluate_candidate, public_evidence, verify_candidate
from neurodaily.presets import research_presets
from neurodaily.schema import validate
from neurodaily.sources import BUILTIN, conferences, fda


def _one_source() -> Config:
    config = DEFAULT_CONFIG()
    config.sources = {name: {"enabled": name == "pubmed"} for name in set(BUILTIN) | set(OPTIONAL_SOURCES)}
    config.journals = []
    config.search = {"query": "TI=attention"}
    return config


def _paper(name, identifier, day):
    return {"title": name, "source": "pubmed", "kind": "paper", "date": day, "url": "",
            "extra": {"pmid": identifier}}


_ROWS = [_paper("Attention", "1", "2026-11-08"), _paper("Memory", "2", "2026-11-09"),
         _paper("Attention", "3", "2026-11-20"), _paper("Memory", "4", "2026-11-21")]
_LABELS = [{"ids": [f"pmid:{i}"], "relevant": True} for i in range(1, 5)]


def _fetch(config, name, start, end, *, broad=False):
    rows = [row for row in _ROWS if start <= row["date"] <= end]
    if not broad and config.search["query"] == "TI=attention":
        rows = [row for row in rows if row["title"] == "Attention"]
    return rows, {"status": "ok", "coverage": "full", "captured": len(rows), "request_count": 1}


class OptimizationEvidenceTests(TestCase):
    @patch("neurodaily.optimization_evidence._fetch", side_effect=_fetch)
    def test_shared_capture_retains_citations_and_disjoint_evaluation_windows(self, mocked_fetch):
        baseline = _one_source()
        candidate = _one_source()
        candidate.search = {"query": "TI=attention OR TI=memory"}
        snapshot = capture_evidence(baseline, today=date(2026, 11, 24), max_sources=1,
                                    extra_sources=["pubmed"])
        evidence = public_evidence(snapshot)
        self.assertNotIn("captures", evidence)
        self.assertEqual(evidence["sources"][0]["status"], "published_items_filtered_by_rules")
        self.assertEqual(evidence["sources"][0]["examples"][1]["status"], "miss")
        self.assertEqual(evidence["sources"][0]["citation"], "https://pubmed.ncbi.nlm.nih.gov/")

        development = evaluate_candidate(snapshot, baseline, candidate, labels=_LABELS)
        holdout = verify_candidate(snapshot, baseline, candidate, labels=_LABELS)
        self.assertTrue(development["eligible"])
        self.assertTrue(holdout["eligible"])
        self.assertEqual(development["added"][0]["ids"], ["pmid:2"])
        self.assertEqual(holdout["added"][0]["ids"], ["pmid:4"])
        self.assertEqual(development["delta"]["recall"], 0.5)
        self.assertEqual(holdout["delta"]["recall"], 0.5)
        self.assertTrue(holdout["details"]["native_probes"])
        self.assertEqual(mocked_fetch.call_count, 4)

    @patch("neurodaily.optimization_evidence._fetch", side_effect=_fetch)
    def test_unjudged_changes_and_unapproved_urls_cannot_enter_review(self, mocked_fetch):
        baseline = _one_source()
        candidate = _one_source()
        candidate.search = {"query": "TI=attention OR TI=memory"}
        candidate.sources["attacker"] = {"enabled": True, "type": "rss", "url": "https://example.test"}
        snapshot = capture_evidence(baseline, today=date(2026, 11, 24), max_sources=1,
                                    extra_sources=["pubmed"])
        result = verify_candidate(snapshot, baseline, candidate)
        self.assertFalse(result["eligible"])
        self.assertIn("source_endpoint_not_preapproved", result["reasons"])
        self.assertIn("no_positive_relevance_judgment_in_window", result["reasons"])
        self.assertEqual(mocked_fetch.call_count, 2)

    @patch("neurodaily.optimization_evidence._fetch", side_effect=_fetch)
    def test_native_holdout_must_reproduce_candidate_gain(self, mocked_fetch):
        baseline = _one_source()
        candidate = _one_source()
        candidate.search = {"query": "TI=attention OR TI=memory"}
        snapshot = capture_evidence(baseline, today=date(2026, 11, 24), max_sources=1,
                                    extra_sources=["pubmed"])
        mocked_fetch.side_effect = lambda _config, name, start, end, broad=False: _fetch(
            baseline, name, start, end, broad=broad)
        result = verify_candidate(snapshot, baseline, candidate, labels=_LABELS)
        self.assertFalse(result["eligible"])
        self.assertIn("native_trial_did_not_reproduce_added_records", result["reasons"])

    def test_presets_validate_and_use_distinct_conference_profiles(self):
        expected = {"neuro": "SfN Neuroscience 2027", "oncology": "AACR Annual Meeting 2027",
                    "critical-care": "SCCM Critical Care Congress 2027"}
        for preset in research_presets():
            data = preset["config"]
            self.assertEqual(validate(data), [])
            config = Config.from_dict(data)
            self.assertTrue(config.source_opts("europe_pmc")["enabled"])
            self.assertIn("trial", config.search["rules"])
            with patch("neurodaily.sources.conferences.date", wraps=date) as clock:
                clock.today.return_value = date(2026, 11, 24)
                titles = {row.title for row in conferences.fetch(config)}
            self.assertEqual(titles.intersection(expected.values()), {expected[config.profile]})

    @patch("neurodaily.sources.fda._fetch_rows")
    @patch("neurodaily.sources.fda._date_range", return_value=("20261101", "20261130"))
    def test_fda_profile_keyword_and_approval_date(self, _window, rows):
        rows.return_value = [{"application_number": "NDA123456",
                              "openfda": {"generic_name": ["cisplatin"]},
                              "submissions": [{"submission_status": "AP", "submission_status_date": "20030112"},
                                              {"submission_status": "AP", "submission_status_date": "20261111"}]}]
        config = _one_source()
        config.sources["fda_drugs"]["filter_keywords"] = ["cisplatin"]
        approvals = fda.fetch_drugs(config)
        self.assertEqual([row.date for row in approvals], ["2026-11-11"])
