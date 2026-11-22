"""Optional cross-day title/identifier deduplication."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import os
import re
from pathlib import Path

from .records import record_ids

SEEN_DAYS = 30


def _path(config) -> Path:
    try:
        root = Path(config.output_dir())
    except Exception:
        root = Path("output")
    return root / "seen.json"


def _key(item) -> str:
    ids = record_ids(item)
    if ids:
        return ids[0]
    return re.sub(r"[\W_]+", "", (item.title or "").casefold())[:80]


def filter_seen(items, config, today: date | None = None):
    if not (getattr(config, "output", {}) or {}).get("seen_dedup", False):
        return items
    today = today or date.today()
    path = _path(config)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        seen = data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        seen = {}
    cutoff = (today - timedelta(days=SEEN_DAYS)).isoformat()
    seen = {key: value for key, value in seen.items()
            if isinstance(value, str) and value >= cutoff}
    current = today.isoformat()
    kept = []
    for item in items:
        key = _key(item)
        if not key:
            kept.append(item)
            continue
        if seen.get(key) and seen[key] != current:
            continue
        seen[key] = current
        kept.append(item)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(seen, ensure_ascii=False, indent=0), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass
    return kept
