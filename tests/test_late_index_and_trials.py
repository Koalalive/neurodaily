from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

import httpx

from neurodaily.config import DEFAULT_CONFIG, Discipline
from neurodaily.sources import http, pubmed, trials


class FrozenDateTime(datetime):
    @classmethod
    def now(cls):
        return cls(2026, 11, 22, 12, 0)


def config_with_terms(*terms):
    config = DEFAULT_CONFIG()
    config.disciplines = [Discipline(name="Fixture", keywords=list(terms))]
    config.global_keywords = []
    return config


def date_xml(date):
    year, month, day = date.split("-")
    return f"<Year>{year}</Year><Month>{month}</Month><Day>{day}</Day>"


def pubmed_xml(pmid, published, *, created="", indexed=""):
    history = "".join(f'<PubMedPubDate PubStatus="{name}">{date_xml(date)}</PubMedPubDate>'
                      for name, date in (("entrez", created), ("pubmed", indexed)) if date)
    return httpx.Response(200, text=f"""<PubmedArticleSet><PubmedArticle>
      <MedlineCitation><PMID>{pmid}</PMID><DateCreated>{date_xml('2001-05-06')}</DateCreated>
      <Article><ArticleTitle>Memory study {pmid}</ArticleTitle>
      <ArticleDate DateType="Electronic">{date_xml(published)}</ArticleDate></Article>
      </MedlineCitation><PubmedData><History>{history}</History></PubmedData>
      </PubmedArticle></PubmedArticleSet>""")


def pubmed_ids(*pmids):
    return httpx.Response(200, json={"esearchresult": {"idlist": list(pmids), "count": str(len(pmids))}})


class PubMedDiscoveryTests(TestCase):
    def test_recent_creation_gets_independent_query_budget_and_keeps_print_date(self):
        config = config_with_terms("memory")
        config.sources["pubmed"].update(max_results=1, lookback_days=1)

        with patch.object(pubmed, "datetime", FrozenDateTime), patch.object(pubmed, "get", side_effect=[
            pubmed_ids("123"), pubmed_xml("123", "2026-11-22", created="2026-11-22"),
            pubmed_ids("456"), pubmed_xml("456", "2024-03-02", created="2026-11-22", indexed="2024-03-02"),
        ]) as get:
            recent, late = pubmed.fetch(config)

        published_params, _, added_params, _ = [call.kwargs["params"] for call in get.call_args_list]
        self.assertIn('"last 1 days"[dp]', published_params["term"])
        self.assertNotIn("[crdt]", published_params["term"])
        self.assertIn('"last 1 days"[crdt] NOT "last 1 days"[dp]', added_params["term"])
        self.assertEqual((published_params["retmax"], added_params["retmax"]), (1, 1))
        self.assertEqual(recent.date, "2026-11-22")
        self.assertEqual(late.date, "2024-03-02")
        self.assertEqual(late.extra["published_online"], "2024-03-02")
        self.assertEqual(late.extra["pubmed_created_at"], "2026-11-22")
        self.assertEqual(late.extra["source_discovered_at"], "2026-11-22")
        self.assertEqual(late.extra["pubmed_first_indexed_at"], "2024-03-02")
        self.assertEqual(late.extra["entry_date"], "2026-11-22")

    def test_explicit_publication_dates_override_relative_discovery(self):
        config = config_with_terms("memory")
        config.search = {"query": "TI=memory AND PY=2024"}
        config.sources["pubmed"]["lookback_days"] = 1
        with patch.object(pubmed, "get", side_effect=[
            pubmed_ids("456"), pubmed_xml("456", "2024-03-02", created="2026-11-22"),
        ]) as get:
            result, = pubmed.fetch(config)
        query = get.call_args_list[0].kwargs["params"]["term"]
        self.assertIn("2024/01/01[dp]:2024/12/31[dp]", query)
        self.assertNotIn("[crdt]", query)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(result.date, "2024-03-02")

    def test_preview_uses_one_date_query_and_can_use_public_index_date_if_creation_missing(self):
        config = config_with_terms("memory")
        config.sources["pubmed"].update(preview=True, lookback_days=1)
        with patch.object(pubmed, "datetime", FrozenDateTime), patch.object(pubmed, "get", side_effect=[
            pubmed_ids("456"), pubmed_xml("456", "2024-03-02", indexed="2026-11-22"),
        ]) as get:
            result, = pubmed.fetch(config)
        self.assertIn('"last 1 days"[dp] OR "last 1 days"[crdt]', get.call_args_list[0].kwargs["params"]["term"])
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args_list[0].kwargs["retries"], 0)
        self.assertEqual(result.extra["source_discovered_at"], "2026-11-22")
        self.assertNotIn("pubmed_created_at", result.extra)


def trial_row(number, update, **status_fields):
    return {"protocolSection": {
        "identificationModule": {"nctId": f"NCT{number:08d}", "briefTitle": f"Trial {number}"},
        "statusModule": {"overallStatus": "RECRUITING", "lastUpdatePostDateStruct": {"date": update}, **status_fields},
        "conditionsModule": {"conditions": ["Memory"]},
        "designModule": {"phases": ["PHASE1"], "enrollmentInfo": {"count": 6}},
    }}


