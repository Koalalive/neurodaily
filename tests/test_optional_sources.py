from datetime import date, timedelta
from unittest.mock import patch
import unittest

import httpx

from neurodaily.config import DEFAULT_CONFIG
from neurodaily.sources import europe_pmc, gdelt, nih_brain, openalex
from neurodaily.sources.http import capture_requests


def response(data):
    return httpx.Response(200, json=data)


class EuropePMCTests(unittest.TestCase):
    def test_bounds_pagination_and_bibliographic_metadata(self):
        config = DEFAULT_CONFIG()
        config.sources["europe_pmc"] = {"query": "TITLE:fixture", "max_results": 2,
                                        "paper_date_range": ["2025-01-01", "2025-06-01"]}
        row = {
            "title": "A <i>fixture</i> study", "id": "12345678", "source": "MED",
            "pmcid": "PMC123456", "doi": "https://doi.org/10.1234/Test", "isOpenAccess": "Y",
            "firstPublicationDate": "2025-03-04", "firstIndexDate": "2025-03-15",
            "abstractText": "<b>Methods:</b> Example abstract.",
            "pubTypeList": {"pubType": ["Randomized Controlled Trial"]},
            "meshHeadingList": {"meshHeading": [{"descriptorName": "Stroke"}]},
            "journalInfo": {
                "journal": {"title": "Fixture Journal", "medlineAbbreviation": "Fix J", "issn": "1234-5678"},
                "electronicPublicationDate": "2025-03-04",
                "printPublicationDate": "2025-04",
            },
            "authorList": {"author": [{"fullName": "Alex Li", "authorAffiliationDetailsList": {
                "authorAffiliation": [{"affiliation": "Lab, Lyon, France"}],
            }}]},
        }
        pages = [
            response({"hitCount": 3, "nextCursorMark": "next", "resultList": {"result": [row]}}),
            response({"hitCount": 3, "nextCursorMark": "last", "resultList": {"result": [
                {"title": "Preprint", "id": "PPR100", "source": "PPR", "pubYear": "2025"},
            ]}}),
        ]
        with patch.object(europe_pmc, "get", side_effect=pages) as get, capture_requests() as stats:
            first, second = europe_pmc.fetch(config)
        self.assertEqual([call.kwargs["params"]["cursorMark"] for call in get.call_args_list], ["*", "next"])
        self.assertEqual([call.kwargs["params"]["pageSize"] for call in get.call_args_list], [2, 1])
        self.assertIn("(TITLE:fixture) AND FIRST_PDATE:[2025-01-01 TO 2025-06-01]", stats.queries[0])
        self.assertEqual((stats.candidate_count, stats.truncated), (2, True))
        self.assertEqual((first.kind, first.source, first.date, first.doi),
                         ("paper", "europe_pmc", "2025-03-04", "10.1234/test"))
        self.assertEqual(first.extra["pmid"], "12345678")
        self.assertEqual(first.extra["pmcid"], "PMC123456")
        self.assertEqual(first.affiliations, ["Lab, Lyon, France"])
        self.assertEqual(first.extra["mesh_terms"], ["Stroke"])
        self.assertEqual(first.extra["publication_types"], ["Randomized Controlled Trial"])
        self.assertEqual(first.extra["published_print"], "2025-04")
        self.assertEqual(second.date, "2025")

    def test_duplicate_cursor_reports_sample_without_looping(self):
        config = DEFAULT_CONFIG()
        payload = {"hitCount": 100, "nextCursorMark": "*", "resultList": {"result": []}}
        with patch.object(europe_pmc, "get", return_value=response(payload)) as get, capture_requests() as stats:
            self.assertEqual(europe_pmc.fetch(config), [])
        get.assert_called_once()
        self.assertTrue(stats.truncated)


