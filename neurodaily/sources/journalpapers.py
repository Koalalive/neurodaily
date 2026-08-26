"""Top-journal paper source.

Instead of broad keyword search, this pulls from the configured ``journals``
watch-list RSS feeds and keeps only entries that match the user's research
interests (discipline keywords + global keywords). Emits ``paper`` Items tagged
with the source journal, so ``Latest Papers`` surfaces top-journal work first.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

from .http import get, parse_date_any, strip_html
from ..models import Item

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False


def _relevant(config, title: str, summary: str) -> bool:
    """True if the entry looks relevant to the configured research interests."""
    kw = [k.lower() for k in config.all_keywords()]
    if not kw:
        return True
    hay = (title + " " + summary).lower()
    return any(k in hay for k in kw)


def _feed_content(e) -> str:
    """Best text from a feedparser entry across summary/description/content."""
    raw = e.get("summary") or e.get("description") or ""
    if not raw and e.get("content"):
        raw = " ".join(c.get("value", "") for c in e.get("content", []))
    return strip_html(raw[:1500])


def _parse_feed(config, journal_name: str, rss_url: str) -> list[Item]:
    resp = get(rss_url, timeout=15.0, retries=1, user_agent="python-httpx")
    if resp is None:
        return []
    try:
        parsed = feedparser.parse(resp.content)
    except Exception:
        return []
    out: list[Item] = []
    seen: set[str] = set()
    for e in parsed.entries:
        link = e.get("link", "")
        title = e.get("title", "")
        if not title or not link or link in seen:
            continue
        seen.add(link)
        summary = _feed_content(e)
        if not _relevant(config, title, summary):
            continue
        raw_authors = [a.get("name", "") for a in e.get("authors", []) if a.get("name")]
        authors, corresponding = _split_authors_with_corresponding(raw_authors)
        out.append(Item(
            title=title,
            url=link,
            summary=summary,
            authors=authors,
            corresponding=corresponding,
            source=journal_name,
            kind="paper",
            date=parse_date_any(e.get("published", e.get("updated", ""))),
            doi="",
            tags=["top-journal"],
            extra={"journal": journal_name, "feed": rss_url},
        ))
    return out


def _split_authors_with_corresponding(author_strings: list[str]) -> tuple[list[str], list[str]]:
    """Split combined author strings into names; detect corresponding markers.

    Some journal feeds return one string like "A. One, B. Two *" per entry, or a
    single combined author blob. We split on commas/semicolons and flag names that
    carry a correspondence marker (``*``, ``✉``, ``†``) as corresponding authors.
    """
    authors: list[str] = []
    corresponding: list[str] = []
    markers = ("*", "✉", "†", "corresponding", "correspondence", "to whom")
    for blob in author_strings:
        parts = re.split(r"[;,]\s*|\s+and\s+", blob)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            # clean trailing markers for the display name but keep them for detection
            stripped = p
            for m in markers:
                stripped = stripped.replace(m, "")
            stripped = stripped.strip()
            if not stripped:
                continue
            authors.append(stripped)
            if any(m in p for m in markers):
                if stripped not in corresponding:
                    corresponding.append(stripped)
    return authors, corresponding


def fetch(config, logger=None) -> list[Item]:
    if not HAS_FEEDPARSER:
        return []
    opts = config.source_opts("journal")
    max_results = int(opts.get("max_results", 25))
    lookback = int(opts.get("lookback_days", 7))

    feeds = [(j.name, j.rss) for j in config.journals if j.rss]
    if not feeds:
        return []

    all_items: list[Item] = []
    with ThreadPoolExecutor(max_workers=min(8, len(feeds))) as pool:
        futures = [pool.submit(_parse_feed, config, name, url) for name, url in feeds]
        for f in futures:
            try:
                all_items.extend(f.result())
            except Exception:
                continue

    seen: set[str] = set()
    deduped: list[Item] = []
    for it in all_items:
        if it.url and it.url in seen:
            continue
        if it.url:
            seen.add(it.url)
        deduped.append(it)
    deduped.sort(key=lambda i: i.date or "0000-00-00", reverse=True)
    return deduped[:max_results]
