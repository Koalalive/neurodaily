from datetime import datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from neurodaily import delivery, mailer
from neurodaily.config import Config
from neurodaily.digest import DigestResult
from neurodaily.models import Item


def result():
    item = Item("Example paper", kind="paper")
    return DigestResult(items=[item], sections={"papers": [item], "industry": [],
                                                "trials_conferences": [], "policy": []},
                        health=[], generated_at=datetime.now().isoformat(),
                        config_profile="fixture", config=Config.load())


class EmailRecipientTests(unittest.TestCase):
    def test_legacy_to_and_per_recipient_settings(self):
        legacy = mailer.recipients({"to": ["a@example.org", "b@example.org"]})
        self.assertEqual([row["language"] for row in legacy], ["zh", "zh"])
        configured = mailer.recipients({"recipients": [
            {"address": "a@example.org", "time": "09:30", "language": "en"},
            {"address": "b@example.org", "time": "", "language": "ru"},
        ]})
        self.assertEqual(configured[0]["time"], "09:30")
        self.assertEqual(configured[1]["language"], "ru")

    def test_email_subject_and_body_language(self):
        for language, marker in (("zh", "最新论文"), ("en", "Latest papers"),
                                 ("ru", "Новые публикации")):
            subject, html, _ = mailer.render_email(result(), {"attach_report": False,
                                                                "language": language},
                                                    language=language)
            self.assertIn(marker, html)
            self.assertTrue(subject)

    def test_future_push_time_is_queued(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "queue.json"
            with patch.object(delivery, "_queue_path", return_value=path):
                self.assertTrue(delivery._future_due({"time": "23:59"}, datetime(2026, 11, 23, 8, 0)))
                self.assertFalse(delivery._future_due({"time": "08:00"}, datetime(2026, 11, 23, 8, 0)))
                delivery._queue_email("7", "/tmp/report.html", "fixture",
                                      {"address": "a@example.org", "language": "en"}, "2026-11-23T23:59")
                rows = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(rows[0]["language"], "en")
                delivery._queue_email("7", "/tmp/report.html", "fixture",
                                      {"address": "a@example.org", "language": "en"}, "2026-11-23T23:59")
                self.assertEqual(len(json.loads(path.read_text(encoding="utf-8"))), 1)


if __name__ == "__main__":
    unittest.main()
