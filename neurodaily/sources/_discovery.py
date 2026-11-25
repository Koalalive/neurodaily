"""Metadata and request bounds shared by optional discovery sources."""

from datetime import date, timedelta
import re
from urllib.parse import urlsplit

from ..search import compile_search
from .http import mark_sampled, record_failure


def text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def records(value) -> list[dict]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def strings(value) -> list[str]:
    return list(dict.fromkeys(text(part) for part in value if text(part))) if isinstance(value, list) else []


def http_url(value) -> str:
    url = text(value)
    try:
        parts = urlsplit(url)
        return url if parts.scheme in {"http", "https"} and parts.hostname else ""
    except ValueError:
        return ""


def date_value(*values) -> str:
    """Keep publication date precision and skip malformed provider dates."""
    for value in values:
        raw = str(value) if type(value) is int else text(value)
        partial = raw.split("T", 1)[0]
        if not re.fullmatch(r"\d{4}(?:-\d\d(?:-\d\d)?)?", partial):
            continue
        try:
            full = {4: partial + "-01-01", 7: partial + "-01"}.get(len(partial), partial)
            date.fromisoformat(full)
            return partial
        except ValueError:
            continue
    return ""


def int_option(value, fallback: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError, OverflowError):
        return fallback


def request_scope(config, source: str, cap: int) -> tuple[dict, str, int]:
    opts = config.source_opts(source)
    requested = int_option(opts.get("max_results"), 50)
    if requested > cap:
        mark_sampled(truncated=True)
    limit = min(requested, cap)
    query = text(opts.get("query"))
    if not query:
        terms = [word for term in config.all_keywords()
                 if (word := " ".join(text(term).replace('"', " ").replace("\\", " ").split()))]
        if len(terms) > 6:
            mark_sampled()
        query = " OR ".join(f'"{term[:96]}"' for term in terms[:6])
    if not query or len(query) > 1000:
        record_failure(f"{source} needs a focused query of up to 1,000 characters.")
        return opts, "", limit
    return opts, query, limit


def fixed_bounds(opts, explicit=None) -> tuple[str, str] | None:
    evidence = opts.get("evidence_date_range")
    if not evidence and explicit is not None:
        return explicit
    window = evidence or opts.get("retrieval_date_range")
    if isinstance(window, (list, tuple)) and len(window) == 2:
        start, end = map(date_value, window)
        if len(start) == len(end) == 10:
            if explicit is not None:
                return max(start, explicit[0]), min(end, explicit[1])
            return start, end
    return explicit


def paper_bounds(config, opts) -> tuple[str, str]:
    bounds = opts.get("paper_date_range") or compile_search(config.search, config.journals).date_range
    if isinstance(bounds, (list, tuple)) and len(bounds) == 2:
        start, end = map(date_value, bounds)
        bounds = (start, end) if len(start) == len(end) == 10 else None
    else:
        bounds = None
    if window := fixed_bounds(opts, bounds):
        return window
    today = date.today()
    days = min(int_option(opts.get("lookback_days"), 7), 3650)
    return (today - timedelta(days=days)).isoformat(), today.isoformat()
