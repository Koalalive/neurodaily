"""Offline coverage for per-destination delivery receipts and retry."""

import json
import smtplib
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from threading import Event
from unittest.mock import patch

from neurodaily import delivery, delivery_receipts, history
from neurodaily.delivery import _destination, deliver_report, list_receipts, retry_delivery
from neurodaily.digest import DigestResult
from neurodaily.models import Item


class DeliveryReceiptTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        folder = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        self.report = str(folder / "report.html")
        paper = Item(title="Sample paper", url="https://example.test/paper", source="pubmed",
                     doi="10.1234/delivery-test")
        self.result = DigestResult(items=[paper], sections={"papers": [paper]}, health=[],
                                   generated_at="2026-11-21T12:00:00")
        self.email = {"enabled": False, "attach_report": False}
        self.hooks = {"wecom": "https://example.test/webhook?key=private-token"}
        stack.enter_context(patch("neurodaily.history.db_path", return_value=str(folder / "history.db")))
        stack.enter_context(patch("neurodaily.mailer.load_cfg", return_value=self.email))
        stack.enter_context(patch("neurodaily.mailer.render_email", return_value=("subject", "html", "text")))
        self.last_email = stack.enter_context(patch("neurodaily.mailer.save_last"))
        self.password = stack.enter_context(patch("neurodaily.mailer._password", return_value="password"))
        self.send_mail = stack.enter_context(patch("neurodaily.mailer.send_with_retry"))
        stack.enter_context(patch("neurodaily.webhooks.load_cfg", return_value=self.hooks))
        self.send_hook = stack.enter_context(patch("neurodaily.webhooks.send_all"))
        self.task_id = self.make_run()

    def make_run(self):
        date = self.result.generated_at
        return str(history.record_run("fixture", self.result.config_profile, "completed", date, date))

    def test_accepted_and_refused_email_are_distinct_and_only_refused_email_is_retried(self):
        address = "researcher@example.test"
        self.email.update(enabled=True, to=["lab@example.test", address])
        self.send_mail.side_effect = [None, smtplib.SMTPRecipientsRefused({address: (550, b"private error")})]
        self.send_hook.return_value = {"wecom": "ok"}
        self.assertEqual(deliver_report(self.result, self.report, task_id=self.task_id),
                         {"email 1": "ok", "email 2": "failed", "wecom": "ok"})
        rows = {row["label"]: row for row in list_receipts(self.task_id)}
        failure = rows["email 2"]
        self.assertEqual((failure["status"], failure["attempts"]), ("failed", 1))
        self.assertIn("拒绝该收件人", failure["error"])
        self.assertEqual(rows["email 1"]["status"], "accepted")
        self.assertEqual(rows["wecom"]["status"], "accepted")
        public_data = json.dumps(rows)
        for private in (address, "lab@example.test", "private-token", "private error"):
            self.assertNotIn(private, public_data)

        self.send_mail.side_effect = None
        with self.assertRaises(ValueError):
            retry_delivery(self.result, self.report, self.task_id, rows["email 1"]["destination"])
        updated = retry_delivery(self.result, self.report, self.task_id, failure["destination"])
        self.assertEqual((updated["status"], updated["attempts"], updated["error"]), ("accepted", 2, None))
        self.assertEqual(self.send_mail.call_count, 3)
        self.assertEqual(self.send_mail.call_args.args[3]["to"], [address])
        self.send_hook.assert_called_once()
        self.last_email.assert_called_once()

    def test_retry_refuses_changed_destination_and_does_not_expose_webhook_error(self):
        original = self.hooks["wecom"]
        self.send_hook.return_value = {"wecom": f"failed: request to {original}"}
        deliver_report(self.result, self.report, task_id=self.task_id)
        row, = list_receipts(self.task_id)
        self.assertEqual(row["status"], "failed")
        self.assertNotIn("private-token", json.dumps(row))

        self.hooks["wecom"] = "https://example.test/new?key=another-token"
        with self.assertRaisesRegex(ValueError, "移除或变更"):
            retry_delivery(self.result, self.report, self.task_id, row["destination"])
        self.send_hook.assert_called_once()
        self.assertEqual(list_receipts(self.task_id), [row])

    def test_dedup_applies_to_other_tasks_and_failed_receipts(self):
        self.send_hook.side_effect = [{"wecom": "failed"}, {"wecom": "ok"}]
        deliver_report(self.result, self.report, task_id=self.task_id)
        failed, = list_receipts(self.task_id)
        deliver_report(self.result, self.report, task_id=self.make_run())

        update = retry_delivery(self.result, self.report, self.task_id, failed["destination"])
        self.assertEqual((update["status"], update["attempts"]), ("no_new", 1))
        third = self.make_run()
        self.assertEqual(deliver_report(self.result, self.report, task_id=third), {})
        no_new, = list_receipts(third)
        self.assertEqual((no_new["status"], no_new["attempts"]), ("no_new", 0))
        self.assertEqual(self.send_hook.call_count, 2)

    def test_concurrent_retries_only_send_once(self):
        self.send_hook.return_value = {"wecom": "failed"}
        deliver_report(self.result, self.report, task_id=self.task_id)
        failed, = list_receipts(self.task_id)
        entered, release = Event(), Event()

        def slow_send(*_):
            entered.set()
            if not release.wait(5):
                raise TimeoutError
            return {"wecom": "ok"}

        self.send_hook.side_effect = slow_send
        with ThreadPoolExecutor(max_workers=1) as pool:
            active = pool.submit(retry_delivery, self.result, self.report, self.task_id, failed["destination"])
            try:
                self.assertTrue(entered.wait(5))
                self.assertEqual(list_receipts(self.task_id)[0]["status"], "sending")
                with self.assertRaises(ValueError):
                    retry_delivery(self.result, self.report, self.task_id, failed["destination"])
            finally:
                release.set()
            self.assertEqual(active.result(timeout=5)["status"], "accepted")
        self.assertEqual(self.send_hook.call_count, 2)

    def test_busy_destination_can_be_retried_after_its_lease_is_released(self):
        destination = _destination("wecom", self.hooks["wecom"])
        with history.delivery_lease(self.result.config_profile, destination) as acquired:
            self.assertTrue(acquired)
            self.assertEqual(deliver_report(self.result, self.report, task_id=self.task_id),
                             {"wecom": "failed"})
        failure, = list_receipts(self.task_id)
        self.assertEqual((failure["status"], failure["attempts"]), ("failed", 0))
        self.send_hook.assert_not_called()

        self.send_hook.return_value = {"wecom": "ok"}
        updated = retry_delivery(self.result, self.report, self.task_id, destination)
        self.assertEqual((updated["status"], updated["attempts"]), ("accepted", 1))

    def test_queued_email_keeps_its_pending_receipt_while_destination_is_busy(self):
        address = "lab@example.test"
        profile = self.result.config_profile
        destination = _destination("email", address)
        self.email.update(enabled=True, to=[address])
        delivery_receipts.prepare(self.task_id, profile, [(destination, "email", "email 1")])
        Path(self.report).write_text("<html>Queued report</html>", encoding="utf-8")
        queued = Path(self.report).with_name("queue.json")
        now = datetime.fromisoformat("2026-11-21T14:00:00")
        with (patch("neurodaily.delivery._queue_path", return_value=queued),
              patch("neurodaily.task_runs.load_result", return_value=self.result)):
            delivery._queue_email(self.task_id, self.report, profile,
                                  {"address": address}, "2026-11-21T13:00:00")
            with history.delivery_lease(profile, destination) as acquired:
                self.assertTrue(acquired)
                self.assertEqual(delivery.run_email_queue(now), {})
                self.assertEqual(len(delivery._read_queue()), 1)
            self.assertEqual(delivery.run_email_queue(now), {address: "ok"})
            self.assertEqual(delivery.run_email_queue(now), {})
        self.send_mail.assert_called_once()
        receipt, = list_receipts(self.task_id)
        self.assertEqual((receipt["status"], receipt["attempts"]), ("accepted", 1))

    def test_turning_off_email_pauses_an_existing_queue_entry(self):
        address = "lab@example.test"
        profile = self.result.config_profile
        destination = _destination("email", address)
        self.email.update(enabled=False, to=[address])
        delivery_receipts.prepare(self.task_id, profile, [(destination, "email", "email 1")])
        Path(self.report).write_text("<html>Queued report</html>", encoding="utf-8")
        queue_file = Path(self.report).with_name("queue.json")
        now = datetime.fromisoformat("2026-11-21T14:00:00")
        with (patch("neurodaily.delivery._queue_path", return_value=queue_file),
              patch("neurodaily.task_runs.load_result", return_value=self.result)):
            delivery._queue_email(self.task_id, self.report, profile,
                                  {"address": address}, "2026-11-21T13:00:00")
            self.assertEqual(delivery.run_email_queue(now), {})
            self.assertEqual(list_receipts(self.task_id)[0]["status"], "pending")
            self.send_mail.assert_not_called()
            self.email["enabled"] = True
            self.assertEqual(delivery.run_email_queue(now), {address: "ok"})
        self.send_mail.assert_called_once()

    def test_turning_off_email_during_preparation_keeps_the_entry_pending(self):
        address = "lab@example.test"
        profile = self.result.config_profile
        destination = _destination("email", address)
        self.email.update(enabled=True, to=[address])
        delivery_receipts.prepare(self.task_id, profile, [(destination, "email", "email 1")])
        Path(self.report).write_text("<html>Queued report</html>", encoding="utf-8")
        now = datetime.fromisoformat("2026-11-21T14:00:00")
        increment = delivery._increment

        def disable_during_preparation(*args):
            self.email["enabled"] = False
            return increment(*args)

        with (patch("neurodaily.delivery.mailer.load_cfg", side_effect=lambda: dict(self.email)),
              patch("neurodaily.task_runs.load_result", return_value=self.result),
              patch("neurodaily.delivery._increment", side_effect=disable_during_preparation)):
            delivery._queue_email(self.task_id, self.report, profile,
                                  {"address": address}, "2026-11-21T13:00:00")
            self.assertEqual(delivery.run_email_queue(now), {})
        self.send_mail.assert_not_called()
        receipt, = list_receipts(self.task_id)
        self.assertEqual((receipt["status"], receipt["attempts"]), ("pending", 0))

    def test_processing_a_due_email_does_not_overwrite_a_concurrent_enqueue(self):
        profile = self.result.config_profile
        first, second = "a@example.test", "b@example.test"
        second_task = self.make_run()
        self.email.update(enabled=True, to=[first, second])
        for task, address in ((self.task_id, first), (second_task, second)):
            delivery_receipts.prepare(task, profile, [(_destination("email", address), "email", "email 1")])
        Path(self.report).write_text("<html>Queued report</html>", encoding="utf-8")
        queue_file = Path(self.report).with_name("queue.json")
        now = datetime.fromisoformat("2026-11-21T14:00:00")
        entered, resume = Event(), Event()

        def send(*_args, **_kwargs):
            entered.set()
            self.assertTrue(resume.wait(5))

        self.send_mail.side_effect = send
        with (patch("neurodaily.delivery._queue_path", return_value=queue_file),
              patch("neurodaily.task_runs.load_result", return_value=self.result),
              ThreadPoolExecutor(1) as executor):
            delivery._queue_email(self.task_id, self.report, profile,
                                  {"address": first}, "2026-11-21T13:00:00")
            active = executor.submit(delivery.run_email_queue, now)
            try:
                self.assertTrue(entered.wait(5))
                delivery._queue_email(second_task, self.report, profile,
                                      {"address": second}, "2026-11-21T15:00:00")
            finally:
                resume.set()
            self.assertEqual(active.result(timeout=5), {first: "ok"})
            self.assertEqual([row["task_id"] for row in delivery._read_queue()], [second_task])

    def test_legacy_queue_is_imported_once_and_kept_on_disk(self):
        profile = self.result.config_profile
        address = "lab@example.test"
        self.email.update(enabled=True, to=[address])
        delivery_receipts.prepare(self.task_id, profile, [(_destination("email", address), "email", "email 1")])
        Path(self.report).write_text("<html>Queued report</html>", encoding="utf-8")
        queue_file = Path(self.report).with_name("queue.json")
        old_rows = [{"task_id": self.task_id, "report_path": self.report, "profile": profile,
                     "address": address, "language": "zh", "due": "2026-11-21T13:00:00"}]
        queue_file.write_text(json.dumps(old_rows), encoding="utf-8")
        now = datetime.fromisoformat("2026-11-21T14:00:00")
        with (patch("neurodaily.delivery._queue_path", return_value=queue_file),
              patch("neurodaily.task_runs.load_result", return_value=self.result)):
            self.assertEqual(delivery.run_email_queue(now), {address: "ok"})
            self.assertEqual(delivery.run_email_queue(now), {})
        self.send_mail.assert_called_once()
        self.assertEqual(json.loads(queue_file.read_text(encoding="utf-8")), old_rows)

    def test_retry_with_stale_attempt_cannot_send_after_another_retry_failed(self):
        self.send_hook.return_value = {"wecom": "failed"}
        deliver_report(self.result, self.report, task_id=self.task_id)
        first, = list_receipts(self.task_id)
        updated = retry_delivery(self.result, self.report, self.task_id, first["destination"])
        self.assertEqual((updated["status"], updated["attempts"]), ("failed", 2))

        with patch("neurodaily.delivery.list_receipts", return_value=[first]):
            with self.assertRaisesRegex(ValueError, "已更新"):
                retry_delivery(self.result, self.report, self.task_id, first["destination"])
        self.assertEqual(self.send_hook.call_count, 2)

    def test_interrupted_send_has_unknown_outcome_and_is_not_retried(self):
        self.send_hook.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            deliver_report(self.result, self.report, task_id=self.task_id)
        interrupted, = list_receipts(self.task_id)
        self.assertEqual((interrupted["status"], interrupted["attempts"]), ("unknown", 1))
        with self.assertRaises(ValueError):
            retry_delivery(self.result, self.report, self.task_id, interrupted["destination"])
        self.send_hook.assert_called_once()

    def test_missing_password_can_be_corrected_and_retried(self):
        self.email.update(enabled=True, to=["lab@example.test"])
        self.hooks.clear()
        self.password.return_value = ""
        self.assertEqual(deliver_report(self.result, self.report, task_id=self.task_id), {"email 1": "failed"})
        failure, = list_receipts(self.task_id)
        self.assertEqual((failure["status"], failure["attempts"]), ("failed", 0))
        self.send_mail.assert_not_called()

        self.password.return_value = "password"
        final = retry_delivery(self.result, self.report, self.task_id, failure["destination"])
        self.assertEqual((final["status"], final["attempts"]), ("accepted", 1))
        self.send_mail.assert_called_once()

    def test_removing_history_also_removes_its_receipts(self):
        self.send_hook.return_value = {"wecom": "ok"}
        another = self.make_run()
        deliver_report(self.result, self.report, task_id=self.task_id)
        deliver_report(self.result, self.report, task_id=another)
        self.assertEqual(len(list_receipts(self.task_id)), 1)
        self.assertTrue(history.delete_run(int(self.task_id)))
        self.assertEqual(list_receipts(self.task_id), [])
        self.assertEqual(len(list_receipts(another)), 1)
        self.assertEqual(history.clear_history(), 1)
        self.assertEqual(list_receipts(another), [])
