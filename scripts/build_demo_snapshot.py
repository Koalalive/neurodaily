#!/usr/bin/env python3
"""Build the public GitHub Pages demo in three languages.

Run from the repository root. It never sends email and strips client metadata
from the generated snapshots.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from neurodaily import ai_summary, api_billing
from neurodaily.config import Config
from neurodaily.digest import run
from neurodaily.render import render_html
from neurodaily.research_activity import enrich_geography
from neurodaily.topic_map import available, build_topics, enrich_topics

OUT = Path(os.environ.get("NEURODAILY_DEMO_DIR", "docs/demo"))
CONFIG = Path("config/demo.json")
EMAIL = re.compile(r"(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}")
LOCAL = re.compile(r"/Users/[^\s\"'<]+")


def clean(html: str) -> str:
    html = EMAIL.sub("[email hidden]", html)
    html = LOCAL.sub("[local path hidden]", html)
    html = re.sub(r'<meta name="nd-base" content="[^"]*">',
                  '<meta name="nd-base" content="">', html)
    # The public snapshot must not show non-functional workspace controls.
    html = re.sub(r'<div class="toolbar">[\s\S]*?</div>\s*</div>', '</div>', html, count=1)
    # The focus prompt belongs in the private daily report, not the public site.
    html = re.sub(r'<section id="prompt">[\s\S]*?</section>', '', html, count=1)
    html = re.sub(r'<a class="btn ghost" id="promptLink"[\s\S]*?</a>', '', html, count=1)
    html = html.replace("http://127.0.0.1:8031", "")
    return re.sub(r'href="/history/\d+"', 'href="#"', html)


def main() -> int:
    cfg = Config.load(str(CONFIG))
    cfg.windows["daily_paper_hours"] = 168
    result = run(cfg, check_duplicate=False, record=False, force=True, mode="daily")
    ai_summary.generate_all(result)
    # The public demo explicitly opts into the AI geography map. On a fresh
    # GitHub runner the local billing database starts with geo_enabled=false.
    api_billing.save_settings({"geo_enabled": True})
    enrich_geography(result)
    print(f"topic sklearn={available()} items={len(result.items)}", flush=True)
    try:
        ok = enrich_topics(result, force=True)
        print(f"topic enrich={ok} points={len((result.topics or {}).get('points', []))}", flush=True)
    except Exception:
        import traceback
        traceback.print_exc()
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in ("zh", "en", "ru"):
        (OUT / f"latest-report.{lang}.html").write_text(
            clean(render_html(result, locale=lang)), encoding="utf-8")
    print(f"demo updated: {len(result.items)} items; {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
