import unittest
from unittest.mock import patch

from neurodaily import ai_summary
from neurodaily.digest import DigestResult
from neurodaily.models import Item


class AiSummaryLanguageTests(unittest.TestCase):
    def test_generate_all_keeps_each_language(self):
        result = DigestResult(items=[Item("Paper")], sections={"papers": []},
                              health=[], generated_at="2026-11-23T08:00:00",
                              config_profile="fixture")
        calls = []

        def fake_generate(_result, _cfg=None, **kwargs):
            calls.append(kwargs.get("language"))
            return f"summary-{kwargs.get('language')}"

        with patch.object(ai_summary, "generate", side_effect=fake_generate):
            out = ai_summary.generate_all(result, {"enabled": True})
        self.assertEqual(out["en"], "summary-en")
        self.assertEqual(set(out), {"zh", "en", "ru"})
        self.assertEqual(result.ai_summaries["ru"], "summary-ru")


if __name__ == "__main__":
    unittest.main()
