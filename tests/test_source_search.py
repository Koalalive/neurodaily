"""Offline provider fixtures for advanced candidate fetches and coverage."""

import unittest
from unittest.mock import patch

import httpx

from neurodaily.config import DEFAULT_CONFIG, Journal
from neurodaily.sources import arxiv, biorxiv, fda, http, journalpapers, pubmed


class HttpDiagnosticsTests(unittest.TestCase):
    def test_timeout_and_rate_limit_are_distinct_from_empty(self):
        def respond(request):
            path = request.url.path
            if path == "/slow":
                raise httpx.ReadTimeout("timeout", request=request)
            if path == "/limited":
                return httpx.Response(429, headers={"Retry-After": "120"})
            return httpx.Response(200, json={"results": []})

        with httpx.Client(transport=httpx.MockTransport(respond)) as client, patch.object(http, "_client", client):
            for path, expected in (("/slow", "timeout"), ("/limited", "limited"), ("/empty", "empty")):
                with self.subTest(path=path), http.capture_requests() as stats:
                    response = http.get(f"https://example.org{path}?secret=private", retries=0)
                    if response is not None:
                        http.record_candidates(len(response.json()["results"]))
                    report = stats.as_dict(0)
                    self.assertEqual(report["status"], expected)
                    self.assertEqual(report["request_count"], 1)
                    self.assertNotIn("private", str(report))

    def test_fda_no_match_is_not_a_missing_endpoint(self):
        def respond(request):
            message = "No matches found!" if "drugsfda" in request.url.path else "Endpoint unavailable"
            return httpx.Response(404, json={"error": {"code": "NOT_FOUND", "message": message}})

        config = DEFAULT_CONFIG()
        with httpx.Client(transport=httpx.MockTransport(respond)) as client, patch.object(http, "_client", client):
            with http.capture_requests() as stats:
                self.assertEqual(fda.fetch_drugs(config), [])
                self.assertEqual(stats.as_dict(0)["status"], "empty")
            with http.capture_requests() as stats:
                self.assertEqual(fda.fetch_devices(config), [])
                self.assertEqual(stats.as_dict(0)["status"], "failed")


