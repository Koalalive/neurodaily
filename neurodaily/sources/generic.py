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
from html.parser import HTMLParser

from ._discovery import fixed_bounds
from .http import get, mark_sampled, parse_date_any, record_candidates, record_failure, record_query, strip_html
from ..models import Item
from ..security import external_url


class _References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.urls.extend(value for key, value in attrs if key == "href" and value)


def entry_references(entry) -> list[str]:
    parser = _References()
    parser.feed(str(entry.get("summary") or entry.get("description") or "")[:12_000])
    urls = parser.urls + [link["href"] for link in entry.get("links", [])
                         if isinstance(link, dict) and isinstance(link.get("href"), str)]
    return list(dict.fromkeys(url for value in urls if (url := external_url(value))))[:24]


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


def _excluded_date(date: str, lookback: int, bounds) -> bool:
    if bounds:
        return bool(date and not (bounds[0] <= date[:10] <= bounds[1]))
    return _too_old(date, lookback)


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
    from ..security import validate_http_url
    try:
        validate_http_url(url, resolve=False)
    except ValueError:
        record_failure("Blocked RSS URL")
        return []
    record_query("Configured RSS feed")
    mark_sampled()
    preview = bool(opts.get("preview"))
    resp = get(url, timeout=8.0 if preview else 15.0, retries=0 if preview else 1,
               user_agent="python-httpx", untrusted_url=True)
    if resp is None:
        if logger:
            logger.warning("generic rss %s: fetch failed", name)
        return []
    try:
        parsed = feedparser.parse(resp.content)
    except Exception:
        record_failure("The configured RSS feed could not be parsed")
        return []
    if not parsed.entries and (parsed.get("bozo") or not parsed.get("version")):
        record_failure("The configured RSS endpoint did not return a valid feed")
        return []
    record_candidates(len(parsed.entries))

    lookback = int(opts.get("lookback_days", 7) or 7)
    bounds = fixed_bounds(opts, opts.get("paper_date_range"))
    kind = _kind(opts)
    out: list[Item] = []
    seen: set[str] = set()
    limit = _limit(opts)
    for e in parsed.entries:
        link = e.get("link", "")
        title = e.get("title", "")
        if not title or not link or link in seen:
            continue
        seen.add(link)
        raw = e.get("summary") or e.get("description") or ""
        summary = strip_html(raw)
        date = _entry_date(e)
        if _excluded_date(date, lookback, bounds):
            continue
        if not _matches(f"{title} {summary}", opts.get("filter_keywords")):
            continue
        if len(out) >= limit:
            mark_sampled(truncated=True)
            break
        extra = {"feed": parsed.get("feed", {}).get("title", url), "source_url": url,
                 "reference_urls": entry_references(e)}
        if kind == "paper" and summary:
            extra["abstract"] = summary
        out.append(Item(
            title=title,
            url=link,
            summary=summary[:1500],
            authors=[a.get("name", "") for a in e.get("authors", []) if a.get("name")],
            source=name,
            kind=kind,
            date=date,
            extra=extra,
        ))
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
    record_query("Configured JSON API")
    mark_sampled()
    resp = get(url, timeout=20.0, retries=1, user_agent="python-httpx", untrusted_url=True)
    if resp is None:
        if logger:
            logger.warning("generic json %s: fetch failed", name)
        return []
    try:
        payload = resp.json()
    except ValueError:
        record_failure("The configured API did not return valid JSON")
        return []

    rows = _dig(payload, opts.get("items_path") or "")
    if not isinstance(rows, list):
        if not isinstance(payload, list):
            record_failure("The configured API items path did not contain a list")
            return []
        rows = payload
    record_candidates(len(rows))

    mapping = opts.get("map") or {}
    lookback = int(opts.get("lookback_days", 7) or 7)
    bounds = fixed_bounds(opts, opts.get("paper_date_range"))
    kind = _kind(opts)
    out: list[Item] = []
    limit = _limit(opts)
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get(mapping.get("title", "title"), "") or "").strip()
        link = str(row.get(mapping.get("url", "url"), "") or "").strip()
        if not title:
            continue
        summary = strip_html(str(row.get(mapping.get("summary", "summary"), "") or ""))
        date = parse_date_any(str(row.get(mapping.get("date", "date"), "") or ""))
        if _excluded_date(date, lookback, bounds):
            continue
        if not _matches(f"{title} {summary}", opts.get("filter_keywords")):
            continue
        if len(out) >= limit:
            mark_sampled(truncated=True)
            break
        doi = str(row.get(mapping.get("doi", "doi"), "") or "").strip()
        authors_raw = row.get(mapping.get("authors", "authors"), [])
        if isinstance(authors_raw, str):
            authors = [a.strip() for a in authors_raw.split(",") if a.strip()]
        elif isinstance(authors_raw, list):
            authors = [str(a) for a in authors_raw]
        else:
            authors = []
        extra = {"api": url}
        if kind == "paper" and summary:
            extra["abstract"] = summary
        out.append(Item(title=title, url=link, summary=summary[:1500], authors=authors,
                        source=name, kind=kind, date=date, doi=doi,
                        extra=extra))
    return out
