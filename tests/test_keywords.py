import unittest

from neurodaily.config import DEFAULT_CONFIG
from neurodaily.keywords import keyword_cloud
from neurodaily.models import Item


class KeywordCloudTests(unittest.TestCase):
    def test_synonyms_count_once_per_item_and_preserve_canonical_ids(self):
        items = {
            "doi:10.1/001": Item("ＩＣＵ and intensive care units", summary="ICU, ICU",
                                  tags=["ICU", "top-journal"], source="pubmed",
                                  extra={"keywords": ["Intensive Care Unit"], "mesh_terms": ["Humans"]}),
            "pmid:20": Item("New study of ICU outcomes", extra={"abstract": "Intensive care unit results."}),
            "nct:NCT0305": Item("Feasibility assessment", kind="trial",
                                 extra={"conditions": ["Intensive Care Units"]}),
            "url:unrelated": Item("Icumen encountered")
        }
        cloud = {row["term"]: row for row in keyword_cloud(items)}
        self.assertEqual(cloud["intensive care unit"], {
            "term": "intensive care unit", "count": 3,
            "entries": ["doi:10.1/001", "nct:NCT0305", "pmid:20"],
        })
        for word in ("icu", "top journal", "pubmed", "humans", "and", "study", "outcomes"):
            self.assertNotIn(word, cloud)

    def test_chinese_cyrillic_and_configured_topics_keep_word_boundaries(self):
        config = DEFAULT_CONFIG()
        config.global_keywords = ["cortical microcircuits", "胸腔压变化"]
        items = {
            "zh1": Item("重症监护室机械通气患者的胸腔压变化研究"),
            "zh2": Item("机械通气与重症監護"),
            "ru1": Item("Сепсис: новый подход к интенсивной терапии"),
            "ru2": Item("Интенсивная терапия при сепсисе", extra={"keywords": ["Сепсис"]}),
            "en1": Item("Cortical microcircuits and working memory"),
            "en2": Item("Parallel circuits", summary="Microcircuits adjacent to cortical structures."),
        }
        cloud = {row["term"]: row for row in keyword_cloud(items, config)}
        self.assertEqual(cloud["重症监护"]["count"], 2)
        self.assertEqual(cloud["机械通气"]["entries"], ["zh1", "zh2"])
        self.assertEqual(cloud["胸腔压变化"]["entries"], ["zh1"])
        self.assertEqual(cloud["интенсивная терапия"]["count"], 2)
        self.assertEqual(cloud["сепсис"]["entries"], ["ru2", "ru1"])
        self.assertEqual(cloud["cortical microcircuits"]["count"], 1)
        self.assertNotIn("исследование", cloud)
        self.assertNotIn("研究", cloud)

    def test_representatives_prioritize_evidence_and_are_bounded(self):
        core = {
            "abstract": Item("Design", summary="Sepsis analysis"),
            "title": Item("Sepsis analysis"),
            "title:match": Item("Sepsis", extra={"matched_rules": ["TS=sepsis"]}),
        }
        items = {**core, **{f"metadata:{i}": Item("Design", extra={"keywords": ["Sepsis"]}) for i in range(7)}}
        cloud = keyword_cloud(items)
        self.assertEqual(cloud[0], {
            "term": "sepsis", "count": 10, "entries": [f"metadata:{i}" for i in range(5)],
        })
        self.assertEqual(keyword_cloud(items), cloud)
        self.assertEqual(keyword_cloud(core)[0]["entries"], ["title:match", "title", "abstract"])

    def test_malformed_optional_metadata_falls_back_to_summary(self):
        items = {"r1": Item("<strong>Working Memory</strong>", summary="Deep learning",
                            extra={"abstract": 3, "keywords": [None, 3]})}
        self.assertEqual({row["term"] for row in keyword_cloud(items)}, {"working memory", "deep learning"})
        self.assertEqual(keyword_cloud({}), [])

    def test_number_of_displayed_terms_is_bounded(self):
        items = {f"p:{i}": Item("Results", extra={"keywords": [f"marker{i}"]}) for i in range(60)}
        cloud = keyword_cloud(items)
        self.assertEqual(len(cloud), 36)
        self.assertTrue(all(row["count"] == 1 and row["entries"][0] in items for row in cloud))


if __name__ == "__main__":
    unittest.main()
