import unittest
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx

from neurodaily.security import validate_http_url, validate_label, within
from neurodaily.sources.http import _SourceTransport


class SecurityGuardTests(unittest.TestCase):
    def test_private_and_local_sources_are_blocked(self):
        for url in ("http://127.0.0.1:8080/feed", "http://localhost/feed",
                    "http://10.0.0.8/feed", "http://169.254.169.254/latest"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    validate_http_url(url, resolve=False)
        self.assertEqual(validate_http_url("https://example.test/feed", resolve=False),
                         "https://example.test/feed")

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


if __name__ == "__main__":
    unittest.main()