class LiteratureSourceTests(unittest.TestCase):
    def test_pubmed_legacy_query_includes_global_keywords(self):
        config = DEFAULT_CONFIG()
        config.global_keywords = ["global-fixture"]
        for discipline in config.disciplines:
            discipline.enabled = False
        self.assertEqual(pubmed.build_terms(config), ['("global-fixture"[Title/Abstract])'])

    def test_pubmed_uses_advanced_query_and_complete_metadata(self):
        config = DEFAULT_CONFIG()
        config.search = {"query": "TI=memory AND PY=2023-2024"}
        config.sources["pubmed"].update({"preview": True, "max_results": 1, "lookback_days": 1})
        abstract = "ordinary " * 150 + "end-of-abstract marker"
        xml = f"""<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>
        <Article><ArticleTitle>Working <i>memory</i> task</ArticleTitle>
        <Abstract><AbstractText>{abstract}</AbstractText></Abstract>
        <Journal><ISSN>1234-5678</ISSN><Title>Example Journal</Title>
        <ISOAbbreviation>Ex J</ISOAbbreviation></Journal>
        <ArticleDate DateType="Electronic"><Year>2024</Year><Month>11</Month><Day>30</Day></ArticleDate>
        <PublicationTypeList><PublicationType>Journal Article</PublicationType></PublicationTypeList>
        </Article><MedlineJournalInfo><ISSNLinking>1234-567X</ISSNLinking></MedlineJournalInfo>
        <MeshHeadingList><MeshHeading><DescriptorName>Memory</DescriptorName></MeshHeading></MeshHeadingList>
        <KeywordList><Keyword>EEG</Keyword></KeywordList></MedlineCitation>
        <PubmedData><ArticleIdList><ArticleId IdType="doi">10.1234/identifier</ArticleId></ArticleIdList></PubmedData>
        </PubmedArticle></PubmedArticleSet>"""
        replies = (httpx.Response(200, json={"esearchresult": {"idlist": ["123"], "count": "15"}}),
                   httpx.Response(200, text=xml))
        with patch.object(pubmed, "get", side_effect=replies) as get, http.capture_requests() as stats:
            result, = pubmed.fetch(config)
        query = get.call_args_list[0].kwargs["params"]["term"]
        self.assertIn("memory[ti]", query)
        self.assertIn("2023/01/01[dp]:2024/12/31[dp]", query)
        self.assertEqual(result.date, "2024-11-30")
        self.assertEqual(result.title, "Working memory task")
        self.assertEqual(result.doi, "10.1234/identifier")
        self.assertNotIn("end-of-abstract", result.summary)
        self.assertIn("end-of-abstract", result.extra["abstract"])
        self.assertEqual(result.extra["issns"], ["1234-5678", "1234-567X"])
        self.assertEqual(result.extra["keywords"], ["EEG"])
        self.assertEqual(result.extra["mesh_terms"], ["Memory"])
        self.assertEqual(stats.as_dict(1)["candidate_count"], 15)
        self.assertTrue(stats.as_dict(1)["truncated"])

    def test_arxiv_pages_advanced_candidates_without_merging_publisher_doi(self):
        config = DEFAULT_CONFIG()
        config.search = {"query": "TI=learning AND PY=2024"}
        config.sources["arxiv"]["max_results"] = 64

        def respond(url, *, params, **kwargs):
            entries = "".join(
                f"""<entry><id>https://arxiv.org/abs/2410.{idx:05d}v2</id>
                <title>Learning example {idx}</title><published>2024-10-30T06:00:00Z</published>
                <summary>Full abstract</summary><arxiv:doi>10.1234/published-{idx}</arxiv:doi></entry>"""
                for idx in range(params["start"], params["start"] + params["max_results"])
            )
            return httpx.Response(200, text=f"""<feed xmlns="http://www.w3.org/2005/Atom"
                xmlns:open="http://a9.com/-/spec/opensearch/1.1/"
                xmlns:arxiv="http://arxiv.org/schemas/atom">
                <open:totalResults>80</open:totalResults>{entries}</feed>""")

        with patch.object(arxiv, "get", side_effect=respond) as get, http.capture_requests() as stats:
            items = arxiv.fetch(config)
        self.assertEqual(len(items), 64)
        calls = [call.kwargs["params"] for call in get.call_args_list]
        self.assertEqual([call["start"] for call in calls], [0, 60])
        self.assertIn('ti:"learning"', calls[0]["search_query"])
        self.assertIn("submittedDate:[202401010000 TO 202412312359]", calls[0]["search_query"])
        self.assertNotIn("cat:", calls[0]["search_query"])
        self.assertEqual(items[0].extra["arxiv_id"], "2410.00000")
        self.assertEqual(items[0].extra["version"], "2")
        self.assertEqual(items[0].extra["published_doi"], "10.1234/published-0")
        self.assertEqual(items[0].doi, "")
        self.assertTrue(stats.as_dict(len(items))["truncated"])

    def test_biorxiv_pushes_exact_category_and_uses_latest_version(self):
        config = DEFAULT_CONFIG()
        config.search = {"query": "CAT=neuroscience AND PY=2024"}
        paper = {"doi": "10.1101/fixture", "title": "Working memory", "category": "neuroscience",
                 "date": "2024-11-01", "abstract": "complete"}
        v2 = dict(paper, version="2", published="10.1234/peer-reviewed")
        replies = (
            httpx.Response(200, json={"collection": [dict(paper, version="1"), v2],
                                      "messages": [{"total": 2}]}),
            httpx.Response(200, json={"collection": [], "messages": [{"total": 0}]}),
        )
        with patch.object(biorxiv, "get", side_effect=replies) as get, http.capture_requests() as stats:
            result, = biorxiv.fetch(config)
        for call in get.call_args_list:
            self.assertEqual(call.kwargs["params"], {"category": "neuroscience"})
            self.assertIn("/2024-01-01/2024-12-31/0", call.args[0])
        self.assertEqual(stats.as_dict(1)["candidate_count"], 2)
        self.assertTrue(result.url.endswith("fixturev2"))
        self.assertEqual(result.extra["published_doi"], "10.1234/peer-reviewed")

    def test_journal_workers_report_partial_coverage_and_keep_full_abstract(self):
        config = DEFAULT_CONFIG()
        config.search = {"query": "AB=marker AND PY=2025"}
        config.sources["journal"].update({"preview": True, "max_results": 4})
        config.journals = [Journal("Fixture Journal", rss="https://example.org/good"),
                           Journal("Busy Journal", rss="https://example.org/busy")]
        long_text = "ordinary " * 170 + "marker"
        rss = f"""<rss version="2.0" xmlns:prism="http://prismstandard.org/namespaces/basic/2.0/">
        <channel><title>Fixture Journal</title><link>https://example.org</link><description>Journal</description>
        <item><title>First record</title><link>https://example.org/paper</link>
        <description>{long_text}</description><pubDate>Mon, 01 Sep 2025 00:00:00 GMT</pubDate>
        <prism:doi>10.1234/complete</prism:doi></item>
        <item><title>Second record</title><link>https://example.org/half</link>
        <description>Second record</description><pubDate>Mon, 01 Sep 2025 00:00:00 GMT</pubDate></item>
        </channel></rss>"""

        def respond(request):
            if request.url.path == "/good":
                return httpx.Response(200, text=rss)
            return httpx.Response(429)

        with httpx.Client(transport=httpx.MockTransport(respond)) as client, patch.object(http, "_client", client):
            with http.capture_requests() as stats:
                complete, missing = journalpapers.fetch(config)
        report = stats.as_dict(2)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["request_count"], 2)
        self.assertEqual(report["candidate_count"], 2)
        self.assertIn("HTTP 429", report["request_errors"])
        self.assertEqual(complete.doi, "10.1234/complete")
        self.assertNotIn("marker", complete.summary)
        self.assertIn("marker", complete.extra["abstract"])
        self.assertNotIn("abstract", missing.extra)
        self.assertFalse(missing.summary)


if __name__ == "__main__":
    unittest.main()
