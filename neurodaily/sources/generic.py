"""Config-defined sources: add a feed/API without writing Python.

Config example (config.json -> sources):
    "lab_news": {"type": "rss", "url": "https://example.org/feed.xml",
                 "kind": "news", "max_results": 20, "lookback_days": 7}
    "my_api":   {"type": "json_api", "url": "https://api.example.org/items",
                 "items_path": "data.items", "kind": "paper",
                 "map": {"title": "title", "url": "link",
                         "summary": "abstract", "date": "published"}}
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .http import get, parse_date_any, strip_html
from ..models import Item


def _limit(opts: dict) -> int:
    try:
        return max(1, int(opts.get("max_results", 20)))
    except (TypeError, ValueError):
        return 20


def _kind(opts: dict) -> str:
    return (opts.get("kind") or "news").strip()


def _matches(text: str, keywords) -> bool:
    if not keywords:
        return True
    low = (text or "").lower()
    return any(str(k).lower() in low for k in keywords if str(k).strip())


def _too_old(date_str: str, lookback_days: int) -> bool:
    if not date_str:
        return False
    try:
        d = datetime.fromisoformat(date_str[:10])
    except ValueError:
        return False
    return d < datetime.now() - timedelta(days=lookback_days)


def _entry_date(entry) -> str:
    for key in ("published_parsed", "updated_parsed"):
        st = entry.get(key)
        if st:
            try:
                return f"{st.tm_year:04d}-{st.tm_mon:02d}-{st.tm_mday:02d}"
            except Exception:
                pass
    return parse_date_any(entry.get("published", entry.get("updated", "")))


def fetch_rss(name: str, config, logger=None) -> list[Item]:
    import feedparser

    opts = config.source_opts(name)
    url = (opts.get("url") or "").strip()
    if not url:
        return []
    resp = get(url, timeout=15.0, retries=1, user_agent="python-httpx")
    if resp is None:
        if logger:
            logger.warning("generic rss %s: fetch failed", name)
        return []
    parsed = feedparser.parse(resp.content)
    if parsed.get("bozo") and not parsed.get("entries"):
        return []

    lookback = int(opts.get("lookback_days", 7) or 7)
    kind = _kind(opts)
    out: list[Item] = []
    seen: set[str] = set()
    for e in parsed.entries:
        link = e.get("link", "")
        title = e.get("title", "")
        if not title or not link or link in seen:
            continue
        seen.add(link)
        raw = e.get("summary") or e.get("description") or ""
        date = _entry_date(e)
        if _too_old(date, lookback):
            continue
        if not _matches(f"{title} {raw}", opts.get("filter_keywords")):
            continue
        out.append(Item(
            title=title,
            url=link,
            summary=strip_html(raw[:1500]),
            authors=[a.get("name", "") for a in e.get("authors", []) if a.get("name")],
            source=name,
            kind=kind,
            date=date,
            extra={"feed": parsed.get("feed", {}).get("title", url), "source_url": url},
        ))
        if len(out) >= _limit(opts):
            break
    return out


def _dig(data, path: str):
    cur = data
    for part in [p for p in (path or "").split(".") if p]:
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit():
            idx = int(part)
            cur = cur[idx] if 0 <= idx < len(cur) else None
        else:
            return None
    return cur


def fetch_json(name: str, config, logger=None) -> list[Item]:
    opts = config.source_opts(name)
    url = (opts.get("url") or "").strip()
    if not url:
        return []
    resp = get(url, timeout=20.0, retries=1, user_agent="python-httpx")
    if resp is None:
        if logger:
            logger.warning("generic json %s: fetch failed", name)
        return []
    try:
        payload = resp.json()
    except Exception:
        return []

    rows = _dig(payload, opts.get("items_path") or "")
    if not isinstance(rows, list):
        rows = payload if isinstance(payload, list) else []

    mapping = opts.get("map") or {}
    lookback = int(opts.get("lookback_days", 7) or 7)
    kind = _kind(opts)
    out: list[Item] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get(mapping.get("title", "title"), "") or "").strip()
        link = str(row.get(mapping.get("url", "url"), "") or "").strip()
        if not title:
            continue
        summary = strip_html(str(row.get(mapping.get("summary", "summary"), "") or "")[:1500])
        date = parse_date_any(str(row.get(mapping.get("date", "date"), "") or ""))
        if _too_old(date, lookback):
            continue
        if not _matches(f"{title} {summary}", opts.get("filter_keywords")):
            continue
        doi = str(row.get(mapping.get("doi", "doi"), "") or "").strip()
        authors_raw = row.get(mapping.get("authors", "authors"), [])
        if isinstance(authors_raw, str):
            authors = [a.strip() for a in authors_raw.split(",") if a.strip()]
        elif isinstance(authors_raw, list):
            authors = [str(a) for a in authors_raw]
        else:
            authors = []
        out.append(Item(title=title, url=link, summary=summary, authors=authors,
                        source=name, kind=kind, date=date, doi=doi,
                        extra={"api": url}))
        if len(out) >= _limit(opts):
            break
    return out
