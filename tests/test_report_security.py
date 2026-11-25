"""Report CSP protects stored files while allowing the packaged UI scripts."""

import re
from unittest import TestCase

from neurodaily import demo
from neurodaily.render import render_html
from neurodaily.report_security import protect_report


class ReportSecurityTests(TestCase):
    def test_current_report_preserves_navigation_and_interactivity(self):
        for language in ("zh", "en", "ru"):
            with self.subTest(language=language):
                rendered = render_html(demo.build_result(), locale=language)
                protected, headers = protect_report(rendered, language)
                nonce = re.search(r"script-src 'nonce-([^']+)'", headers["Content-Security-Policy"])[1]
                self.assertIn("frame-ancestors 'self'", headers["Content-Security-Policy"])
                self.assertIn("object-src 'none'", headers["Content-Security-Policy"])
                self.assertEqual(headers["Referrer-Policy"], "no-referrer")
                self.assertIn('type="application/json" id="nd-research-data"', protected)
                self.assertGreaterEqual(protected.count(f'<script nonce="{nonce}">'), 3)
                self.assertIn('href="https://', protected)
                self.assertNotEqual(headers["Content-Security-Policy"],
                                    protect_report(rendered, language)[1]["Content-Security-Policy"])

    def test_legacy_report_recovers_map_and_discards_unrecognized_code(self):
        saved = """<!doctype html><html><head><meta http-equiv="refresh" content="0">
            <base href="https://example.test"></head><body>
            <script type="application/json" id="nd-research-data">{"points":[]}</script>
            <script>window.unrecognizedFixture = true;</script>
            <a href="javascript:void(0)" onclick="return false">Blocked link</a>
            <a href="/settings">Settings</a><a href="#papers">Papers</a>
            <a href="https://example.test/?x=1&amp;y=2">Paper link</a>
            <script src="/static/report/feedback.js"></script></body></html>"""
        protected, _ = protect_report(saved, "en")
        self.assertNotIn("window.unrecognizedFixture", protected)
        self.assertNotIn("javascript:void", protected)
        self.assertNotIn('onclick="return false"', protected)
        self.assertNotIn("http-equiv", protected)
        self.assertNotIn("<base", protected)
        self.assertNotIn("feedback.js", protected)
        self.assertIn('href="/settings"', protected)
        self.assertIn('href="#papers"', protected)
        self.assertIn('href="https://example.test/?x=1&amp;y=2"', protected)
        self.assertRegex(protected, r'<script nonce="[^"]+">')
