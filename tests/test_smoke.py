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


# ---------------------------------------------------------------------------
# New: schema, config ops, profiles, exporters, demo, webhooks, generic sources
# ---------------------------------------------------------------------------
import json  # noqa: E402
from neurodaily import config_ops, demo, exporters, webhooks  # noqa: E402
from neurodaily import schema  # noqa: E402
from neurodaily.sources import generic  # noqa: E402


class SchemaTests(unittest.TestCase):
    def test_default_is_valid(self):
        self.assertEqual(schema.validate(DEFAULT_CONFIG().to_dict()), [])

    def test_empty_disciplines_rejected(self):
        errs = schema.validate({"profile": "x", "disciplines": []})
        self.assertTrue(any("disciplines" in e for e in errs))

    def test_generic_source_requires_url(self):
        errs = schema.validate({"disciplines": [{"name": "X", "keywords": ["x"]}],
                                "sources": {"bad": {"type": "rss", "enabled": True}}})
        self.assertTrue(any("url is required" in e for e in errs))

    def test_unknown_kind_rejected(self):
        errs = schema.validate({"disciplines": [{"name": "X", "keywords": ["x"]}],
                                "sources": {"s": {"type": "rss", "url": "https://x",
                                                  "kind": "nope"}}})
        self.assertTrue(any("unknown kind" in e for e in errs))


class ConfigOpsTests(unittest.TestCase):
    def test_merge_semantics(self):
        base = {"a": {"b": 1}, "l": [1, 2], "keep": 1}
        patch = {"a": {"c": 2}, "l": [3], "keep": None}
        out = config_ops.deep_merge(base, patch)
        self.assertEqual(out["a"], {"b": 1, "c": 2})
        self.assertEqual(out["l"], [3])
        self.assertNotIn("keep", out)

    def test_dry_run_does_not_write(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "config.json")
        with open(path, "w") as f:
            json.dump(DEFAULT_CONFIG().to_dict(), f)
        with open(path) as f:
            before = f.read()
        ok, errs, diff = config_ops.apply_patch(path, {"profile": "oncology"}, dry_run=True)
        self.assertTrue(ok, errs)
        with open(path) as f:
            self.assertEqual(f.read(), before)
        self.assertIn("oncology", diff)

    def test_apply_writes_and_validates(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "config.json")
        with open(path, "w") as f:
            json.dump(DEFAULT_CONFIG().to_dict(), f)
        ok, errs, _ = config_ops.apply_patch(path, {"profile": "oncology"})
        self.assertTrue(ok, errs)
        self.assertEqual(json.load(open(path))["profile"], "oncology")

    def test_invalid_patch_rejected(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "config.json")
        with open(path, "w") as f:
            json.dump(DEFAULT_CONFIG().to_dict(), f)
        ok, errs, _ = config_ops.apply_patch(path, {"disciplines": []})
        self.assertFalse(ok)
        self.assertTrue(errs)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.patches = [
            mock.patch.object(config_ops, "profiles_dir", return_value=self.tmp),
            mock.patch.object(config_ops, "profile_path",
                              side_effect=lambda n: os.path.join(self.tmp, f"{n}.json")),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_new_and_list(self):
        path = config_ops.new_profile("oncology")
        self.assertTrue(os.path.exists(path))
        self.assertIn("oncology", config_ops.list_profiles())


class ExportTests(unittest.TestCase):
    def test_json_and_bibtex(self):
        r = demo.build_result()
        d = tempfile.mkdtemp()
        jp = exporters.write_json(r, os.path.join(d, "x.json"))
        bp = exporters.write_bibtex(r, os.path.join(d, "x.bib"))
        with open(jp) as f:
            data = json.load(f)
        self.assertEqual(data["counts"]["items"], len(r.items))
        with open(bp) as f:
            bib = f.read()
        self.assertIn("@article", bib)
        self.assertIn("Oligodendrocyte", bib)


class DemoTests(unittest.TestCase):
    def test_demo_result(self):
        r = demo.build_result()
        self.assertEqual(len(r.items), 10)
        self.assertEqual(sum(len(v) for v in r.sections.values()), 10)
        self.assertTrue(r.on_this_day)
        h = render_html(r)
        self.assertLess(h.find("历史上的今天"), h.find("Latest Papers"))


class WebhookTests(unittest.TestCase):
    def test_build_text(self):
        r = demo.build_result()
        txt = webhooks.build_text(r, 3)
        self.assertIn("NeuroDaily", txt)
        self.assertIn(r.sections["papers"][0].title, txt)

    def test_no_config_is_noop(self):
        r = demo.build_result()
        self.assertEqual(webhooks.send_all(r, {"feishu": "", "wecom": ""}), {})


class GenericSourceTests(unittest.TestCase):
    RSS = (b'<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>'
           b'<item><title>Hello paper</title><link>https://x/1</link>'
           b'<description>An abstract</description>'
           b'<pubDate>Mon, 10 Nov 2026 00:00:00 GMT</pubDate></item></channel></rss>')

    def test_rss(self):
        class R:
            content = self.RSS
        cfg = DEFAULT_CONFIG()
        cfg.sources["t"] = {"enabled": True, "type": "rss", "url": "https://x/feed",
                            "kind": "paper", "max_results": 5, "lookback_days": 3650}
        with mock.patch.object(generic, "get", return_value=R()):
            items = generic.fetch_rss("t", cfg)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Hello paper")
        self.assertEqual(items[0].kind, "paper")

    def test_json(self):
        class R:
            def json(self):
                return {"data": {"items": [{"title": "J paper", "link": "https://x/2",
                                            "abstract": "a", "published": "2026-11-01"}]}}
        cfg = DEFAULT_CONFIG()
        cfg.sources["j"] = {"enabled": True, "type": "json_api", "url": "https://x/api",
                            "items_path": "data.items", "kind": "paper",
                            "map": {"title": "title", "url": "link",
                                    "summary": "abstract", "date": "published"},
                            "max_results": 5, "lookback_days": 3650}
        with mock.patch.object(generic, "get", return_value=R()):
            items = generic.fetch_json("j", cfg)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, "https://x/2")