def trial_page(*rows, next_token=None):
    data = {"studies": list(rows)}
    if next_token is not None:
        data["nextPageToken"] = next_token
    return httpx.Response(200, json=data)


class ClinicalTrialPaginationTests(TestCase):
    def test_all_terms_are_requested_and_pagination_deduplicates_in_date_order(self):
        config = config_with_terms(*(f"term {number}" for number in range(1, 10)))
        config.global_keywords = ["global term"]
        config.sources["trials"].update(max_results=3, lookback_days=2)
        late = trial_row(3, "2026-11-22", studyFirstSubmitDate="2025-03-01",
                         studyFirstPostDateStruct={"date": "2025-03-08"}, resultsFirstSubmitDate="2026-11-20",
                         resultsFirstPostDateStruct={"date": "2026-11-22"}, overallStatus="COMPLETED")
        with patch.object(trials, "get", side_effect=[
            trial_page(trial_row(1, "2026-11-20"), next_token="next-A"),
            trial_page(trial_row(1, "2026-11-21"), trial_row(2, "2026-11-20")),
            trial_page(late),
        ]) as get, http.capture_requests() as stats, patch.object(trials, "datetime", FrozenDateTime):
            items = trials.fetch(config)
        first, second, next_page = [call.kwargs["params"] for call in get.call_args_list]
        self.assertEqual(first["query.term"], '"term 1" OR "term 2" OR "term 3" OR "term 4" OR "term 5"')
        self.assertIn('"term 9"', second["query.term"])
        self.assertIn('"global term"', second["query.term"])
        self.assertEqual(next_page, {**first, "pageToken": "next-A"})
        self.assertIn("2026-11-20", first["filter.advanced"])
        self.assertEqual([item.extra["nct"] for item in items], ["NCT00000003", "NCT00000001", "NCT00000002"])
        self.assertEqual(items[1].date, "2026-11-21")
        self.assertEqual(stats.as_dict(3)["coverage"], "full")
        self.assertEqual(items[0].date, "2026-11-22")
        self.assertEqual(items[0].extra["trial_dates"], {
            "first_submitted": "2025-03-01", "first_posted": "2025-03-08",
            "last_update_posted": "2026-11-22", "results_first_submitted": "2026-11-20",
            "results_first_posted": "2026-11-22",
        })
        self.assertEqual(items[0].extra["trial_events"], [
            {"kind": "registered", "date": "2025-03-08"},
            {"kind": "registry_updated", "date": "2026-11-22"},
            {"kind": "results_posted", "date": "2026-11-22"},
        ])
        self.assertEqual(items[0].extra["status"], "COMPLETED")
        self.assertEqual(items[0].extra["source_discovered_at"], "2025-03-08")
        self.assertTrue(items[0].extra["has_results"])

    def test_duplicate_page_token_stops_and_marks_partial(self):
        config = config_with_terms("memory")
        config.sources["trials"]["max_results"] = 4
        response = trial_page(trial_row(1, "2026-11-22"), next_token="repeated")
        with patch.object(trials, "get", return_value=response) as get, http.capture_requests() as stats:
            items = trials.fetch(config)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(len(items), 1)
        self.assertEqual(stats.as_dict(1)["coverage"], "partial")
        self.assertTrue(stats.as_dict(1)["truncated"])

    def test_preview_caps_requests_and_marks_unchecked_topics(self):
        config = config_with_terms(*(f"term {number}" for number in range(16)))
        config.sources["trials"].update(preview=True, max_results=500)
        response = trial_page(trial_row(1, "2026-11-22"))
        with patch.object(trials, "_PREVIEW_REQUEST_LIMIT", 2), patch.object(trials, "get", return_value=response) as get, http.capture_requests() as stats:
            items = trials.fetch(config)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args_list[0].kwargs["params"]["pageSize"], 30)
        self.assertEqual(get.call_args_list[0].kwargs["retries"], 0)
        self.assertEqual(len(items), 1)
        self.assertEqual(stats.as_dict(1)["coverage"], "partial")
        self.assertTrue(stats.as_dict(1)["truncated"])

    def test_query_literals_cannot_inject_boolean_operators(self):
        config = config_with_terms('incomplete" OR "arbitrary', 'incomplete" OR "arbitrary', "Мышление")
        self.assertEqual(list(trials._queries(config)), ['"incomplete OR arbitrary" OR "Мышление"'])

    def test_oversized_term_is_reported_but_does_not_block_other_terms(self):
        config = config_with_terms("关" * 120, "sepsis")
        with patch.object(trials, "get", return_value=trial_page()) as get, http.capture_requests() as stats:
            items = trials.fetch(config)
        self.assertEqual(items, [])
        self.assertEqual(get.call_args.kwargs["params"]["query.term"], '"sepsis"')
        self.assertTrue(stats.as_dict(0)["truncated"])
        self.assertEqual(stats.as_dict(0)["coverage"], "partial")
