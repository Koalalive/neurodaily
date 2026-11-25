"""Curated conference calendar; no scraping and no region split."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from importlib.resources import files
import json

from ..models import Item
from ._discovery import fixed_bounds
from .http import record_candidates, record_query


def _date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def fetch(config, logger=None) -> list[Item]:
    opts = config.source_opts("conferences")
    if opts.get("enabled", True) is False:
        return []
    record_query("Curated academic conference calendar")
    try:
        rows = json.loads(files("neurodaily").joinpath("data", "conferences.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(rows, list):
        return []
    record_candidates(len(rows))
    # The catalogue deliberately includes future meetings relative to the run.
    fixed = fixed_bounds(opts)
    today = date.fromisoformat(fixed[1]) if fixed else date.today()
    horizon = today + timedelta(days=730)
    limit = max(1, int(opts.get("max_results", 50)))
    profiles = {"neuro", "oncology", "critical-care"}
    profile = (opts.get("query") or config.profile).casefold().strip()
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if profile in profiles and profile not in row.get("profiles", ["neuro"]):
            continue
        start, end = _date(row.get("start")), _date(row.get("end"))
        if not start or not end or end < today or start > horizon:
            continue
        deadlines = []
        for deadline in row.get("deadlines") or []:
            if not isinstance(deadline, dict):
                continue
            day = _date(deadline.get("date"))
            if day and day >= today:
                deadlines.append({"label": str(deadline.get("label") or "截止"), "date": day.isoformat()})
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        days = (start - today).days
        when = "正在召开" if days <= 0 else f"还有 {days} 天"
        parts = [str(row.get("full") or "").strip(), str(row.get("city") or "").strip(), when]
        parts += [f"{d['label']} {d['date']}" for d in deadlines]
        summary = " · ".join(part for part in parts if part)
        out.append(Item(
            title=name, url=str(row.get("url") or ""), summary=summary,
            source="conferences", kind="conference", date=start.isoformat(),
            extra={"start": start.isoformat(), "end": end.isoformat(),
                   "city": str(row.get("city") or ""), "deadlines": deadlines,
                   "venue": row.get("venue"),
                   "full": str(row.get("full") or "")},
        ))
        if len(out) >= limit:
            break
    return out
