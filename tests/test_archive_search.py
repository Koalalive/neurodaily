from contextlib import ExitStack
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from neurodaily import archive_search
from neurodaily.digest import DigestResult
from neurodaily.models import Item


def _report(*items, profile="neuro", run_id=1, skipped=False):
    return DigestResult(list(items), {}, [], "2026-11-21T08:00:00",
                        config_profile=profile, history_id=run_id, skipped=skipped)


class LocalArchiveTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.directory = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        stack.enter_context(mock.patch.object(archive_search, "DEFAULT_DIRS", {"output": str(self.directory)}))

    def search(self, query, **kwargs):
        return archive_search.search_archive(query, **{"profile": "neuro", **kwargs})["results"]

    def test_empty_or_skipped_reports_do_not_create_database(self):
        self.assertEqual(self.search("stimulation"), [])
        archive_search.index_report(_report(Item(title="stimulation"), skipped=True))
        archive_search.index_report(_report(Item(title="stimulation", kind="not-mapped")))
        self.assertEqual(self.search("stimulation"), [])
        self.assertFalse((self.directory / "archive.db").exists())

    def test_cjk_and_latin_terms_search_with_profiles_kind_and_original_source_urls(self):
        url = "https://example.test/study/NCT00000001?report=1&language=zh#trial"
        trial = Item(title="<em>阿尔茨海默病</em> ＥＥＧ 研究", url=url,
                     kind="trial", source="ClinicalTrials.gov", date="2026-11-14",
                     summary="<p>Brain stimulation is studied here.</p><script>discard me</script>",
                     extra={"nct_id": "NCT00000001", "phase": ["PHASE2"], "status": "RECRUITING",
                            "record_ids": ["pmid:123456"]})
        paper = Item(title="阿尔茨海默病中的 EEG 论文", summary="A report.", kind="paper")
        archive_search.index_report(_report(trial, paper, run_id=10))
        archive_search.index_report(_report(paper, profile="oncology", run_id=11))
        rows = self.search("茨海默 EEG", kind="trial")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["run_id"], 10)
        self.assertEqual(row["url"], url)
        self.assertEqual(row["record_id"], "nct:NCT00000001")
        self.assertEqual(row["stage"], "PHASE2 · RECRUITING")
        self.assertEqual(row["title"], "阿尔茨海默病 ＥＥＧ 研究")
        self.assertNotIn("discard me", row["summary"])
        self.assertEqual(self.search("pmid:123456"), rows)
        self.assertEqual(self.search("recruiting"), rows)
        self.assertEqual([item["kind"] for item in self.search("茨海默", profile="oncology")], ["paper"])
        self.assertFalse(self.search("茨 海病"))

    def test_upsert_keeps_profile_separate_and_does_not_let_old_run_replace_new(self):
        original = Item(title="Dataset cognition", doi="10.1234/article", url="https://example.test/v1?q=5",
                        summary="Useful motor data.", date="2026-11-12")
        latest = Item(title="Dataset cognition, updated", doi="10.1234/article", url="https://example.test/v2")
        archive_search.index_report(_report(original, run_id=1))
        archive_search.index_report(_report(latest, run_id=2))
        archive_search.index_report(_report(original, run_id=1))
        archive_search.index_report(_report(original, run_id=None))
        archive_search.index_report(_report(original, profile="independent", run_id=3))
        self.assertEqual([(row["url"], row["run_id"], row["date"]) for row in self.search("motor")],
                         [(latest.url, 2, original.date)])
        self.assertEqual([row["url"] for row in self.search("motor", profile="independent")], [original.url])
        self.assertEqual(len(self.search("10.1234/article")), 1)

    def test_match_syntax_is_literal_and_exact_phrase_has_no_word_reordering(self):
        exact = Item(title="Deep brain stimulation", url="https://example.test/one")
        unordered = Item(title="Brain deep electrical stimulation", url="https://example.test/two")
        archive_search.index_report(_report(unordered, exact))
        self.assertEqual([row["url"] for row in self.search('"deep brain stimulation"')], [exact.url])
        self.assertEqual(self.search("deep brain stimulation", limit=1)[0]["url"], exact.url)
        self.assertEqual(self.search('unrelated" OR *"'), [])
        with self.assertRaises(ValueError):
            self.search("a", limit=True)
        with self.assertRaises(ValueError):
            self.search("a", kind="unknown")

    def test_non_fts_local_backend_still_searches_and_recovers_index(self):
        item = Item(title="Résumé 与神经科学", kind="paper", summary="Offline archive.")
        with mock.patch.object(archive_search, "_sync_fts", return_value=False):
            archive_search.index_report(_report(item))
            fallback = self.search("resume 神经")
        self.assertEqual(len(fallback), 1)
        self.assertEqual(self.search("resume 神经"), fallback)

    def test_unsafe_links_are_removed_but_content_remains_searchable(self):
        urls = ("javascript:alert(1)", "https://name:password@example.test/",
                "https://example.test/?api-key=TOP-SECRET")
        archive_search.index_report(_report(*(Item(title=f"finding {n}", url=url)
                                               for n, url in enumerate(urls))))
        rows = self.search("finding")
        self.assertEqual(len(rows), len(urls))
        self.assertTrue(all(row["url"] == "" for row in rows))
        self.assertNotIn(b"TOP-SECRET", (self.directory / "archive.db").read_bytes())


