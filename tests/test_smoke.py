"""Dependency-free smoke tests: .venv/bin/python -m unittest discover -s tests -v"""
import datetime as dt
import os
import tempfile
import time
import unittest
from unittest import mock

from neurodaily import mailer, mail_tui, onthisday as otd
from neurodaily.config import Config, DEFAULT_CONFIG
from neurodaily.digest import DigestResult, _prune_reports
from neurodaily.render import render_html


def _result(on_this_day=None, generated_at="2026-11-11T08:00:00"):
    cfg = DEFAULT_CONFIG()
    return DigestResult(items=[], sections={"papers": [], "industry": [],
                                            "trials_conferences": [], "policy": []},
                        health=[], generated_at=generated_at, config_profile="neuro",
                        config=cfg, on_this_day=on_this_day or otd.today_events(dt.date(2026, 11, 11)))


class ConfigTests(unittest.TestCase):
    def test_roundtrip(self):
        d = DEFAULT_CONFIG().to_dict()
        self.assertEqual(Config.from_dict(d).to_dict(), d)

    def test_rejects_empty_disciplines(self):
        with self.assertRaises(ValueError):
            Config.from_dict({"profile": "x"})


class OnThisDayTests(unittest.TestCase):
    def test_366_days_all_have_long_body(self):
        d, empty, short = dt.date(2024, 1, 1), 0, 0
        while d.year == 2024:
            evs = otd.today_events(d)
            if not evs:
                empty += 1
            elif not any(len(e.get("body", "")) >= 500 for e in evs):
                short += 1
            d += dt.timedelta(days=1)
        self.assertEqual(empty, 0)
        self.assertEqual(short, 0)

    def test_no_birth_or_death_entries(self):
        pool = list(otd.EVERGREEN_ALL) + [x for v in otd.EVENTS.values() for x in v]
        bad = [e["title"] for e in pool if "出生" in e["title"] or "逝世" in e["title"]]
        self.assertEqual(bad, [])


class RenderTests(unittest.TestCase):
    def test_section_is_on_top_and_graph_js_once(self):
        h = render_html(_result())
        self.assertLess(h.find("历史上的今天"), h.find("Latest Papers"))
        self.assertEqual(h.count("Connected Papers"), 1)


class MailerTests(unittest.TestCase):
    def test_subject_format(self):
        s = mailer.subject_for(_result(generated_at="2026-11-11T08:00:00"), mailer.DEFAULT_CFG)
        self.assertEqual(s, "神经病专家的厕所读物-2026-11-11 星期三")

    def test_empty_recipients_raises(self):
        cfg = dict(mailer.DEFAULT_CFG)
        cfg["to"] = []
        with mock.patch.object(mailer, "_password", return_value="x"):
            with self.assertRaises(RuntimeError):
                mailer.send("s", "<p>h</p>", "t", cfg)

    def test_attachment_size_guard(self):
        d = tempfile.mkdtemp()
        big = os.path.join(d, "big.html")
        with open(big, "wb") as f:
            f.write(b"x" * (9 * 1024 * 1024))
        cfg = dict(mailer.DEFAULT_CFG)
        cfg["attach_max_mb"] = 8
        cfg["to"] = ["a@b.com"]
        msg = mailer._build_message(cfg, "s", "<p>h</p>", "t", [big])
        self.assertFalse(any(p.get_filename() for p in msg.walk() if p.get_filename()))

    def test_missing_attachment_is_skipped(self):
        cfg = dict(mailer.DEFAULT_CFG)
        cfg["to"] = ["a@b.com"]
        msg = mailer._build_message(cfg, "s", "<p>h</p>", "t", ["/nope/missing.html"])
        self.assertFalse(any(p.get_filename() for p in msg.walk() if p.get_filename()))


class MailTuiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mktemp(suffix=".json")
        self.patch = mock.patch.object(mail_tui, "CFG_PATH", self.tmp)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_add_remove_and_duplicate(self):
        self.assertFalse(mail_tui.add_recipient("bad")[0])
        self.assertTrue(mail_tui.add_recipient("t1@example.com")[0])
        self.assertFalse(mail_tui.add_recipient("T1@Example.com")[0])
        self.assertTrue(mail_tui.remove_recipient("t1@example.com")[0])

    def test_keeps_smtp_settings(self):
        mail_tui.add_recipient("t2@example.com")
        cfg = mail_tui.load_cfg()
        self.assertTrue(cfg.get("smtp_host"))
        self.assertIn("t2@example.com", cfg.get("to", []))


class PruneTests(unittest.TestCase):
    def test_keeps_newest_plus_referenced(self):
        d = tempfile.mkdtemp()
        files = []
        for i in range(5):
            p = os.path.join(d, f"neurodaily_x{i}.html")
            with open(p, "w") as fh:
                fh.write("x")
            time.sleep(0.01)
            files.append(p)
        ref = os.path.basename(files[0])
        with mock.patch("neurodaily.history.list_runs",
                        return_value=[{"report_path": ref}]):
            _prune_reports(d, keep=2)
        left = set(os.listdir(d))
        self.assertIn(files[0].split("/")[-1], left)
        self.assertGreaterEqual(len(left), 3)


if __name__ == "__main__":
    unittest.main()
