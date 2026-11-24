import hashlib
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from neurodaily.webapp import create_app


class OptimizationWorkbenchTests(unittest.TestCase):
    def test_local_workbench_preserves_manual_preview_and_serves_pinned_deep_chat(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(str(Path(tmp) / "config.json")))
            page = BeautifulSoup(client.get("/settings").text, "html.parser")
            advanced = page.select_one('section[aria-labelledby="advanced_search_title"]')
            self.assertIsNotNone(advanced.select_one("#search_preview_button"))
            workbench = advanced.select_one("#optimization-workbench")
            self.assertIsNotNone(workbench.select_one('input[role="switch"][checked]'))
            self.assertIsNotNone(workbench.select_one('label[for="optimization-text"]'))
            self.assertIsNotNone(workbench.select_one("#optimization-status[role='status']"))
            limits = workbench.select_one("#optimization-max-sources")
            self.assertEqual((limits["min"], limits["max"], limits["value"]), ("1", "14", "10"))
            script = page.select_one('script[src$="/optimization/workbench.js"]')
            self.assertEqual(script["type"], "module")
            self.assertEqual(client.get(script["src"]).status_code, 200)
            bundle = client.get("/static/optimization/deep-chat.js")
            self.assertEqual(bundle.status_code, 200)
            self.assertEqual(
                hashlib.sha256(bundle.content).hexdigest(),
                "6844eaf354e19d50dcdd8ee78968d6ae32ccd4b9f15a883902d60e93d69caf84",
            )
            license_text = client.get("/static/optimization/DEEP-CHAT-LICENSE.txt").text
            self.assertIn("Copyright (c) 2024 Ovidijus Parsiunas", license_text)
