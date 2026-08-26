"""Render a DigestResult to a self-contained HTML report using Jinja2."""
from __future__ import annotations

import os
from datetime import datetime

from .config import Config, DEFAULT_CONFIG
from .digest import DigestResult

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _stdlib_loader():
    try:
        from jinja2 import Environment, FileSystemLoader
        return Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    except ImportError:
        return None


def render_html(result: DigestResult, config: Config | None = None) -> str:
    env = _stdlib_loader()
    if env is None:
        return _fallback_plain(result)
    try:
        template = env.get_template("report.html.j2")
        ctx = {
            "result": result,
            "today": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        return template.render(**ctx)
    except Exception:
        return _fallback_plain(result)


def _fallback_plain(result: DigestResult) -> str:
    """Minimal but readable HTML if Jinja2 is unavailable."""
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    for it in result.items:
        rows.append(
            f"<li>[{it.kind_label}][{it.source}] <b>{it.title}</b> "
            f"({it.date_display})<br>{it.summary[:300]}</li>"
        )
    health = "<br>".join(
        f"{h['source']}: {'ok' if h['ok'] else 'failed'} ({h['count']})"
        for h in result.health
    )
    return (
        f"<html><head><meta charset='utf-8'><title>NeuroDaily</title></head><body>"
        f"<h1>NeuroDaily — {today}</h1><p>{len(result.items)} items</p>"
        f"<ul>{''.join(rows)}</ul><hr><h2>Health</h2>{health}</body></html>"
    )
