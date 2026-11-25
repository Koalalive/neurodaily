from datetime import date
from unittest import TestCase
from unittest.mock import patch

from neurodaily.config import Config, DEFAULT_CONFIG, OPTIONAL_SOURCES
from neurodaily.optimization_evidence import capture_evidence, evaluate_candidate, public_evidence, verify_candidate
from neurodaily.presets import research_presets
from neurodaily.schema import validate
from neurodaily.sources import BUILTIN, arxiv, biorxiv, conferences, fda, gdelt, pubmed, trials


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
        comparison, = holdout["details"]["sources"]
        self.assertEqual(comparison["source"], "pubmed")
        self.assertEqual(comparison["baseline"]["matched"], 1)
        self.assertEqual(comparison["candidate"]["matched"], 2)
        self.assertEqual(comparison["candidate"]["request_count"], 1)
        self.assertEqual(mocked_fetch.call_count, 6)

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
        self.assertEqual(mocked_fetch.call_count, 4)

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
        self.assertTrue(result["eligible"])
        self.assertEqual(result["delta"]["recall"], 0)
        self.assertEqual(result["added"], [])

    def test_development_uses_native_source_quotas_with_same_frozen_baseline(self):
        def fetch(config, name, start, end, *, broad=False):
            rows = [row for row in _ROWS if start <= row["date"] <= end]
            if not broad:
                rows = rows[:config.source_opts(name)["max_results"]]
            return rows, {"status": "ok", "coverage": "full", "captured": len(rows), "request_count": 1}

        baseline, candidate = _one_source(), _one_source()
        baseline.search = candidate.search = {"query": "TI=attention OR TI=memory"}
        baseline.sources["pubmed"]["max_results"] = 1
        candidate.sources["pubmed"]["max_results"] = 4
        with patch("neurodaily.optimization_evidence._fetch", side_effect=fetch):
            snapshot = capture_evidence(baseline, today=date(2026, 11, 24), max_sources=1)
            development = evaluate_candidate(snapshot, baseline, candidate, labels=_LABELS)
        self.assertTrue(development["eligible"])
        self.assertEqual(development["delta"]["recall"], 0.5)
        self.assertEqual([row["ids"] for row in development["added"]], [["pmid:2"]])

    def test_capture_date_strata_preserve_older_records_when_newer_partition_is_full(self):
        newer = [_paper("Attention", str(n), "2026-11-23") for n in range(5, 35)]

        def fetch(config, name, start, end, *, broad=False):
            rows = sorted([row for row in [*_ROWS, *newer] if start <= row["date"] <= end],
                          key=lambda paper: paper["date"], reverse=True)[:24]
            return rows, {"status": "ok", "coverage": "sampled", "captured": len(rows), "request_count": 1}

        baseline = DEFAULT_CONFIG()
        with patch("neurodaily.optimization_evidence._fetch", side_effect=fetch) as query:
            snapshot = capture_evidence(baseline, today=date(2026, 11, 24), max_sources=1, extra_sources=["pubmed"])
        self.assertEqual(snapshot["budget"]["planned_sources"], 1)
        self.assertEqual({call.args[2:4] for call in query.call_args_list},
                         {("2026-10-26", "2026-11-14"), ("2026-11-15", "2026-11-24")})
        samples = {row["date"] for row in snapshot["sources"][0]["examples"]}
        self.assertIn("2026-11-09", samples)
        self.assertIn("2026-11-23", samples)

    def test_holdout_retains_native_changes_even_when_missing_judgments_block_review(self):
        baseline, candidate = _one_source(), _one_source()
        candidate.search = {"query": "TI=attention OR TI=memory"}
        with patch("neurodaily.optimization_evidence._fetch", side_effect=_fetch):
            snapshot = capture_evidence(baseline, today=date(2026, 11, 24), max_sources=1)
        new_paper = _paper("Memory bridge", "25", "2026-11-22")

        def fresh(config, name, start, end, *, broad=False):
            rows, diagnostic = _fetch(config, name, start, end, broad=broad)
            return [*rows, new_paper], diagnostic

        with patch("neurodaily.optimization_evidence._fetch", side_effect=fresh):
            verification = verify_candidate(snapshot, baseline, candidate, labels=_LABELS)
        self.assertFalse(verification["eligible"])
        self.assertIn("native_trial_changes_need_relevance_judgments", verification["reasons"])
        self.assertIn(["pmid:25"], [row["ids"] for row in verification["added"]])

    def test_explicit_source_windows_apply_before_provider_limits(self):
        config = _one_source()
        for source in ("pubmed", "arxiv", "biorxiv", "trials", "fda_drugs", "gdelt"):
            config.sources[source].update(evidence_date_range=("2026-11-01", "2026-11-14"), preview=True)
        with patch.object(pubmed, "_esearch", return_value=[]) as query:
            pubmed.fetch(config)
        self.assertIn("2026/11/01[dp]:2026/11/14[dp]", query.call_args.args[0])
        self.assertIn("2026/11/01[crdt]:2026/11/14[crdt]", query.call_args.args[0])
        with patch.object(arxiv, "_page", return_value=([], 0)) as query:
            arxiv.fetch(config)
        self.assertIn("202611010000 TO 202611142359", query.call_args.args[0])
        with patch.object(biorxiv, "get", return_value=None) as query:
            biorxiv.fetch(config)
        self.assertIn("/2026-11-01/2026-11-14/", query.call_args.args[0])
        with patch.object(trials, "get", return_value=None) as query:
            trials.fetch(config)
        self.assertIn("[2026-11-01,2026-11-14]", query.call_args.kwargs["params"]["filter.advanced"])
        with patch.object(fda, "_fetch_rows", return_value=[]) as query:
            fda.fetch_drugs(config)
        self.assertIn("[20261101 TO 20261114]", query.call_args.args[1])
        with patch.object(gdelt, "get", return_value=None) as query:
            gdelt.fetch(config)
        self.assertEqual(query.call_args.kwargs["params"]["startdatetime"], "20261101000000")
        self.assertEqual(query.call_args.kwargs["params"]["enddatetime"], "20261114235959")

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
