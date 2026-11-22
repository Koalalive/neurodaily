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
    def test_save_report_accepts_filename_in_current_directory(self):
        from pathlib import Path
        from neurodaily.digest import save_report

        with tempfile.TemporaryDirectory() as directory:
            previous = os.getcwd()
            try:
                os.chdir(directory)
                with mock.patch("neurodaily.digest._write_static_history"), \
                     mock.patch("neurodaily.digest._prune_reports"):
                    name = save_report(demo.build_result(), "review.html")
                self.assertEqual(name, "review.html")
                self.assertIn("NeuroDaily", Path(name).read_text(encoding="utf-8"))
            finally:
                os.chdir(previous)

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
    def test_nested_null_deletes_key_in_new_object(self):
        self.assertEqual(config_ops.deep_merge({}, {"new": {"removed": None}}),
                         {"new": {}})

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

    def test_new_profile_keeps_existing_config(self):
        path = config_ops.new_profile("oncology")
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"profile": "custom"}')
        with self.assertRaises(FileExistsError):
            config_ops.new_profile("oncology")
        with open(path, encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"profile": "custom"})

    def test_cli_rejects_missing_profile_before_run(self):
        from contextlib import redirect_stderr
        from io import StringIO
        from neurodaily import cli
        err = StringIO()
        with mock.patch.object(cli, "cmd_run") as run, redirect_stderr(err):
            with self.assertRaises(SystemExit) as failure:
                cli.main(["--profile", "missing", "run"])
        self.assertEqual(failure.exception.code, 2)
        self.assertIn("profile not found: missing", err.getvalue())
        run.assert_not_called()


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
        self.assertLess(h.find('id="ai-summary"'), h.find('id="on-this-day"'))


class RouteTests(unittest.TestCase):
    def test_routes_and_guards(self):
        from fastapi.testclient import TestClient
        from neurodaily.webapp import create_app
        c = TestClient(create_app())
        for p in ("/", "/settings", "/api/config", "/api/status", "/history", "/reports"):
            self.assertEqual(c.get(p).status_code, 200, p)
        self.assertEqual(c.post("/api/config", json={"disciplines": []}).status_code, 400)
        self.assertEqual(c.get("/reports/..%2F..%2Fetc%2Fpasswd").status_code, 404)


class JournalMetricsTests(unittest.TestCase):
    def test_official_overrides_auto(self):
        from neurodaily import journal_metrics as jm
        off = tempfile.mktemp(suffix=".json"); auto = tempfile.mktemp(suffix=".json")
        with open(off, "w") as f:
            json.dump({"ttl_days": 1, "journals": {"Nature Medicine":
                       {"if": 58.7, "jcr": "Q1", "cas": "1区", "year": 2023}}}, f)
        with open(auto, "w") as f:
            json.dump({"journals": {"Nature Medicine":
                       {"oa_2yr": 31.6, "fetched_at": "2026-11-20"}}}, f)
        with mock.patch.object(jm, "OFFICIAL_PATH", off), mock.patch.object(jm, "AUTO_PATH", auto):
            m = jm.lookup("Nat Med")
            self.assertEqual(m["if"], 58.7)
            self.assertEqual(m["oa_2yr"], 31.6)
            self.assertTrue(m["official"])

    def test_import_csv(self):
        from neurodaily import journal_metrics as jm
        off = tempfile.mktemp(suffix=".json")
        csv_path = tempfile.mktemp(suffix=".csv")
        with open(csv_path, "w") as f:
            f.write("journal,if,jcr,cas,year\nNeuron,14.7,Q1,1区,2023\n")
        with mock.patch.object(jm, "OFFICIAL_PATH", off):
            out = jm.import_csv(csv_path)
            self.assertEqual(out["imported"], 1)
            m = jm.lookup("Neuron")
            self.assertEqual(m["if"], 14.7)
            self.assertEqual(m["cas"], "1区")

    def test_render_official_badges(self):
        r = demo.build_result()
        r.sections["papers"][0].extra["metrics"] = {"if": 58.7, "jcr": "Q1", "cas": "1区"}
        h = render_html(r)
        self.assertIn("IF 58.7", h)
        self.assertIn("中科院 1区", h)

    def test_config_hardcoded_overrides_all(self):
        from neurodaily import journal_metrics as jm
        from neurodaily.config import DEFAULT_CONFIG, Journal
        cfg = DEFAULT_CONFIG()
        cfg.journals = [Journal(name="Nature", impact_factor=99.9, jcr="Q1",
                                cas="1区", metric_year=2025)]
        m = jm.lookup("Nature", cfg)
        self.assertEqual(m["if"], 99.9)
        self.assertEqual(m["jcr"], "Q1")
        self.assertEqual(m["cas"], "1区")
        self.assertEqual(m["source"], "config")

    def test_config_exact_name_not_substring(self):
        from neurodaily import journal_metrics as jm
        from neurodaily.config import DEFAULT_CONFIG, Journal
        cfg = DEFAULT_CONFIG()
        cfg.journals = [Journal(name="Nature", impact_factor=99.9)]
        m = jm.lookup("Nature Medicine", cfg)
        self.assertTrue(m is None or m.get("source") != "config")

    def test_render_config_hardcoded_badge(self):
        from bs4 import BeautifulSoup
        r = demo.build_result()
        from neurodaily.config import DEFAULT_CONFIG, Journal
        cfg = DEFAULT_CONFIG()
        cfg.journals = [Journal(name="Nature", impact_factor=99.9, jcr="Q1", cas="1区")]
        r.config = cfg
        h = render_html(r, cfg)
        self.assertIn("IF 99.9", h)
        self.assertIn("中科院分区 1区", BeautifulSoup(h, "html.parser").get_text(" ", strip=True))

    def test_journal_from_dict_accepts_if_alias(self):
        from neurodaily.config import Journal
        j = Journal.from_dict({"name": "X", "if": 12.5, "jcr": "Q2",
                               "cas": "2区", "year": 2024})
        self.assertEqual(j.impact_factor, 12.5)
        self.assertEqual(j.jcr, "Q2")
        self.assertEqual(j.cas, "2区")
        self.assertEqual(j.metric_year, 2024)

    def test_journal_metric_year_survives_config_round_trip(self):
        from neurodaily.config import Config, Journal

        cfg = DEFAULT_CONFIG()
        cfg.journals = [Journal(name="Neuron", metric_year=2025)]
        with tempfile.TemporaryDirectory() as directory:
            path = cfg.save(os.path.join(directory, "config.json"))
            self.assertEqual(Config.load(path).journals[0].metric_year, 2025)


