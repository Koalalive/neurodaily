"""Policy/news source via RSS feeds (feedparser). Handles institutional press
releases, journal news, society announcements — fallback for policy/conference
signals when no structured API exists. Feeds are fetched concurrently."""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

from .http import parse_date_any, get, strip_html
from ..models import Item

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False


def _feed_content(e) -> str:
    """Best text from a feedparser entry across summary/description/content."""
    raw = e.get("summary") or e.get("description") or ""
    if not raw and e.get("content"):
        raw = " ".join(c.get("value", "") for c in e.get("content", []))
    return strip_html(raw[:1500])


def _fetch_meta_description(url: str) -> str:
    """Fetch a page and pull its meta description (best-effort abstract).

    Some feeds (e.g. Nature subject feeds) supply only a title + link, so we fetch
    the article page to extract the abstract from ``<meta name=description>`` /
    ``og:description``. Timeout-bounded and non-fatal on failure.
    """
    resp = get(url, timeout=12.0, retries=1, user_agent="python-httpx")
    if resp is None:
        return ""
    text = resp.text
    # og:description first (often the real abstract on journal pages)
    for pattern in (r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\'](.*?)["\']',
                    r'<meta[^>]*content=["\'](.*?)["\'][^>]*property=["\']og:description["\']',
                    r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']',
                    r'<meta[^>]*content=["\'](.*?)["\'][^>]*name=["\']description["\']'):
        m = re.search(pattern, text, re.S | re.I)
        if m:
            val = strip_html(m.group(1)[:1500])
            if len(val) >= 40:
                return val
    return ""


def _parse_feed(url: str) -> list[Item]:
    """Parse one feed URL into Items (caller applies the result limit)."""
    # feedparser.parse(url) blocks without timeout and stalls the fetch pool.
    resp = get(url, timeout=15.0, retries=1, user_agent="python-httpx")
    if resp is None:
        return []
    try:
        parsed = feedparser.parse(resp.content)
    except Exception:
        return []
    if parsed.get("bozo") and not parsed.get("entries"):
        return []
    out: list[Item] = []
    seen_local: set[str] = set()
    for e in parsed.entries:
        link = e.get("link", "")
        title = e.get("title", "")
        if not title or not link or link in seen_local:
            continue
        seen_local.add(link)
        out.append(Item(
            title=title,
            url=link,
            summary=_feed_content(e),
            authors=[a.get("name", "") for a in e.get("authors", []) if a.get("name")],
            source="policy",
            kind="news",
            date=parse_date_any(e.get("published", e.get("updated", ""))),
            doi="",
            tags=[],
            extra={"feed": parsed.get("feed", {}).get("title", url),
                   "source_url": url},
        ))
    return out


def fetch(config, logger=None) -> list[Item]:
    if not HAS_FEEDPARSER:
        return []
    opts = config.source_opts("policy")
    max_results = int(opts.get("max_results", 10))
    lookback = int(opts.get("lookback_days", 10))

    feeds = config.policy_feeds
    if not feeds:
        return []

    all_items: list[Item] = []
    with ThreadPoolExecutor(max_workers=min(8, len(feeds))) as pool:
        for items in pool.map(_parse_feed, feeds):
            all_items.extend(items)

    seen: set[str] = set()
    deduped: list[Item] = []
    for it in all_items:
        if it.url in seen:
            continue
        seen.add(it.url)
        deduped.append(it)

    # Same-day filter: RSS feeds carry many historical items (weeks old), so
    # keep only entries published today when lookback_days=1.
    from datetime import datetime, timedelta
    if lookback <= 1:
        today = datetime.now().strftime("%Y-%m-%d")
        deduped = [it for it in deduped if it.date.startswith(today)]
    else:
        cutoff = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")
        deduped = [it for it in deduped if it.date >= cutoff]

    deduped.sort(key=lambda i: i.date or "0000-00-00", reverse=True)
    deduped = deduped[:max_results]

    # Fill in empty summaries by fetching the source page (concurrently, bounded).
    missing = [it for it in deduped if not it.summary or len(it.summary.strip()) < 20]
    if missing:
        with ThreadPoolExecutor(max_workers=min(12, len(missing))) as pool:
            contents = list(pool.map(lambda i: _fetch_meta_description(i.url), missing))
        for it, content in zip(missing, contents):
            if content:
                it.summary = content
    return deduped
