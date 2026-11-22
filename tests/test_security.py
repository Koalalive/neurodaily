import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from neurodaily.security import validate_http_url, validate_label, within


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

    def test_output_must_stay_inside_root(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertTrue(within(root, root / "report.html"))
            self.assertFalse(within(root, root / ".." / "outside.html"))


if __name__ == "__main__":
    unittest.main()