class WindowTests(unittest.TestCase):
    def test_time_window_accepts_utc_offset(self):
        from datetime import datetime, timedelta, timezone
        from neurodaily.digest import _filter_by_windows
        from neurodaily.models import Item

        now = datetime.now(timezone.utc)
        recent = Item(title="recent", date=(now - timedelta(hours=1)).isoformat(), kind="paper")
        old = Item(title="old", date=(now - timedelta(hours=3)).isoformat(), kind="paper")
        self.assertEqual(_filter_by_windows([recent, old], {"paper": 2}), [recent])

    def test_paper_window_filters_old_papers(self):
        from neurodaily.digest import _filter_papers_by_window
        from neurodaily.models import Item
        from datetime import datetime, timedelta
        now = datetime.now()
        items = [
            Item(title="new paper", kind="paper", date=(now - timedelta(hours=10)).strftime("%Y-%m-%d")),
            Item(title="old paper", kind="paper", date=(now - timedelta(hours=100)).strftime("%Y-%m-%d")),
            Item(title="old trial", kind="trial", date=(now - timedelta(days=30)).strftime("%Y-%m-%d")),
            Item(title="undated paper", kind="paper", date=""),
        ]
        out = _filter_papers_by_window(items, 36)
        titles = {i.title for i in out}
        self.assertIn("new paper", titles)
        self.assertNotIn("old paper", titles)
        self.assertIn("old trial", titles)
        self.assertIn("undated paper", titles)

    def test_default_windows(self):
        w = DEFAULT_CONFIG().windows
        for key in ("daily_paper_hours", "trials_hours", "funding_hours", "news_hours"):
            self.assertEqual(w[key], 36)
        self.assertGreaterEqual(w["manual_paper_hours"], 36)

    def test_kind_windows_filter(self):
        from neurodaily.digest import _filter_by_windows
        from neurodaily.models import Item
        from datetime import datetime, timedelta
        now = datetime.now()
        items = [
            Item(title="old trial", kind="trial", date=(now - timedelta(hours=100)).strftime("%Y-%m-%d")),
            Item(title="old funding", kind="funding", date=(now - timedelta(hours=100)).strftime("%Y-%m-%d")),
            Item(title="old news", kind="news", date=(now - timedelta(hours=100)).strftime("%Y-%m-%d")),
            Item(title="new trial", kind="trial", date=(now - timedelta(hours=10)).strftime("%Y-%m-%d")),
            Item(title="new news", kind="news", date=(now - timedelta(hours=10)).strftime("%Y-%m-%d")),
        ]
        out = _filter_by_windows(items, {"trial": 36, "funding": 36, "news": 36})
        titles = {i.title for i in out}
        self.assertNotIn("old trial", titles)
        self.assertNotIn("old funding", titles)
        self.assertNotIn("old news", titles)
        self.assertIn("new trial", titles)
        self.assertIn("new news", titles)


