"""Policy/news source via RSS feeds (feedparser). Handles institutional press
releases, journal news, society announcements — fallback for policy/conference
signals when no structured API exists. Feeds are fetched concurrently."""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context

from .generic import entry_references
from .http import get, mark_sampled, parse_date_any, record_candidates, record_failure, record_query, strip_html
from .journalpapers import _doi
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


def _parse_feed(url: str, kind: str, *, preview: bool = False) -> list[Item]:
    """Parse one feed URL into Items (caller applies the result limit)."""
    # feedparser.parse(url) blocks without timeout and stalls the fetch pool.
    resp = get(url, timeout=8.0 if preview else 15.0, retries=0 if preview else 1, user_agent="python-httpx")
    if resp is None:
        record_failure(f"Policy RSS unavailable: {url}")
        return []
    try:
        parsed = feedparser.parse(resp.content)
    except Exception:
        record_failure(f"Policy RSS could not be parsed: {url}")
        return []
    if not parsed.entries and (parsed.get("bozo") or not parsed.get("version")):
        record_failure(f"Policy RSS is not a valid feed: {url}")
        return []
    record_candidates(len(parsed.entries))
    out: list[Item] = []
    seen_local: set[str] = set()
    for e in parsed.entries:
        link = e.get("link", "")
        title = e.get("title", "")
        if not title or not link or link in seen_local:
            continue
        seen_local.add(link)
        summary = _feed_content(e)
        extra = {"feed": parsed.get("feed", {}).get("title", url), "source_url": url}
        if kind == "paper":
            extra["journal"] = e.get("prism_publicationname") or extra["feed"]
            if summary:
                extra["abstract"] = summary
        extra["reference_urls"] = entry_references(e)
        out.append(Item(
            title=title,
            url=link,
            summary=summary,
            authors=[a.get("name", "") for a in e.get("authors", []) if a.get("name")],
            source="policy",
            kind=kind,
            date=parse_date_any(e.get("published", e.get("updated", ""))),
            doi=_doi(e) if kind == "paper" else "",
            tags=[],
            extra=extra,
        ))
    return out


def fetch(config, logger=None) -> list[Item]:
    if not HAS_FEEDPARSER:
        record_failure("RSS parsing is unavailable")
        return []
    opts = config.source_opts("policy")
    max_results = int(opts.get("max_results", 10))
    lookback = int(opts.get("lookback_days", 10))
    preview = bool(opts.get("preview"))

    feeds = config.policy_feeds
    if not feeds:
        return []
    from ..security import validate_http_url
    safe_feeds = []
    for url in feeds:
        try:
            validate_http_url(url, resolve=False)
            safe_feeds.append(url)
        except ValueError:
            record_failure(f"Blocked RSS URL: {url}")
    feeds = safe_feeds
    if not feeds:
        return []
    record_query(f"Policy RSS · {len(feeds)} feed(s)")
    mark_sampled(truncated=preview and len(feeds) > 8)
    if preview:
        feeds = feeds[:8]
    types = opts.get("feed_kinds") or {}
    journal_feeds = {journal.rss for journal in config.journals if journal.rss}
    journal_feeds.update({
        "https://www.nature.com/mp.rss", "https://www.nature.com/nm.rss",
        "https://www.nature.com/ncomms.rss", "https://www.cell.com/action/showFeed?type=etoc&feed=rss&jc=neuron",
    })

    all_items: list[Item] = []
    with ThreadPoolExecutor(max_workers=min(8, len(feeds))) as pool:
        futures = [pool.submit(copy_context().run, _parse_feed, url,
                               types.get(url) or ("paper" if url in journal_feeds else "news"), preview=preview)
                   for url in feeds]
        for future in futures:
            all_items.extend(future.result())

    seen: set[str] = set()
    deduped: list[Item] = []
    for it in all_items:
        identity = (it.kind, it.url)
        if identity in seen:
            continue
        seen.add(identity)
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
    if len(deduped) > max_results:
        mark_sampled(truncated=True)
    deduped = deduped[:max_results]

    # Fill in empty summaries by fetching the source page (concurrently, bounded).
    missing = [it for it in deduped if it.kind != "paper" and len(it.summary.strip()) < 20] if not preview else []
    if missing:
        with ThreadPoolExecutor(max_workers=min(12, len(missing))) as pool:
            futures = [pool.submit(copy_context().run, _fetch_meta_description, it.url) for it in missing]
            contents = [future.result() for future in futures]
        for it, content in zip(missing, contents):
            if content:
                it.summary = content
    return deduped
