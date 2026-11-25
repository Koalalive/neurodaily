"""Optional GDELT DOC discovery with headlines and links from its article index."""

from datetime import datetime, timezone

from ._discovery import date_value, fixed_bounds, http_url, int_option, records, request_scope, text
from .http import get, mark_sampled, record_candidates, record_failure, record_query, strip_html
from ..models import Item


BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
_MAX_RESULTS = 100


def _seen_at(value) -> str:
    try:
        seen = datetime.strptime(text(value), "%Y%m%dT%H%M%SZ")
        return seen.replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return ""


def fetch(config, logger=None) -> list[Item]:
    opts, query, limit = request_scope(config, "gdelt", _MAX_RESULTS)
    if not query:
        return []
    if not text(opts.get("query")) and " OR " in query:
        query = f"({query})"
    days = min(int_option(opts.get("lookback_days"), 3), 365)
    window = fixed_bounds(opts)
    if window:
        start, end = window
        if start > end:
            return []
        bounds = {"startdatetime": start.replace("-", "") + "000000",
                  "enddatetime": end.replace("-", "") + "235959"}
        record_query(f"{query} · {start} to {end}")
    else:
        bounds = {"timespan": f"{days}d"}
        record_query(f"{query} · last {days} day(s)")
    response = get(BASE, params={"query": query, "mode": "artlist", "format": "json",
                                 "sort": "datedesc", "maxrecords": limit, **bounds}, timeout=18, retries=0)
    if response is None:
        return []
    try:
        rows = response.json()["articles"]
        if not isinstance(rows, list):
            raise ValueError("invalid GDELT article list")
    except (TypeError, ValueError, KeyError):
        record_failure("GDELT returned an invalid article-list response.")
        return []
    record_candidates(len(rows))
    mark_sampled(truncated=len(rows) >= limit)
    items = []
    seen = set()
    for row in records(rows[:limit]):
        title, url = strip_html(text(row.get("title"))), http_url(row.get("url"))
        if not title or not url or url in seen:
            continue
        seen.add(url)
        seen_at = _seen_at(row.get("seendate"))
        extra = {
            "indexed_at": seen_at,
            "date_kind": "indexed" if seen_at else "",
            "publisher_domain": text(row.get("domain")),
            "publisher_country": text(row.get("sourcecountry")),
            "language": text(row.get("language")),
        }
        items.append(Item(title=title, url=url, source="gdelt", kind="news",
                          date=date_value(seen_at),
                          extra={key: value for key, value in extra.items() if value}))
    return items