class OnThisDayLangTests(unittest.TestCase):
    def test_labels_switch(self):
        evs = otd.today_events()
        en = otd.render_section_html(evs, lang="en")
        ru = otd.render_section_html(evs, lang="ru")
        self.assertIn("On This Day", en)
        self.assertIn("В этот день", ru)

    def test_fallback_without_key(self):
        from neurodaily import ai_summary
        with mock.patch.object(ai_summary, "api_key", return_value=""), \
             mock.patch.object(otd, "_load_translations", return_value={}), \
             mock.patch.object(otd, "_save_translations"):
            evs = otd.today_events(lang="en")
        self.assertTrue(evs)
        self.assertFalse(all(e.get("translated", True) for e in evs))


class RenderAITests(unittest.TestCase):
    def test_allowed_link(self):
        from neurodaily.render import render_ai_text
        h = render_ai_text("见 [Nature 论文](https://example.com/a)", {"https://example.com/a"})
        self.assertIn('href="https://example.com/a"', h)
        self.assertIn("Nature 论文</a>", h)

    def test_rejected_link(self):
        from neurodaily.render import render_ai_text
        h = render_ai_text("见 [伪造链接](https://evil.example/x)", {"https://example.com/a"})
        self.assertNotIn("<a ", h)
        self.assertIn("伪造链接", h)

    def test_escape_html(self):
        from neurodaily.render import render_ai_text
        h = render_ai_text("<script>alert(1)</script>")
        self.assertNotIn("<script>", h)
        self.assertIn("&lt;script&gt;", h)


class SummaryContextTests(unittest.TestCase):
    def test_build_text_includes_urls(self):
        from neurodaily.ai_summary import build_text
        from neurodaily.demo import build_result
        text = build_text(build_result())
        self.assertIn("url: http", text)


class ReportTocTests(unittest.TestCase):
    def test_toc_and_anchors(self):
        from neurodaily.demo import build_result
        from neurodaily.render import render_html
        h = render_html(build_result())
        self.assertIn('class="toc"', h)
        self.assertIn('href="#trials_conferences"', h)
        self.assertIn('href="#policy"', h)
        self.assertIn('id="papers"', h)
        self.assertIn('id="industry"', h)


class AIRefLinkTests(unittest.TestCase):
    def test_ref_link_renders(self):
        from neurodaily.render import render_ai_text
        refs = {"R1": {"url": "https://example.com/paper"}}
        h = render_ai_text("见 [记忆改善](R1)", {"https://example.com/paper"}, refs)
        self.assertIn('href="https://example.com/paper"', h)
        self.assertIn("记忆改善</a>", h)

    def test_strip_links_dedup(self):
        from neurodaily.ai_summary import _strip_links
        s = _strip_links("证据[少突胶质细胞功能障碍](R1)。")
        self.assertEqual(s.count("少突胶质细胞功能障碍"), 1)


class EmailSafeTests(unittest.TestCase):
    def test_strips_interactive_chrome(self):
        from neurodaily.mailer import email_safe_html
        from neurodaily.demo import build_result
        from neurodaily.render import render_html
        h = render_html(build_result())
        e = email_safe_html(h)
        for marker in ('id="runNow"', 'id="settingsLink"', 'id="histLink"', 'id="promptLink"'):
            self.assertNotIn(marker, e)
        self.assertNotIn('class="toc"', e)
        self.assertNotIn("<script", e)
        self.assertIn("Latest Papers", e)
        self.assertIn("目录", e)
        self.assertIn('href="#trials_conferences"', e)
        self.assertNotIn("<button", e)
        self.assertNotIn('class="sec-actions"', e)


class SettingsEnglishTests(unittest.TestCase):
    def test_settings_page_english(self):
        from neurodaily.settings_page import SETTINGS_HTML
        self.assertIn("Save & continue to search", SETTINGS_HTML)
        self.assertIn("Research presets", SETTINGS_HTML)
        self.assertIn("Push settings (email / webhook)", SETTINGS_HTML)
        self.assertNotIn("保存并立即检索推送", SETTINGS_HTML)


