import json
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from neurodaily.config import DEFAULT_CONFIG
from neurodaily.geography import locate_items
from neurodaily.models import Item
from neurodaily.sources.trials import fetch


COUNTRIES = {
    "US": {"name": "United States", "zh": "美国", "ru": "Соединённые Штаты", "lat": 39, "lon": -98},
    "FR": {"name": "France", "zh": "法国", "ru": "Франция", "lat": 46, "lon": 2},
    "DE": {"name": "Germany", "zh": "德国", "ru": "Германия", "lat": 51, "lon": 10},
    "CN": {"name": "China", "zh": "中国", "ru": "Китай", "lat": 35, "lon": 104},
    "GE": {"name": "Georgia", "zh": "格鲁吉亚", "ru": "Грузия", "lat": 42, "lon": 43.5},
    "AU": {"name": "Australia", "zh": "澳大利亚", "ru": "Австралия", "lat": -25, "lon": 133},
    "TR": {"name": "Turkey", "zh": "土耳其", "ru": "Турция", "lat": 39, "lon": 35},
}


def message(rows):
    return {"content": json.dumps(rows, ensure_ascii=False)}


@patch("neurodaily.geography._countries", return_value=COUNTRIES)
class GeographyTests(unittest.TestCase):
    def test_trial_records_keep_multiple_sites_and_suppress_contact_data(self, _):
        response = Mock()
        response.json.return_value = {"studies": [{"protocolSection": {
            "identificationModule": {"nctId": "NCT04723901", "briefTitle": "Fixture trial"},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Fixture Sponsor, Germany"}},
            "contactsLocationsModule": {"locations": [
                {"country": "United States", "city": "Boston", "facility": "Fixture Hospital",
                 "contacts": [{"name": "Fixture person"}], "geoPoint": {"lat": 42.36, "lon": -71.05}},
                {"country": "France", "city": "Lyon", "geoPoint": {"lat": 999, "lon": 4.8}},
                {"country": "China", "city": "Shanghai", "geoPoint": {"lat": True, "lon": 121}},
            ]},
        }}]}
        config = DEFAULT_CONFIG()
        config.disciplines = config.disciplines[:1]
        with patch("neurodaily.sources.trials.get", return_value=response):
            trial, = fetch(config)
        sites = trial.extra["trial_sites"]
        self.assertEqual(len(sites), 3)
        self.assertNotIn("contacts", sites[0])
        self.assertNotIn("geoPoint", sites[1])
        self.assertNotIn("geoPoint", sites[2])
        self.assertIn("Fixture Sponsor, Germany", trial.affiliations)

        result = locate_items({"trial": trial})
        self.assertEqual(result["unknown"], [])
        self.assertEqual({row["country"] for row in result["places"]}, {"US", "FR", "CN"})
        self.assertEqual({row["role"] for row in result["places"]}, {"trial_site"})
        points = {row["country"]: row for row in result["places"]}
        self.assertEqual((points["US"]["lat"], points["US"]["lon"], points["US"]["precision"]),
                         (42.36, -71.05, "site"))
        self.assertEqual((points["FR"]["lat"], points["FR"]["lon"], points["FR"]["precision"]),
                         (46, 2, "country"))

    def test_affiliation_is_not_a_study_or_news_location(self, _):
        items = {
            "paper": Item("Paper", affiliations=["Lab, Cambridge MA 02139 USA", "Institute, Germany",
                                                   "University campus, Georgia", "Lab, CA"]),
            "news": Item("Announcement", source="Germany", kind="news", affiliations=["Publisher, Germany"]),
            "legacy_trial": Item("Older trial", kind="trial", affiliations=["Trial sponsor, France"]),
        }
        result = locate_items(items)
        self.assertEqual(result["unknown"], ["news", "legacy_trial"])
        self.assertEqual([(row["country"], row["role"], row["precision"], row["method"])
                          for row in result["places"]],
                         [("US", "institution", "country", "metadata"),
                          ("DE", "institution", "country", "metadata")])

    def test_model_only_maps_verbatim_role_specific_country_evidence(self, _):
        study = "The study recruited participants in Germany."
        event = "The society held its congress in Lyon, France."
        items = {
            "paper": Item("Paper", summary=study, affiliations=["Fixture University, France"]),
            "event": Item("Congress", kind="news", summary=event),
            "byline": Item("New guideline", kind="news",
                           summary="Publisher correspondent in Germany reported the guideline was announced."),
            "ambiguous": Item("Bad location", kind="news", summary="The society opened an office in Georgia."),
            "patient": Item("Case report", summary="The study recruited a patient who lived at a home address in France."),
        }
        chat = Mock(return_value=message([
            {"id": "0", "country": "DE", "role": "study_site", "evidence": study, "lat": 1, "lon": 2},
            {"id": "1", "country": "FR", "role": "event", "evidence": event},
        ]))
        result = locate_items(items, chat=chat)
        chat.assert_called_once()
        self.assertEqual(result["unknown"], ["byline", "ambiguous", "patient"])
        points = {(row["id"], row["role"]): row for row in result["places"]}
        self.assertEqual(len(points), 2)
        self.assertNotIn(("paper", "institution"), points)
        self.assertEqual(points["paper", "study_site"]["evidence"], study)
        self.assertEqual((points["paper", "study_site"]["lat"], points["paper", "study_site"]["lon"]),
                         (51, 10))
        self.assertEqual(points["event", "event"]["method"], "model")

    def test_news_without_event_location_falls_back_to_publisher(self, _):
        item = Item("Science news", kind="news", url="https://www.science.org/content/article/example",
                    summary="A headline without a country or city.")
        point, = locate_items({"news": item})["places"]
        self.assertEqual((point["role"], point["method"], point["country"], point["name"]),
                         ("media_outlet", "publisher", "US", "Washington, D.C."))
        self.assertIn("Science/AAAS", point["evidence"])

    def test_parenthetical_country_and_institution_inference(self, _):
        trial = Item("Trial", kind="trial", extra={"trial_sites": [{
            "facility": "Fixture University", "city": "Zonguldak",
            "country": "Turkey (Türkiye)", "geoPoint": {"lat": 41.45, "lon": 31.79},
        }]})
        point, = locate_items({"trial": trial})["places"]
        self.assertEqual((point["country"], point["name"], point["precision"]),
                         ("TR", "Fixture University, Zonguldak", "site"))

        paper = Item("Paper", affiliations=["University of New South Wales"])
        quote = "University of New South Wales"
        chat = Mock(return_value=message([{
            "id": "0", "country": "AU", "role": "institution",
            "evidence": quote,
        }]))
        point, = locate_items({"paper": paper}, chat=chat)["places"]
        self.assertEqual((point["country"], point["role"], point["method"]),
                         ("AU", "institution", "model"))

    def test_last_author_location_precedes_other_author_affiliations_and_removes_email(self, _):
        paper = Item("Fixture", authors=["First", "Last"],
                     affiliations=["First institution, France", "Last institute, Beijing, China"],
                     extra={"last_author_affiliations": [
                         {"address": "Last institute, Beijing, China. Electronic address: person@example.test"}
                     ]})
        point, = locate_items({"paper": paper})["places"]
        self.assertEqual((point["role"], point["precision"], point["country"], point["name"]),
                         ("last_author_institution", "city", "CN", "Beijing"))
        self.assertNotIn("person@example.test", point["evidence"])

    def test_model_maps_city_only_quotes_and_rejects_country_conflicts(self, _):
        quote = "The research society held its congress in Beijing."
        item = Item("Congress update", kind="news", summary=quote)
        chat = Mock(return_value=message([
            {"id": "0", "country": "CN", "city": "Beijing", "role": "event", "evidence": quote}
        ]))
        point, = locate_items({"event": item}, chat=chat)["places"]
        self.assertEqual((point["name"], point["country"], point["precision"], point["method"]),
                         ("Beijing", "CN", "city", "model"))
        chat.return_value = message([{"id": "0", "country": "FR", "city": "Beijing",
                                      "role": "event", "evidence": quote}])
        self.assertEqual(locate_items({"event": item}, chat=chat)["unknown"], ["event"])

    def test_address_backfill_uses_only_exact_doi_metadata(self, _):
        from neurodaily.sources import europe_pmc
        response = Mock()
        response.json.return_value = {"resultList": {"result": [
            {"doi": "10.1234/fixture", "title": "Matching paper", "authorList": {"author": [
                {"lastName": "First", "affiliation": "First lab, France"},
                {"lastName": "Last", "affiliation": "Last laboratory, Beijing, China"}
            ]}},
            {"doi": "10.1234/other", "title": "Unrelated paper", "authorList": {"author": [
                {"lastName": "Other", "affiliation": "Other laboratory, Germany"}
            ]}}
        ]}}
        with patch.object(europe_pmc, "get", return_value=response) as request:
            lookup = europe_pmc.last_author_metadata(["10.1234/fixture"])
        self.assertEqual(lookup, {"10.1234/fixture": [{"address": "Last laboratory, Beijing, China"}]})
        self.assertIn('DOI:"10.1234/fixture"', request.call_args.kwargs["params"]["query"])

    def test_model_rejects_wrong_country_roles_and_fabricated_quotes(self, _):
        supplied = "The study recruited participants in Germany."
        items = {"paper": Item("Fixture paper", summary=supplied)}
        for country, role, quote in (
            ("FR", "study_site", supplied),
            ("DE", "trial_site", supplied),
            ("DE", "institution", supplied),
            ("DE", "study_site", "The study recruited patients in Germany."),
        ):
            with self.subTest(country=country, role=role, quote=quote):
                chat = Mock(return_value=message([{"id": "0", "country": country, "role": role,
                                                  "evidence": quote}]))
                self.assertEqual(locate_items(items, chat=chat),
                                 {"places": [], "unknown": ["paper"], "deferred": ["paper"]})
        chat = Mock(return_value={"content": "Provider interrupted"})
        self.assertEqual(locate_items(items, chat=chat)["deferred"], ["paper"])

    def test_cache_tracks_content_and_reuses_positive_and_negative_results(self, _):
        event = "The organizers held a meeting in Germany."
        items = {"old": Item("Meeting", kind="conference", summary=event)}
        with TemporaryDirectory() as directory:
            yields = [{"id": "0", "country": "DE", "role": "event", "evidence": event}]
            chat = Mock(return_value=message(yields))
            first = locate_items(items, chat=chat, cache_dir=directory)
            self.assertEqual(first["places"][0]["id"], "old")
            again = locate_items({"new": items["old"]}, chat=chat, cache_dir=directory)
            self.assertEqual(again["places"][0]["id"], "new")
            chat.assert_called_once()
            chat.return_value = message([])
            items["old"].summary = "The organizers held a different meeting in Germany."
            self.assertEqual(locate_items(items, chat=chat, cache_dir=directory)["unknown"], ["old"])
            locate_items(items, chat=chat, cache_dir=directory)
            self.assertEqual(chat.call_count, 2)

    def test_model_budget_leaves_unprocessed_items_visible(self, _):
        items = {str(i): Item(f"Event {i}", kind="news", summary="They held a meeting in France.")
                 for i in range(26)}
        chat = Mock(return_value=message([]))
        result = locate_items(items, chat=chat)
        self.assertEqual(chat.call_count, 4)
        self.assertTrue(all(len(json.loads(call.args[0][1]["content"])) <= 6
                            for call in chat.call_args_list))
        self.assertEqual(result["deferred"], ["24", "25"])
        self.assertEqual(result["unknown"], list(items))
