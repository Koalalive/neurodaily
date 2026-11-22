import unittest

from neurodaily.digest import DigestResult
from neurodaily.models import Item
from neurodaily.topic_map import available, build_topics, tokenize


class TopicMapTests(unittest.TestCase):
    def test_tokenizer_handles_mixed_text(self):
        tokens = tokenize("Deep brain stimulation 用于抑郁症 treatment")
        self.assertIn("brain", tokens)
        self.assertIn("stimulation", tokens)
        self.assertTrue(any("\u4e00" <= char <= "\u9fff" for token in tokens for char in token))

    @unittest.skipUnless(available(), "scikit-learn is optional")
    def test_builds_bilingual_lda_tsne_map(self):
        docs = []
        for index in range(12):
            title = f"Deep brain stimulation depression trial {index}" if index % 2 else f"抑郁症 脑刺激 治疗 {index}"
            docs.append(Item(title, summary="treatment response and cortical activity"))
        result = DigestResult(items=docs, sections={"papers": docs, "industry": [],
                                                    "trials_conferences": [], "policy": []},
                              health=[], generated_at="2026-11-23T08:00:00",
                              config_profile="fixture")
        data = build_topics(result, force=True)
        self.assertIsNotNone(data)
        self.assertEqual(len(data["points"]), 12)
        self.assertGreaterEqual(len(data["topics"]), 2)
        self.assertTrue(all("url" in point and "x" in point for point in data["points"]))


if __name__ == "__main__":
    unittest.main()
