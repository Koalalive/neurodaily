import unittest
import os
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx

from neurodaily.security import external_url, public_addresses, trusted_fake_ip_host, validate_http_url, validate_label, within
from neurodaily.sources.http import _SourceTransport


class SecurityGuardTests(unittest.TestCase):
    def test_report_links_require_http_without_credentials(self):
        unsafe = ("javascript:void(0)", "data:text/plain,fixture", "//example.test",
                  "https://user:pass@example.test", "https://example.test:0", "https://example.test/\titem")
        for url in unsafe:
            with self.subTest(url=url):
                self.assertEqual(external_url(url), "")
        self.assertEqual(external_url("https://example.test/p?q=one&x=two"),
                         "https://example.test/p?q=one&x=two")

    def test_private_and_local_sources_are_blocked(self):
        for url in ("http://127.0.0.1:8080/feed", "http://localhost/feed",
                    "http://10.0.0.8/feed", "http://169.254.169.254/latest"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    validate_http_url(url, resolve=False)
        self.assertEqual(validate_http_url("https://example.test/feed", resolve=False),
                         "https://example.test/feed")

    def test_trusted_feed_hosts_allow_fake_ip_only(self):
        def fake_dns(host, port, **kwargs):
            address = "198.18.0.157" if host == "www.nature.com" else "198.18.0.160"
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (address, port))]

        self.assertTrue(trusted_fake_ip_host("www.nature.com"))
        self.assertFalse(trusted_fake_ip_host("evil.example"))
        with patch("neurodaily.security.socket.getaddrinfo", side_effect=fake_dns):
            self.assertEqual(public_addresses("www.nature.com", 443, allow_fake_ip=True),
                             ("198.18.0.157",))
            with self.assertRaises(ValueError):
                public_addresses("www.nature.com", 443, allow_fake_ip=False)
            with self.assertRaises(ValueError):
                public_addresses("evil.example", 443, allow_fake_ip=True)

    def test_schedule_label_rejects_paths(self):
        self.assertEqual(validate_label("com.neurodaily.daily"), "com.neurodaily.daily")
        for value in ("../evil", "a/b", "a..b", ""):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_label(value)

    def test_source_transport_pins_validated_addresses_and_checks_each_request(self):
        def dns(host, port, **kwargs):
            address = "93.184.216.34" if host == "public.example.test" else "192.0.2.12"
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (address, port))]

        def upstream(request):
            self.assertEqual(request.url.host, "93.184.216.34")
            self.assertEqual(request.headers["Host"], "public.example.test")
            self.assertEqual(request.extensions["sni_hostname"], "public.example.test")
            return httpx.Response(302, headers={"location": "https://different.example.test/"})

        with patch("neurodaily.security.socket.getaddrinfo", side_effect=dns), \
             patch.object(httpx.HTTPTransport, "handle_request", side_effect=upstream) as sent, \
             httpx.Client(transport=_SourceTransport(), follow_redirects=True) as client:
            with self.assertRaises(httpx.RequestError):
                client.get("https://public.example.test/feed")
            sent.assert_called_once()

    def test_output_must_stay_inside_root(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertTrue(within(root, root / "report.html"))
            self.assertFalse(within(root, root / ".." / "outside.html"))

    def test_webhook_checks_dns_at_delivery_despite_local_source_override(self):
        from neurodaily import webhooks

        url = "https://hook.example.test/send?key=fixture-secret"

        def dns(host, port, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (dns.address, port))]

        dns.address = "93.184.216.34"
        with patch("neurodaily.security.socket.getaddrinfo", side_effect=dns), \
             patch.dict(os.environ, {"NEURODAILY_ALLOW_PRIVATE_SOURCES": "1"}), \
             patch.object(httpx.HTTPTransport, "handle_request") as send:
            self.assertEqual(webhooks.normalize_updates({"wecom": url}), {"wecom": url})
            dns.address = "127.0.0.1"
            with self.assertRaisesRegex(ValueError, "Webhook 推送失败") as error:
                webhooks.send_wecom(url, "test")
            self.assertNotIn("fixture-secret", str(error.exception))
            send.assert_not_called()

    def test_webhook_pins_https_and_does_not_follow_redirects(self):
        from neurodaily import webhooks

        url = "https://hook.example.test/send?key=fixture-secret"

        def dns(host, port, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", port))]

        def redirect(request):
            self.assertEqual(request.url.host, "93.184.216.34")
            self.assertEqual(request.headers["Host"], "hook.example.test")
            self.assertEqual(request.extensions["sni_hostname"], "hook.example.test")
            return httpx.Response(302, headers={"location": "https://other.example.test/"})

        with patch("neurodaily.security.socket.getaddrinfo", side_effect=dns), \
             patch.object(httpx.HTTPTransport, "handle_request", side_effect=redirect) as send:
            with self.assertRaisesRegex(ValueError, "Webhook 推送失败") as error:
                webhooks.send_feishu(url, "test")
            self.assertNotIn("fixture-secret", str(error.exception))
            send.assert_called_once()

    def test_push_api_reports_status_and_keeps_unedited_webhooks(self):
        import json

        from fastapi.testclient import TestClient

        from neurodaily.config import DEFAULT_CONFIG, DEFAULT_DIRS
        from neurodaily.webapp import create_app

        with TemporaryDirectory() as directory, patch.dict(DEFAULT_DIRS, {"output": directory}):
            config = DEFAULT_CONFIG().save(str(Path(directory) / "config.json"))
            file = Path(directory) / "webhooks.json"
            file.write_text('{"feishu":"https://hook.example.test/?key=fixture-secret",'
                            '"wecom":"https://other.example.test/?key=other-secret"}', encoding="utf-8")
            client = TestClient(create_app(config))
            with patch("neurodaily.webhooks.CFG_PATH", str(file)):
                response = client.get("/api/push")
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertNotIn("secret", response.text)
                self.assertTrue(response.json()["webhooks"]["feishu_configured"])
                response = client.post("/api/push", json={"webhooks": {"feishu": ""}})
                self.assertFalse(response.json()["webhooks"]["feishu_configured"])
                self.assertTrue(response.json()["webhooks"]["wecom_configured"])
                self.assertNotIn("secret", response.text)
                saved = json.loads(file.read_text(encoding="utf-8"))
                self.assertEqual(saved["feishu"], "")
                self.assertTrue(saved["wecom"].endswith("other-secret"))


if __name__ == "__main__":
    unittest.main()
