import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from neurodaily.cli import main
from neurodaily.config import DEFAULT_CONFIG
from neurodaily.digest import _mark_match, run
from neurodaily.models import Item
from neurodaily.search import compile_search
from neurodaily.search_quality import evaluate_corpus, load_corpus


class SearchQualityTests(unittest.TestCase):
    def test_default_corpus_replays_without_mutation_and_explains_misses(self):
        corpus = load_corpus()
        snapshot = deepcopy(corpus)
        result = evaluate_corpus(corpus, top=2)
        self.assertEqual(result, evaluate_corpus(corpus, top=2))
        self.assertEqual(corpus, snapshot)
        case = result["cases"][0]
        current = case["candidate"]
        metrics = current["metrics"]
        self.assertEqual(metrics["precision_at_k"], 0.5)
        self.assertEqual(metrics["known_paper_recall"], 0.4)
        self.assertEqual(metrics["known_paper_recall_at_k"], 0.2)
        labels = {row["ids"][0]: row for row in current["judgments"]}
        merged = labels["doi:10.99999/neurodaily-fixture/wm-1"]
        self.assertEqual(merged["sources"], ["journal_rss", "pubmed"])
        self.assertEqual(merged["rank"], 1)
        self.assertEqual(labels["pmid:990001002"]["status"], "below_top_k")
        unknown = labels["doi:10.99999/neurodaily-fixture/wm-3"]
        self.assertEqual(unknown["status"], "unknown_metadata")
        self.assertEqual(unknown["missing_fields"], ["AB"])
        self.assertEqual(labels["doi:10.99999/neurodaily-fixture/wm-4"]["status"], "filtered")
        absence = labels["doi:10.99999/neurodaily-fixture/wm-7"]
        self.assertEqual(absence["status"], "missing_from_capture")
        self.assertEqual(absence["expected_sources"], ["pubmed", "journal_rss"])
        self.assertEqual(case["source_capture"]["journal_rss"]["status"], "partial")

    def test_top_twenty_keeps_unjudged_results_explicit(self):
        current = evaluate_corpus(load_corpus())["cases"][0]["candidate"]
        self.assertEqual(current["metrics"]["precision_at_k"], 2 / 20)
        self.assertEqual(current["metrics"]["unjudged_top_papers"], 1)
        self.assertIsNone(current["top_results"][-1]["relevant"])

    def test_replay_and_digest_rank_same_candidates(self):
        corpus = load_corpus()
        case = corpus["cases"][0]
        config = replace(DEFAULT_CONFIG(), search=case["search"])
        plan = compile_search(config.search, config.journals)
        items = [Item(**row) for row in deepcopy(case["candidates"])]
        for item in items:
            _mark_match(item, plan)
        with (patch("neurodaily.digest._fetch_sources", return_value=(items, [])),
              patch("neurodaily.journal_metrics.for_item", return_value=None),
              patch("neurodaily.onthisday.is_enabled", return_value=False)):
            digest = run(config, check_duplicate=False, record=False)
        replay = evaluate_corpus(corpus, config)["cases"][0]["candidate"]
        self.assertEqual([paper["ids"] for paper in replay["top_results"]],
                         [item.extra["record_ids"] for item in digest.sections["papers"]])

    def test_candidate_and_baseline_compare_against_the_same_labels(self):
        baseline = replace(DEFAULT_CONFIG(), profile="broad-title", search={
            "query": 'TI=("working memory" OR "verbal recall" OR "short-term retention")',
            "sort": "latest",
        })
        with patch("neurodaily.digest._fetch_sources", side_effect=AssertionError("offline replay")):
            result = evaluate_corpus(load_corpus(), baseline=baseline, top=2)["cases"][0]
        self.assertEqual(result["baseline"]["profile"], "broad-title")
        self.assertEqual(result["baseline"]["metrics"]["known_paper_recall"], 0.8)
        self.assertEqual(result["delta"]["known_paper_recall"], -0.4)
        self.assertEqual(result["baseline"]["judgments"][-1]["status"], "missing_from_capture")

    def test_alias_labels_must_name_one_deduplicated_paper_once(self):
        corpus = load_corpus()
        labels = corpus["cases"][0]["labels"]
        labels[0]["ids"].remove("pmid:990001001")
        labels.append({"ids": ["pmid:990001001"], "relevant": False})
        with self.assertRaisesRegex(ValueError, "one judgment per deduplicated paper"):
            evaluate_corpus(corpus)

    def test_stale_search_evidence_is_recomputed(self):
        corpus = load_corpus()
        candidates = corpus["cases"][0]["candidates"]
        candidates[3]["extra"] = {"search_match": "match", "matched_rules": ["from an older query"]}
        judgments = evaluate_corpus(corpus)["cases"][0]["candidate"]["judgments"]
        self.assertEqual(judgments[2]["status"], "unknown_metadata")
        self.assertNotIn("from an older query", judgments[2]["matched_rules"])

    def test_cli_compares_explicit_configs_and_rejects_missing_config(self):
        with TemporaryDirectory() as tmp:
            current_path, baseline_path, corpus_path = [Path(tmp) / name for name in
                                                        ("candidate.json", "baseline.json", "corpus.json")]
            corpus = load_corpus()
            corpus_path.write_text(json.dumps(corpus), encoding="utf-8")
            replace(DEFAULT_CONFIG(), profile="candidate", search={"query": "AB=EEG"}).save(str(current_path))
            replace(DEFAULT_CONFIG(), profile="baseline", search={"query": "AB=MEG"}).save(str(baseline_path))
            with redirect_stdout(io.StringIO()) as output:
                status = main(["--config", str(current_path), "search-quality", "--corpus", str(corpus_path),
                               "--baseline", str(baseline_path), "--top", "3"])
            self.assertEqual(status, 0)
            result = json.loads(output.getvalue())["cases"][0]
            self.assertEqual(result["candidate"]["query"], "AB=EEG")
            self.assertEqual(result["baseline"]["query"], "AB=MEG")
            self.assertGreater(result["delta"]["known_paper_recall"], 0)

            with redirect_stderr(io.StringIO()) as error:
                status = main(["search-quality", "--baseline", str(Path(tmp) / "missing.json")])
            self.assertEqual(status, 2)
            self.assertIn("config not found", error.getvalue())


if __name__ == "__main__":
    unittest.main()