class AISummaryTests(unittest.TestCase):
    def test_build_text_has_blocks(self):
        from neurodaily import ai_summary
        txt = ai_summary.build_text(demo.build_result())
        for block in ("【论文】", "【产业与创投】", "【临床试验】", "【政策与新闻】"):
            self.assertIn(block, txt)

    def test_missing_key_raises(self):
        from neurodaily import ai_summary
        cfg = dict(ai_summary.DEFAULT_CFG)
        cfg["api_key_file"] = "/nonexistent/key"
        cfg["api_key_env"] = "NEURODAILY_TEST_NO_SUCH_ENV"
        with self.assertRaises(RuntimeError):
            ai_summary.generate(demo.build_result(), cfg)

    def test_cache_prevents_second_call(self):
        from neurodaily import ai_summary
        cfg = DEFAULT_CONFIG()
        d = tempfile.mkdtemp()
        cfg.output["dir"] = d
        r = demo.build_result(cfg)
        acfg = dict(ai_summary.DEFAULT_CFG)
        with mock.patch.object(ai_summary, "_call_llm", return_value="X" * 200) as m:
            t1 = ai_summary.generate(r, acfg, api_key_override="k")
            t2 = ai_summary.generate(r, acfg, api_key_override="k")
        self.assertEqual(t1, t2)
        self.assertEqual(m.call_count, 1)

    def test_render_places_ai_above_history(self):
        r = demo.build_result()
        r.ai_summary = "第一段\n第二段"
        r.ai_summary_meta = {"model": "test-model"}
        h = render_html(r)
        self.assertIn("今日 AI 摘要", h)
        self.assertLess(h.find("今日 AI 摘要"), h.find("历史上的今天"))