class SummaryLinkGuaranteeTests(unittest.TestCase):
    def test_entity_fallback_links_journal(self):
        from neurodaily.ai_summary import _entity_fallback
        refs = {"R1": {"url": "https://x/1", "title": "A memory study", "journal": "Nature"}}
        out = _entity_fallback("《Nature》发表了一项记忆研究。", refs)
        self.assertIn("[Nature](R1)", out)

    def test_append_sources_guarantees_links(self):
        from neurodaily.ai_summary import _append_sources
        refs = {"R1": {"url": "https://x/1", "title": "Paper one"},
                "R2": {"url": "https://x/2", "title": "Paper two"}}
        out = _append_sources("正文。", refs, 2)
        self.assertEqual(out.count("](R"), 2)

    def test_insert_citations_one_link_per_sentence(self):
        from neurodaily.ai_summary import _insert_citations
        refs = {"R1": {"url": "https://x/1", "journal": "Nature"},
                "R2": {"url": "https://x/2", "journal": "eLife"}}
        out = _insert_citations("句子一。句子二。", {0: "R1", 1: "R2"}, refs)
        self.assertEqual(out.count("（["), 2)
        self.assertEqual(out.count("](R"), 2)
        self.assertNotIn("[句子", out)


class SummaryCleanupTests(unittest.TestCase):
    def test_clean_parentheses(self):
        from neurodaily.ai_summary import _clean_summary
        cases = {
            "（[记忆改善](R1)）": "（[记忆改善](R1)）",
            "结论（）。": "结论。",
            "研究（TransA-MERFISH揭示环路）。": "研究TransA-MERFISH揭示环路。",
            "说明（含逗号，的补充）。": "说明（含逗号，的补充）。",
            "（R3）": "",
            "（2020）": "（2020）",
            "（共 582 篇）": "（共 582 篇）",
            "（若附件缺失则因体积超限）": "（若附件缺失则因体积超限）",
        }
        for src, want in cases.items():
            self.assertEqual(_clean_summary(src), want)

    def test_render_skips_empty_label(self):
        from neurodaily.render import render_ai_text
        h = render_ai_text("[ ](R1) 正文", {"https://x"}, {"R1": {"url": "https://x"}})
        self.assertNotIn("<a ", h)
        self.assertIn("正文", h)


class EmailSummaryCleanTests(unittest.TestCase):
    def test_email_body_has_no_empty_parens(self):
        from neurodaily.demo import build_result
        from neurodaily.mailer import render_email, load_cfg
        r = build_result()
        r.ai_summary = "研究（[记忆改善](R1)）。另一项（）。"
        r.ai_summary_refs = {"R1": {"url": "https://example.com/x", "title": "X"}}
        _s, h, t = render_email(r, load_cfg())
        self.assertNotIn("（）", h)
        self.assertIn('href="https://example.com/x"', h)


class CollapsibleSectionTests(unittest.TestCase):
    def test_report_has_collapsible_script(self):
        from neurodaily.demo import build_result
        from neurodaily.render import render_html
        h = render_html(build_result())
        self.assertIn("initCollapsibleSections", h)
        self.assertIn("sec-toggle", h)
        self.assertIn(".sec-body[hidden]", h)


class BareRefTests(unittest.TestCase):
    def test_bare_ref_becomes_parenthetical_link(self):
        from neurodaily.ai_summary import _clean_summary
        refs = {"R4": {"url": "https://x/4", "journal": "Nature"}}
        out = _clean_summary("研究显示R4。", refs)
        self.assertIn("（[Nature](R4)）", out)
        self.assertNotIn("R4。", out)

    def test_link_target_not_touched(self):
        from neurodaily.ai_summary import _clean_summary
        refs = {"R8": {"url": "https://x/8", "journal": "eLife"}}
        out = _clean_summary("见[通路](R8)。", refs)
        self.assertIn("[通路](R8)", out)


class ApplyLinksProtectionTests(unittest.TestCase):
    def test_does_not_break_existing_link(self):
        from neurodaily.ai_summary import _apply_links
        text = "星形胶质细胞[CCL5表达受Mir324调控](R8)，通路。"
        out = _apply_links(text, [{"phrase": "星形胶质细胞", "ref": "R2"}], {})
        self.assertIn("[星形胶质细胞](R2)", out)
        self.assertIn("[CCL5表达受Mir324调控](R8)", out)
        self.assertNotIn("[星形胶质细胞[CCL5", out)


class BaseMetaTests(unittest.TestCase):
    def test_report_has_nd_base_meta(self):
        from neurodaily.demo import build_result
        from neurodaily.render import render_html
        self.assertIn('name="nd-base"', render_html(build_result()))


