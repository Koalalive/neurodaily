import unittest

from neurodaily.geo_places import city_candidates


class CityGazetteerTests(unittest.TestCase):
    def test_country_disambiguates_only_verified_rows(self):
        evidence = "The study recruited participants in Cambridge."
        self.assertEqual(city_candidates(evidence), [])
        self.assertEqual(city_candidates(evidence, "US", city="Cambridge"), [])
        self.assertEqual(city_candidates(evidence, "GB", city="Cambridge"),
                         [{"name": "Cambridge", "country": "GB", "lat": 52.2, "lon": 0.117}])
        cambridge_nz, = city_candidates(evidence, "NZ")
        self.assertLess(cambridge_nz["lat"], 0)
        self.assertEqual(city_candidates("Participants were recruited in Alexandria.", "US"), [])

    def test_affiliation_requires_city_address_not_institution_name(self):
        research = "The data were collected at Cambridge University, United Kingdom."
        self.assertEqual(city_candidates(research, "GB", city="Cambridge"), [])
        address = "Department of Biochemistry, University of Cambridge, Cambridge, United Kingdom"
        self.assertEqual([point["name"] for point in city_candidates(address, "GB")], ["Cambridge"])
        boston = "Fixture Research Laboratory, Boston MA 02115, United States"
        self.assertEqual([point["name"] for point in city_candidates(boston, "US")], ["Boston"])
        self.assertEqual(city_candidates("Fixture Boston Scientific unit, United States", "US"), [])

    def test_han_city_names_require_location_context(self):
        self.assertEqual(city_candidates("本研究在北京大学开展。", "CN", city="Beijing"), [])
        self.assertEqual(city_candidates("本研究在吉林省开展。", "CN"), [])
        self.assertEqual([point["name"] for point in city_candidates("本研究在北京市海淀区开展。", "CN",
                                                                     city="Beijing")], ["Beijing"])
        self.assertEqual([point["name"] for point in city_candidates("本研究在吉林市开展。", "CN")], ["Jilin"])

    def test_common_words_country_names_and_state_city_ambiguities(self):
        self.assertEqual(city_candidates("The researchers found nice improvements in France.", "FR"), [])
        self.assertEqual([point["name"] for point in city_candidates("A conference was held in Nice, France.", "FR")],
                         ["Nice"])
        self.assertEqual(city_candidates("The event was held in Singapore.", "SG"), [])
        self.assertEqual(city_candidates("The event was held in Washington, United States.", "US"), [])
        point, = city_candidates("The event was held in Washington, D.C., United States.", "US")
        self.assertAlmostEqual(point["lat"], 38.9, places=1)

    def test_model_hint_cannot_create_a_city_or_match_a_substring(self):
        self.assertEqual(city_candidates("The paper was held in Berkeley, United States.", "US", city="Boston"), [])
        self.assertEqual(city_candidates("We recruited in New York City, United States.", "US", city="York"), [])
        self.assertEqual(city_candidates("This stage was new. York later examined it.", "US", city="New York"), [])
        self.assertEqual(city_candidates("We recruited in York, United Kingdom.", "GB", city="York")[0]["name"], "York")
        self.assertEqual(city_candidates("We recruited in Boston, United States.", "ZZ"), [])
