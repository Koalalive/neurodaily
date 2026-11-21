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
        self.assertEqual(len(points), 3)
        self.assertEqual(points["paper", "institution"]["country"], "FR")
        self.assertEqual(points["paper", "study_site"]["evidence"], study)
        self.assertEqual((points["paper", "study_site"]["lat"], points["paper", "study_site"]["lon"]),
                         (51, 10))
        self.assertEqual(points["event", "event"]["method"], "model")

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
