import json
import unittest
from unittest.mock import Mock, patch

from neurodaily.digest import DigestResult
from neurodaily.models import Item
from neurodaily.demo import build_result
from neurodaily.topic_map import _labels, available, build_topics, enrich_topics, tokenize


class TopicMapTests(unittest.TestCase):
    def test_model_annotations_are_language_specific_and_skip_empty_topics(self):
        topics = [{"id": 0, "size": 4, "label": "default", "terms": ["stimulation"], "examples": ["A study"]},
                  {"id": 1, "size": 0, "label": "empty", "terms": [], "examples": []}]
        chat = Mock(return_value={"content": json.dumps([{"id": 0,
            "zh": {"label": "脑刺激", "description": "研究脑刺激与运动控制。"},
            "en": {"label": "Brain stimulation", "description": "Studies of brain stimulation and movement."}}])})
        _labels(topics, chat)
        self.assertEqual(topics[0]["labels"]["zh"], "脑刺激")
        self.assertEqual(topics[0]["labels"]["ru"], "default")
        self.assertIn("movement", topics[0]["descriptions"]["en"])
        self.assertEqual(topics[1]["descriptions"], {})
        self.assertEqual([row["id"] for row in json.loads(chat.call_args.args[0][1]["content"])], [0])

    def test_annotation_switch_leaves_local_model_available(self):
        result = build_result()
        result.config.output["topic_ai_labels"] = False
        with patch("neurodaily.topic_map.build_topics", return_value={"enabled": True}) as build, \
             patch("neurodaily.ai_summary.load_cfg") as settings:
            self.assertTrue(enrich_topics(result))
        settings.assert_not_called()
        self.assertIsNone(build.call_args.kwargs["chat"])

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
