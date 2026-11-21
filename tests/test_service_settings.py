"""Offline coverage for settings persistence and service probes."""

import json
import smtplib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from neurodaily import ai_summary, mailer
from neurodaily.webapp import create_app


class ServiceSettingsTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.ai_path = self.root / "ai_summary.json"
        self.ai_path.write_text(json.dumps({
            **ai_summary.DEFAULT_CFG,
            "api_key_env": "NEURODAILY_TEST_UNSET_MODEL_KEY",
            "api_key_file": str(self.root / "legacy_key"),
        }), encoding="utf-8")
        path_patch = patch.object(ai_summary, "CFG_PATH", str(self.ai_path))
        path_patch.start()
        self.addCleanup(path_patch.stop)
        self.client = TestClient(create_app(str(self.root / "config.json")))

    def test_ai_settings_keeps_key_private_and_blank_does_not_reset_it(self):
        data = {"base_url": "https://example.test/v1/chat/completions", "model": "fixture", "api_key": "secret-model-key"}
        saved = self.client.post("/api/ai/settings", json=data)
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["base_url"], "https://example.test/v1")
        self.assertEqual(ai_summary.api_key(), "secret-model-key")
        self.assertEqual(self.client.post("/api/ai/settings", json={"enabled": False}).status_code, 200)
        public = self.client.get("/api/ai/settings")
        self.assertFalse(public.json()["enabled"])
        self.assertEqual(public.json()["key_source"], "settings")
        self.assertNotIn("secret-model-key", saved.text + public.text)
        self.assertEqual(ai_summary.api_key(), "secret-model-key")
        self.assertEqual(self.client.post("/api/ai/settings", json={"base_url": "https://other.test/v1"}).status_code, 400)

    def test_ai_probe_uses_draft_and_sends_only_the_probe_message(self):
        original = self.ai_path.read_bytes()
        request = httpx.Request("POST", "https://example.test/v1/chat/completions")
        response = httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]}, request=request)
        with patch.object(ai_summary.httpx, "post", return_value=response) as post:
            reply = self.client.post("/api/ai/test", json={"base_url": "https://example.test/v1", "model": "draft-model", "api_key": "test-secret"})
        self.assertTrue(reply.json()["ok"])
        self.assertEqual(post.call_args.args[0], str(request.url))
        self.assertEqual(post.call_args.kwargs["json"]["model"], "draft-model")
        self.assertEqual(post.call_args.kwargs["json"]["messages"], [{"role": "user", "content": "Reply with OK."}])
        self.assertEqual(self.ai_path.read_bytes(), original)

    def test_ai_probe_classifies_credentials_errors_without_returning_service_body(self):
        response = httpx.Response(401, text="upstream secret", request=httpx.Request("POST", "https://example.test/v1/chat/completions"))
        with patch.object(ai_summary.httpx, "post", return_value=response):
            result = self.client.post("/api/ai/test", json={"base_url": "https://example.test/v1", "model": "draft", "api_key": "draft-key"})
        self.assertFalse(result.json()["ok"])
        self.assertIn("401", result.json()["message"])
        self.assertNotIn("secret", result.text)

    def test_smtp_probe_uses_draft_tls_and_never_sends_mail(self):
        with patch.object(mailer.smtplib, "SMTP_SSL") as ssl_client:
            result = self.client.post("/api/push/test", json={"smtp_host": "smtp.example.test", "smtp_port": 465,
                                      "use_ssl": True, "username": "draft-user", "password": "draft-password"})
        self.assertTrue(result.json()["ok"])
        self.assertEqual(ssl_client.call_args.args, ("smtp.example.test", 465))
        ssl_client.return_value.login.assert_called_once_with("draft-user", "draft-password")
        ssl_client.return_value.sendmail.assert_not_called()
        ssl_client.return_value.quit.assert_called_once()

    def test_smtp_probe_uses_starttls_then_reports_login_failure(self):
        with patch.object(mailer.smtplib, "SMTP") as client, \
             patch.object(mailer, "load_cfg", return_value=mailer.DEFAULT_CFG), \
             patch.object(mailer, "_password", return_value="stored-smtp-password"):
            client.return_value.login.side_effect = smtplib.SMTPAuthenticationError(535, b"provider secret")
            result = self.client.post("/api/push/test", json={})
        self.assertFalse(result.json()["ok"])
        self.assertIn("拒绝登录", result.text)
        self.assertNotIn("secret", result.text)
        self.assertEqual([call[0] for call in client.return_value.method_calls], ["starttls", "login", "quit"])

    def test_browser_cannot_use_a_plain_text_form_to_trigger_probe(self):
        with patch.object(ai_summary, "test_connection") as probe:
            response = self.client.post("/api/ai/test", content='{"model":"fixture"}',
                                        headers={"Content-Type": "text/plain"})
        self.assertEqual(response.status_code, 400)
        probe.assert_not_called()