class OpenSearchArchiveTests(unittest.TestCase):
    def setUp(self):
        prefix = "NEURODAILY_OPENSEARCH_"
        self.config = {prefix + key: value for key, value in {
            "URL": "https://search.example.test/proxy", "INDEX": "papers-v2", "MODEL_ID": "dense-model",
            "PIPELINE": "rrf-normalize", "USERNAME": "fixture", "PASSWORD": "sensitive-fixture"}.items()}

    def test_hybrid_query_and_source_whitelist(self):
        matching = {"profile": "neuro", "kind": "paper", "title": "<b>Model paper</b>",
                    "url": "https://example.test/?page=2", "summary": "<style>ignored</style>Safe.",
                    "run_id": 3, "record_id": "doi:10.1234/test", "authorization": "secret"}
        hits = [{"_source": matching}, {"_source": {**matching, "profile": "other"}},
                {"_source": {**matching, "kind": "trial"}}]
        opener = mock.Mock()
        opener.open.return_value = BytesIO(json.dumps({"hits": {"hits": hits}}).encode())
        with mock.patch.dict(os.environ, self.config, clear=True), \
                mock.patch.object(archive_search, "build_opener", return_value=opener):
            self.assertTrue(archive_search.opensearch_configured())
            result = archive_search.search_archive("memory", profile="neuro", limit=10,
                                                   kind="paper", backend="opensearch")
        request = opener.open.call_args.args[0]
        target = urlsplit(request.full_url)
        self.assertEqual(target.path, "/proxy/papers-v2/_search")
        self.assertEqual(parse_qs(target.query)["search_pipeline"], ["rrf-normalize"])
        self.assertEqual(request.method, "POST")
        self.assertTrue(request.get_header("Authorization").startswith("Basic "))
        hybrid = json.loads(request.data)["query"]["hybrid"]
        self.assertEqual(hybrid["filter"]["bool"]["filter"],
                         [{"term": {"profile": "neuro"}}, {"term": {"kind": "paper"}}])
        self.assertEqual(hybrid["queries"][0]["multi_match"]["query"], "memory")
        self.assertEqual(hybrid["queries"][1]["neural"]["embedding"],
                         {"query_text": "memory", "model_id": "dense-model", "k": 10})
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["results"][0]["summary"], "Safe.")
        self.assertNotIn("authorization", result["results"][0])

    def test_remote_failures_are_visible_and_do_not_contact_server_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(archive_search, "build_opener") as build:
            self.assertFalse(archive_search.opensearch_configured())
            with self.assertRaisesRegex(archive_search.ArchiveSearchError, "OpenSearch requires"):
                archive_search.search_archive("memory", profile="neuro", backend="opensearch")
            build.assert_not_called()
        opener = mock.Mock()
        opener.open.side_effect = HTTPError("https://private.example.test/", 401, "private details",
                                           None, BytesIO(b"ignored confidential diagnostic"))
        with mock.patch.dict(os.environ, self.config, clear=True), \
                mock.patch.object(archive_search, "build_opener", return_value=opener):
            with self.assertRaisesRegex(archive_search.ArchiveSearchError, r"^OpenSearch returned HTTP 401$"):
                archive_search.search_archive("memory", profile="neuro", backend="opensearch")