class OpenAlexTests(unittest.TestCase):
    def test_key_only_in_header_and_clinical_fields(self):
        config = DEFAULT_CONFIG()
        config.sources["openalex"] = {"query": "styled override", "max_results": 2,
                                      "paper_date_range": ["2025-01-01", "2025-06-01"]}
        row = {
            "id": "https://openalex.org/W42", "display_name": "Fixture paper",
            "publication_date": "2025-05-10", "type": "review", "cited_by_count": 0,
            "ids": {"doi": "https://doi.org/10.1234/example", "pmid": "https://pubmed.ncbi.nlm.nih.gov/42/",
                    "pmcid": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC42/"},
            "abstract_inverted_index": {"placeholders": [-1, True, 20000], "paper": [1], "Fixture": [0]},
            "affiliations": [],
            "authorships": [{"author": {"display_name": "Alex Li"}, "is_corresponding": True,
                             "raw_affiliation_strings": ["Research Center, France"], "countries": ["FR"]}],
            "primary_location": {"source": {"display_name": "Fixture Journal", "issn_l": "1111-1111",
                                            "issn": ["1111-1111", "2222-2222"]}},
            "open_access": {"is_oa": False}, "mesh": [{"descriptor_name": "Stroke"}],
        }
        payloads = [
            response({"meta": {"count": 2, "next_cursor": "opaque"}, "results": [row]}),
            response({"meta": {"count": 2}, "results": []}),
        ]
        with (
            patch.dict("os.environ", {"OPENALEX_API_KEY": "unit-test-key"}),
            patch.object(openalex, "get", side_effect=payloads) as get,
            capture_requests() as stats,
        ):
            item, = openalex.fetch(config)
        self.assertEqual([call.kwargs["params"]["cursor"] for call in get.call_args_list], ["*", "opaque"])
        for call in get.call_args_list:
            self.assertEqual(call.kwargs["headers"], {"Authorization": "Bearer unit-test-key"})
            self.assertNotIn("unit-test-key", repr(call.kwargs["params"]))
            self.assertEqual(call.kwargs["params"]["search"], "styled override")
        self.assertNotIn("unit-test-key", repr(stats.as_dict(1)))
        self.assertEqual((item.summary, item.doi, item.date), ("Fixture paper", "10.1234/example", "2025-05-10"))
        self.assertEqual(item.extra["pmid"], "42")
        self.assertEqual(item.extra["pmcid"], "PMC42")
        self.assertEqual(item.extra["institution_countries"], ["FR"])
        self.assertEqual(item.extra["mesh_terms"], ["Stroke"])
        self.assertEqual(item.extra["issns"], ["1111-1111", "2222-2222"])
        self.assertEqual(item.extra["openalex_cited_by_count"], 0)
        self.assertIs(item.extra["is_open_access"], False)
        self.assertEqual(item.corresponding, ["Alex Li"])

    def test_anonymous_only_first_page_and_no_unbounded_query(self):
        config = DEFAULT_CONFIG()
        config.sources["openalex"] = {"max_results": 800}
        payload = {"meta": {"count": 200, "next_cursor": "opaque"}, "results": []}
        with (
            patch.dict("os.environ", {"OPENALEX_API_KEY": ""}),
            patch.object(openalex, "get", return_value=response(payload)) as get,
            capture_requests() as stats,
        ):
            self.assertEqual(openalex.fetch(config), [])
        get.assert_called_once()
        self.assertEqual(get.call_args.kwargs["params"]["per_page"], 100)
        self.assertNotIn("cursor", get.call_args.kwargs["params"])
        self.assertTrue(stats.truncated)
        config.sources["openalex"]["query"] = "x" * 1001
        with patch.object(openalex, "get") as get:
            self.assertEqual(openalex.fetch(config), [])
        get.assert_not_called()


class GDELTTests(unittest.TestCase):
    def test_only_headline_link_and_index_timestamp(self):
        config = DEFAULT_CONFIG()
        config.sources["gdelt"] = {"query": '(neuroscience OR "brain imaging")', "lookback_days": 3, "max_results": 2}
        rows = [
            {"title": "Valid <b>headline</b>", "url": "https://news.example/work",
             "seendate": "20251121T120000Z", "sourcecountry": "France", "domain": "news.example",
             "language": "French", "summary": "body omitted", "socialimage": "https://example.com/image"},
            {"title": "Invalid link", "url": "javascript:alert(1)", "seendate": "invalid"},
        ]
        with patch.object(gdelt, "get", return_value=response({"articles": rows})) as get, capture_requests() as stats:
            item, = gdelt.fetch(config)
        self.assertEqual(get.call_args.kwargs["params"]["query"], config.sources["gdelt"]["query"])
        self.assertEqual(get.call_args.kwargs["params"]["mode"], "artlist")
        self.assertEqual(get.call_args.kwargs["params"]["timespan"], "3d")
        self.assertEqual((item.title, item.summary, item.kind, item.date), ("Valid headline", "", "news", "2025-11-21"))
        self.assertEqual(item.extra["indexed_at"], "2025-11-21T12:00:00+00:00")
        self.assertEqual(item.extra["publisher_country"], "France")
        self.assertEqual(item.extra["date_kind"], "indexed")
        self.assertNotIn("summary", item.extra)
        self.assertNotIn("socialimage", item.extra)
        self.assertTrue(stats.truncated)

    def test_bad_json_surfaces_failure(self):
        with (
            patch.object(gdelt, "get", return_value=httpx.Response(200, text="The API refused the query")),
            capture_requests() as stats,
        ):
            self.assertEqual(gdelt.fetch(DEFAULT_CONFIG()), [])
        self.assertEqual(stats.as_dict(0)["status"], "failed")


class NIHBrainTests(unittest.TestCase):
    def test_curates_brain_initiative_from_official_feed_without_storing_body(self):
        config = DEFAULT_CONFIG()
        config.sources["nih_brain"] = {"query": "imaging", "lookback_days": 3}
        yesterday = date.today() - timedelta(days=1)
        pubdate = yesterday.strftime("%a, %d %b %Y 12:00:00 GMT")
        feed = f'''<rss version="2.0"><channel><title>NIH News Releases</title>
        <link>https://www.nih.gov/</link><description>Official releases</description>
        <item><title>Study improves imaging</title>
        <link>https://www.nih.gov/news-events/news-releases/imaging</link>
        <description>The BRAIN Initiative supported the imaging study.</description><pubDate>{pubdate}</pubDate></item>
        <item><title>Other NIH imaging study</title><link>https://www.nih.gov/news-events/news-releases/other</link>
        <description>General NIH research.</description><pubDate>{pubdate}</pubDate></item>
        <item><title>BRAIN Initiative imaging on an external site</title><link>https://example.com/news/story</link>
        <description>Only official NIH URLs are included.</description><pubDate>{pubdate}</pubDate></item>
        </channel></rss>'''
        with (
            patch.object(nih_brain, "get", return_value=httpx.Response(200, content=feed.encode())) as get,
            capture_requests() as stats,
        ):
            item, = nih_brain.fetch(config)
        self.assertEqual(get.call_args.args, (nih_brain.BASE,))
        self.assertEqual((item.kind, item.source, item.date, item.summary),
                         ("news", "nih_brain", yesterday.isoformat(), ""))
        self.assertEqual(item.extra["publisher_domain"], "www.nih.gov")
        self.assertEqual(stats.candidate_count, 3)
