import unittest
from unittest.mock import patch

from neurodaily.bibliometrics import _publication_period, render_bibliometrics
from neurodaily.config import Config, DEFAULT_CONFIG
from neurodaily.digest import DigestResult
from neurodaily.models import Item
from neurodaily.onthisday import is_enabled
from neurodaily.presets import research_presets
from neurodaily.render import render_html


class BibliometricsTests(unittest.TestCase):
    def test_dates_keep_known_precision_and_exclude_invalid_values(self):
        self.assertEqual(_publication_period("2025-02-11T11:25:30Z"), "2025-02")
        self.assertEqual(_publication_period("2024-02"), "2024-02")
        self.assertEqual(_publication_period("2023"), "2023")
        self.assertEqual(_publication_period("2025-02-29"), "")
        self.assertEqual(_publication_period("2025-13"), "")
        self.assertEqual(_publication_period("winter 2025"), "")

    def test_counts_escaped_names_and_filters_publication_year(self):
        preset = next(row["config"] for row in research_presets() if row["config"]["profile"] == "critical-care")
        config = Config.from_dict(preset)
        self.assertFalse(is_enabled(config))
        result = DigestResult(
            items=[
                Item("paper 1", date="2025-01-04", source="pubmed", authors=["A. Li", "a. li"],
                     extra={"journal": "Intensive Care Med"}),
                Item("paper 2", date="2024-02", source="journal", authors=["A. Li", "<svg/onload=test>"],
                     extra={"journal": "Intensive Care Medicine"}),
                Item("paper 3", source="pubmed"),
                Item("trial", date="2023-02-03", source="trials", kind="trial"),
            ],
            sections={}, health=[], generated_at="2025-01-05T10:00:00", config=config,
        )
        html = render_html(result, locale="en-US")
        start = html.index('id="bibliometrics"')
        panel = html[start:html.index("</script>", start)]
        all_papers = panel[panel.index('data-bib-period="all"'):panel.index('data-bib-period="2025"')]
        self.assertIn("Bibliometrics <b>3</b>", panel)
        self.assertIn('value="unknown">Unknown year', panel)
        self.assertIn('data-bib-period="2024" hidden', panel)
        self.assertNotIn('data-bib-period="2023"', panel)
        self.assertIn("With publication year <b>2</b>", all_papers)
        self.assertIn(">Intensive Care Medicine</th>", all_papers)
        self.assertNotIn(">Intensive Care Med</th>", all_papers)
        self.assertIn('max="2" value="2"></meter></td><td>2</td>', all_papers)
        self.assertIn("&lt;svg/onload=test&gt;", all_papers)
        self.assertNotIn("<svg/onload=test>", panel)
        self.assertIn("critical care digest", html)

    def test_empty_statistics_remain_available_offline_and_in_plain_report(self):
        self.assertIn("В этом отчёте нет статей.", render_bibliometrics([], locale="ru"))
        result = DigestResult(items=[], sections={}, health=[], generated_at="", config=DEFAULT_CONFIG())
        with patch("neurodaily.render._stdlib_loader", return_value=None):
            html = render_html(result, locale="ru")
        self.assertIn("Библиометрия", html)
        self.assertIn('id="bibliometrics"', html)