class DateOnlyWindowTests(unittest.TestCase):
    def test_yesterday_date_only_survives_36h(self):
        from neurodaily.digest import _filter_by_windows
        from neurodaily.models import Item
        from datetime import date, timedelta
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        out = _filter_by_windows(
            [Item(title="vc news", kind="funding", date=yesterday)],
            {"funding": 36},
        )
        self.assertEqual(len(out), 1)

    def test_two_days_ago_date_only_dropped(self):
        from neurodaily.digest import _filter_by_windows
        from neurodaily.models import Item
        from datetime import date, timedelta
        old = (date.today() - timedelta(days=3)).isoformat()
        out = _filter_by_windows(
            [Item(title="old vc", kind="funding", date=old)],
            {"funding": 36},
        )
        self.assertEqual(out, [])


class CitationFormatTests(unittest.TestCase):
    def test_parenthetical_ref_not_doubled(self):
        from neurodaily.ai_summary import _clean_summary
        refs = {"R6": {"url": "https://x/6", "title": "RNS approved for epilepsy"}}
        out = _clean_summary("证据（R6）。", refs)
        self.assertIn("（[RNS approved for epilepsy](R6)）", out)
        self.assertNotIn("（（", out)

    def test_source_label_replaced_by_title(self):
        from neurodaily.ai_summary import _clean_summary
        refs = {"R8": {"url": "https://x/8", "title": "SANTE long-term follow-up", "journal": "trials"}}
        out = _clean_summary("随访R8。", refs)
        self.assertIn("SANTE long-term follow-up", out)
        self.assertNotIn("trials](", out)


class LabelProtectionTests(unittest.TestCase):
    def test_link_label_not_rewritten(self):
        from neurodaily.ai_summary import _clean_summary
        refs = {"R5": {"url": "https://x/5", "title": "Lecanemab (Leqembi) receives full FDA approval"}}
        src = "（[Lecanemab (Leqembi) receives full FDA approval](R5)）"
        out = _clean_summary(src, refs)
        self.assertIn("[Lecanemab (Leqembi) receives full FDA approval](R5)", out)
        self.assertNotIn("（[Leqembi]", out)


class RunNowTests(unittest.TestCase):
    def test_research_presets_are_valid_and_leave_saved_config_untouched(self):
        from pathlib import Path
        from fastapi.testclient import TestClient
        from neurodaily.schema import validate
        from neurodaily.webapp import create_app

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            cfg = DEFAULT_CONFIG()
            cfg.output["dir"] = directory
            cfg.save(str(path))
            before = path.read_bytes()
            response = TestClient(create_app(str(path))).get("/api/config/presets")
            self.assertEqual(response.status_code, 200)
            presets = {entry["label"]: entry["config"] for entry in response.json()}
            self.assertEqual({label: value["profile"] for label, value in presets.items()},
                             {"神经科学": "neuro", "肿瘤学": "oncology", "重症医学": "critical-care"})
            for value in presets.values():
                self.assertNotIn("output", value)
                self.assertNotIn("scheduled", value)
                self.assertEqual(validate({**cfg.to_dict(), **value}), [])
            self.assertIn("Surgical Procedures, Operative",
                          [term for d in presets["肿瘤学"]["disciplines"] for term in d["mesh_terms"]])
            self.assertIn("Sepsis", [term for d in presets["重症医学"]["disciplines"] for term in d["mesh_terms"]])
            self.assertEqual(path.read_bytes(), before)

    def test_oncology_report_shows_its_topic_without_neuroscience_history(self):
        from neurodaily.render import render_html

        cfg = DEFAULT_CONFIG()
        cfg.profile = "oncology"
        html = render_html(demo.build_result(cfg))
        self.assertIn("oncology digest", html)
        self.assertNotIn('id="on-this-day"', html)

    def test_fingerprint_tracks_window_mode_and_feed(self):
        from neurodaily.history import compute_fingerprint
        from neurodaily.webapp import _cfg_with_hours

        cfg = DEFAULT_CONFIG()
        original = compute_fingerprint(cfg)
        self.assertNotEqual(original, compute_fingerprint(_cfg_with_hours(cfg, 12)))
        self.assertNotEqual(original, compute_fingerprint(cfg, mode="daily"))
        next(j for j in cfg.journals if j.rss).rss = "https://example.org/replacement.rss"
        self.assertNotEqual(original, compute_fingerprint(cfg))

    def test_hours_override_is_copy(self):
        from neurodaily.webapp import _cfg_with_hours
        from neurodaily.config import DEFAULT_CONFIG
        c = DEFAULT_CONFIG()
        c.windows = {"daily_paper_hours": 36, "manual_paper_hours": 168,
                     "trials_hours": 36, "funding_hours": 36, "news_hours": 36,
                     "other_lookback_days": 7}
        c2 = _cfg_with_hours(c, 12)
        for k in ("daily_paper_hours", "manual_paper_hours", "trials_hours",
                  "funding_hours", "news_hours"):
            self.assertEqual(c2.windows[k], 12)
        self.assertEqual(c.windows["daily_paper_hours"], 36)
        self.assertEqual(c2.windows["other_lookback_days"], 1)

    def test_run_page(self):
        from fastapi.testclient import TestClient
        from neurodaily.webapp import create_app
        r = TestClient(create_app()).get("/run")
        self.assertEqual(r.status_code, 200)
        self.assertIn("本次检索范围", r.text)
        self.assertIn("hours", r.text)

    def test_settings_feed_selector(self):
        from neurodaily.settings_page import SETTINGS_HTML
        self.assertIn("querySelectorAll('input.feed')", SETTINGS_HTML)


