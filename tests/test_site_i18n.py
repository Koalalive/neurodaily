from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SiteI18nTests(unittest.TestCase):
    def test_language_switch_and_reference_paragraph_removed(self):
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "docs" / "site.js").read_text(encoding="utf-8")
        for lang in ("zh", "en", "ru"):
            self.assertIn(f'data-lang="{lang}"', html)
        self.assertIn('data-i18n="hero_title"', html)
        self.assertNotIn("Python 负责检索与定时任务", html)
        self.assertIn("Traceable research digest", js)
        self.assertIn("Ежедневный научный дайджест", js)
