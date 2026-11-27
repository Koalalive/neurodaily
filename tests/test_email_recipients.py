from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from neurodaily import delivery, delivery_receipts, history, mailer
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
        for language, marker in (("zh", "最新论文"), ("en", "Latest Papers"),
                                 ("ru", "Новые публикации")):
            subject, html, _ = mailer.render_email(result(), {"attach_report": False,
                                                                "language": language},
                                                    language=language)
            self.assertIn(marker, html)
            self.assertTrue(subject)

    def test_email_uses_language_specific_ai_summary(self):
        item = Item("Example paper", kind="paper")
        digest = result()
        digest.ai_summary = "中文摘要"
        digest.ai_summaries = {"zh": "中文摘要", "en": "English summary", "ru": "Русское резюме"}
        _, html, text = mailer.render_email(digest, {"attach_report": False}, language="en")
        self.assertIn("English summary", html)
        self.assertIn("English summary", text)
        self.assertNotIn("中文摘要", html)

    def test_email_html_is_report_style_without_canvas_or_backend_controls(self):
        subject, html, _ = mailer.render_email(result(), {"attach_report": False}, language="zh")
        self.assertTrue(subject)
        self.assertIn('href="#papers"', html)
        for marker in ('id="research-activity"', 'id="topic-map"', 'id="prompt"'):
            self.assertNotIn(marker, html)
        for marker in ('id="runNow"', 'id="settingsLink"', 'id="histLink"'):
            self.assertNotIn(marker, html)

    def test_future_push_time_is_queued(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "queue.json"
            with (patch.object(delivery, "_queue_path", return_value=path),
                  patch.object(history, "db_path", return_value=str(path.with_suffix(".db")))):
                self.assertTrue(delivery._future_due({"time": "23:59"}, datetime(2026, 11, 23, 8, 0)))
                self.assertFalse(delivery._future_due({"time": "08:00"}, datetime(2026, 11, 23, 8, 0)))
                run_id = str(history.record_run("fixture", "fixture", "completed", "2026-11-23T08:00",
                                                "2026-11-23T08:00"))
                address = "a@example.org"
                delivery_receipts.prepare(run_id, "fixture",
                                          [(delivery._destination("email", address), "email", "email 1")])
                delivery._queue_email(run_id, "/tmp/report.html", "fixture",
                                      {"address": "a@example.org", "language": "en"}, "2026-11-23T23:59")
                rows = delivery._read_queue()
                self.assertEqual(rows[0]["language"], "en")
                delivery._queue_email(run_id, "/tmp/report.html", "fixture",
                                      {"address": "a@example.org", "language": "en"}, "2026-11-23T23:59")
                self.assertEqual(len(delivery._read_queue()), 1)
                self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