class WebSearchOutcomeTests(unittest.TestCase):
    def setUp(self):
        from contextlib import ExitStack
        from fastapi.testclient import TestClient
        from neurodaily.webapp import create_app

        stack = ExitStack()
        self.addCleanup(stack.close)
        directory = self.directory = stack.enter_context(tempfile.TemporaryDirectory())
        cfg = DEFAULT_CONFIG()
        cfg.output.update(dir=directory, open_on_finish=False)
        self.config_path = cfg.save(os.path.join(directory, "config.json"))
        self.result = demo.build_result(cfg)
        self.app = create_app(self.config_path)
        self.client = TestClient(self.app)
        stack.enter_context(mock.patch("neurodaily.history.db_path",
                                     return_value=os.path.join(directory, "search_history.db")))
        stack.enter_context(mock.patch("neurodaily.webapp.run_digest", return_value=self.result))
        stack.enter_context(mock.patch("neurodaily.journal_metrics.ensure_fresh"))
        self.ai = stack.enter_context(mock.patch("neurodaily.ai_summary.generate", return_value=""))
        # Scheduled-run tests exercise task/report/delivery wiring, not live
        # geolocation. Keep them deterministic and fast.
        self.geo = stack.enter_context(mock.patch(
            "neurodaily.research_activity.enrich_geography", return_value=False))
        stack.enter_context(mock.patch("neurodaily.mailer.load_cfg", return_value={"enabled": False}))
        stack.enter_context(mock.patch("neurodaily.mailer.render_email", return_value=("", "", "")))
        self.mail = stack.enter_context(mock.patch("neurodaily.mailer.save_last"))
        stack.enter_context(mock.patch("neurodaily.webhooks.load_cfg",
                                     return_value={"feishu": "https://example.test/bot"}))
        self.hooks = stack.enter_context(mock.patch("neurodaily.webhooks.send_all",
                                                   return_value={"feishu": "ok"}))

    def test_success_is_reported_after_the_report_is_written(self):
        def save(result, path):
            self.assertIsNone(self.app.state.last_run)
            self.assertEqual(self.app.state.search_attempt["status"], "running")
            with open(path, "w", encoding="utf-8") as f:
                f.write("<html>saved report</html>")

        with mock.patch("neurodaily.digest.save_report", side_effect=save):
            started = self.client.post("/api/run?force=1").json()
        status = self.client.get("/api/status").json()
        self.assertEqual(status["search"]["started_at"], started["started_at"])
        self.assertEqual(status["search"]["status"], "completed")
        self.assertEqual(status["search"]["item_count"], len(self.result.items))
        self.assertIn("saved report", self.client.get("/report/latest").text)

    def test_save_failure_does_not_announce_success_or_deliver(self):
        with mock.patch("neurodaily.digest.save_report", side_effect=OSError("disk full")):
            with self.assertLogs("neurodaily.webapp", level="ERROR"):
                self.client.post("/api/run?force=1")
        status = self.client.get("/api/status").json()
        self.assertIsNone(status["last_run"])
        self.assertEqual(status["search"]["status"], "failed")
        self.assertEqual(self.client.get("/report/latest").status_code, 404)
        self.mail.assert_not_called()
        self.hooks.assert_not_called()

    def test_skipped_search_does_not_replace_or_deliver_a_report(self):
        self.result.skipped = True
        self.result.skipped_reason = "already searched"
        with mock.patch("neurodaily.digest.save_report") as save:
            self.client.post("/api/run")
        self.assertEqual(self.client.get("/api/status").json()["search"]["status"], "skipped")
        save.assert_not_called()
        self.ai.assert_not_called()
        self.mail.assert_not_called()
        self.hooks.assert_not_called()

    def test_active_search_rejects_a_second_request(self):
        self.app.state.search_attempt = {"status": "running"}
        self.assertEqual(self.client.post("/api/run?force=1").status_code, 409)

    def test_desktop_schedule_shares_report_and_delivery_pipeline(self):
        from datetime import datetime
        from pathlib import Path
        from threading import Event
        from fastapi.testclient import TestClient
        from neurodaily.webapp import create_app, run_digest

        finished = Event()
        stops = []

        def schedule(stop, load, start):
            stops.append(stop)
            self.assertTrue(start(load(), datetime(2026, 11, 20, 8, 0)))
            self.assertTrue(start(load(), datetime(2026, 11, 20, 8, 0)))
            finished.set()

        def save(_result, path):
            Path(path).write_text("<html>scheduled report</html>", encoding="utf-8")

        with mock.patch("neurodaily.webapp.run_schedule", side_effect=schedule), \
             mock.patch("neurodaily.digest.save_report", side_effect=save):
            with TestClient(create_app(self.config_path, desktop=True)) as client:
                self.assertTrue(finished.wait(2))
                result = client.get("/api/status").json()
                self.assertEqual(result["search"]["status"], "completed")
                self.assertEqual(run_digest.call_args.kwargs["mode"], "daily")
                self.assertTrue(run_digest.call_args.kwargs["force"])
                run_digest.assert_called_once()
                self.assertIn("scheduled report", client.get("/report/latest").text)
                self.assertEqual(client.get("/api/launchd/status").json()["backend"], "desktop")
                self.assertEqual(client.post("/api/launchd/install").status_code, 400)
                self.hooks.assert_called_once()
        self.assertTrue(stops[0].is_set())

    def test_desktop_schedule_reports_source_failure_and_retries(self):
        from datetime import datetime, timedelta
        from threading import Event
        from fastapi.testclient import TestClient
        from neurodaily.config import Config
        from neurodaily.webapp import create_app

        cfg = Config.load(self.config_path)
        now = datetime.now()
        cfg.scheduled.update(enabled=True, hour=now.hour, minute=now.minute)
        cfg.save(self.config_path)
        due = now.replace(second=0, microsecond=0)
        failed, retry, finished = Event(), Event(), Event()
        outcomes = []

        def schedule(stop, load, start):
            self.result.health = [{"source": "fixture", "ok": False}]
            outcomes.append(start(load(), due))
            failed.set()
            if retry.wait(3):
                self.result.health = [{"source": "demo", "ok": True, "count": len(self.result.items)}]
                with mock.patch("neurodaily.webapp.RETRY_DELAY", timedelta()):
                    outcomes.append(start(load(), due))
                finished.set()

        with mock.patch("neurodaily.webapp.run_schedule", side_effect=schedule):
            with TestClient(create_app(self.config_path, desktop=True)) as client:
                self.assertTrue(failed.wait(3))
                status = client.get("/api/launchd/status").json()
                self.assertEqual(status["state"], "retrying")
                self.assertEqual(status["last_run"]["status"], "failed")
                self.assertEqual(client.get("/report/latest").status_code, 404)
                self.hooks.assert_not_called()
                retry.set()
                self.assertTrue(finished.wait(3))
                status = client.get("/api/launchd/status").json()
                self.assertEqual(status["last_run"]["status"], "completed")
                self.assertEqual(datetime.fromisoformat(status["next_run"]), due + timedelta(days=1))
                self.assertEqual(outcomes, [False, True])
                self.hooks.assert_called_once()

    def test_latest_report_after_restart_recognizes_custom_names(self):
        from pathlib import Path

        folder = Path(self.directory)
        real = folder / "review_2026-11-20.html"
        demo_report = folder / "neurodaily_demo.html"
        real.write_text(render_html(self.result).replace(" (demo)", ""), encoding="utf-8")
        demo_report.write_text(render_html(self.result), encoding="utf-8")
        (folder / "history.html").write_text("<html>not a report</html>", encoding="utf-8")
        os.utime(real, (100, 100))
        os.utime(demo_report, (200, 200))

        response = self.client.get("/report/latest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, real.read_text(encoding="utf-8"))

        real.unlink()
        self.assertEqual(self.client.get("/report/latest").text,
                         demo_report.read_text(encoding="utf-8"))

    def test_disabled_email_accepts_no_recipients_without_touching_webhooks(self):
        from pathlib import Path

        email = Path(self.directory) / "email.json"
        hooks = Path(self.directory) / "webhooks.json"
        hooks.write_text('{"keep": true}', encoding="utf-8")
        with mock.patch("neurodaily.mailer.CFG_PATH", str(email)), \
             mock.patch("neurodaily.webhooks.CFG_PATH", str(hooks)):
            response = self.client.post("/api/push", json={"email": {"enabled": False, "to": ""}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(email.read_text(encoding="utf-8"))["to"], [])
        self.assertEqual(hooks.read_text(encoding="utf-8"), '{"keep": true}')


class DesktopScheduleTests(unittest.TestCase):
    def test_overdue_today_runs_on_enable_and_after_a_time_or_profile_change(self):
        from datetime import datetime
        from neurodaily.desktop_schedule import run_schedule

        cfg = DEFAULT_CONFIG()
        current = datetime(2026, 11, 20, 8, 5, 24)
        start, stop = mock.Mock(return_value=True), mock.Mock()
        observed = []
        states = iter([("neuro", False, 5), ("neuro", True, 5), ("neuro", True, 2),
                       ("neuro", True, 5), ("oncology", True, 5)])
        stop.is_set.side_effect = lambda: len(observed) == 5
        stop.wait.side_effect = lambda _: observed.append(True)

        def load():
            cfg.profile, enabled, minute = next(states)
            cfg.scheduled.update(enabled=enabled, hour=8, minute=minute)
            return cfg

        def record(config, due):
            start(config.profile, due)
            return True

        run_schedule(stop, load, record, now=lambda: current)
        first = current.replace(second=0)
        self.assertEqual(start.call_args_list, [mock.call("neuro", first),
                         mock.call("neuro", first.replace(minute=2)), mock.call("oncology", first)])

    def test_active_schedule_waits_for_manual_search_then_runs_once(self):
        from datetime import datetime
        from itertools import count
        from threading import Event
        from neurodaily.desktop_schedule import run_schedule

        cfg = DEFAULT_CONFIG()
        cfg.scheduled = {"enabled": True, "hour": 8, "minute": 0}
        times = [datetime(2026, 11, 20, 7, 58), datetime(2026, 11, 20, 7, 59),
                 datetime(2026, 11, 20, 8, 0),
                 datetime(2026, 11, 20, 8, 3), datetime(2026, 11, 20, 8, 5),
                 datetime(2026, 11, 21, 8, 0)]
        stop = Event()
        start = mock.Mock(side_effect=(False, True, True))
        checks = iter(times)
        pauses = count(1)

        def wait(_seconds):
            if next(pauses) == len(times):
                stop.set()

        with mock.patch.object(stop, "wait", side_effect=wait):
            run_schedule(stop, lambda: cfg, start, now=lambda: next(checks))
        self.assertEqual([call.args[1] for call in start.call_args_list],
                         [datetime(2026, 11, 20, 8), datetime(2026, 11, 20, 8),
                          datetime(2026, 11, 21, 8)])

    def test_desktop_schedule_result_survives_restart_and_distinguishes_slots(self):
        from datetime import datetime
        from neurodaily.history import desktop_schedule_result, save_desktop_schedule_result

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "history.db")
            with mock.patch("neurodaily.history.db_path", return_value=path):
                due = datetime(2026, 11, 20, 8)
                save_desktop_schedule_result("neuro", due, "failed", "All sources failed")
                self.assertEqual(desktop_schedule_result("neuro")["status"], "failed")
                save_desktop_schedule_result("neuro", due, "completed")
                self.assertEqual(desktop_schedule_result("neuro", due)["status"], "completed")
                self.assertIsNone(desktop_schedule_result("oncology", due))
                self.assertIsNone(desktop_schedule_result("neuro", due.replace(minute=30)))


class SettingsJournalMetricsTests(unittest.TestCase):
    def test_settings_has_metric_inputs(self):
        from neurodaily.settings_page import SETTINGS_HTML
        for marker in ('class="j-if"', 'class="j-jcr"', 'class="j-cas"'):
            self.assertIn(marker, SETTINGS_HTML)


class SectionButtonTests(unittest.TestCase):
    def test_no_legacy_expand_collapse_pairs(self):
        from neurodaily.demo import build_result
        from neurodaily.render import render_html
        h = render_html(build_result())
        self.assertNotIn('class="sec-actions"', h)
        self.assertNotIn("toggleAll(", h)
        self.assertIn("initCollapsibleSections", h)


class SettingsSourcePreserveTests(unittest.TestCase):
    def test_settings_preserves_custom_source_fields(self):
        from neurodaily.settings_page import SETTINGS_HTML
        self.assertIn("Object.assign({},prev", SETTINGS_HTML)
        self.assertIn("BASE.sources&&BASE.sources[key]", SETTINGS_HTML)
