"""Top-journal paper source.

Instead of broad keyword search, this pulls from the configured ``journals``
watch-list RSS feeds and keeps only entries that match the user's research
interests (discipline keywords + global keywords). Emits ``paper`` Items tagged
with the source journal, so ``Latest Papers`` surfaces top-journal work first.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from ._discovery import fixed_bounds

from .http import get, mark_sampled, parse_date_any, record_candidates, record_failure, record_query, strip_html
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
    return strip_html(raw)


def _doi(entry) -> str:
    for value in (entry.get("prism_doi"), entry.get("dc_identifier"), entry.get("id"), entry.get("link")):
        text = str(value or "").strip()
        if text.casefold().startswith("doi:"):
            text = text[4:].strip()
        if text.startswith(("https://", "http://")):
            parsed = urlsplit(text)
            text = parsed.path.lstrip("/") if parsed.hostname in ("doi.org", "dx.doi.org") else ""
        if re.fullmatch(r"10\.\d+/\S+", text, re.I):
            return text
    return ""


def _parse_feed(config, journal_name: str, rss_url: str, *, advanced: bool = False,
                preview: bool = False, aliases=(), issns=()) -> list[Item]:
    resp = get(rss_url, timeout=8.0 if preview else 15.0,
               retries=0 if preview else 1, user_agent="python-httpx", untrusted_url=True)
    if resp is None:
        return []
    try:
        parsed = feedparser.parse(resp.content)
    except Exception:
        record_failure("A journal RSS feed could not be parsed")
        return []
    if not parsed.entries and (parsed.get("bozo") or not parsed.get("version")):
        record_failure("A journal RSS endpoint did not return a valid feed")
        return []
    record_candidates(len(parsed.entries))
    out: list[Item] = []
    seen: set[str] = set()
    for e in parsed.entries:
        link = e.get("link", "")
        title = e.get("title", "")
        if not title or not link or link in seen:
            continue
        seen.add(link)
        content = _feed_content(e)
        if not advanced and not _relevant(config, title, content):
            continue
        raw_authors = [a.get("name", "") for a in e.get("authors", []) if a.get("name")]
        authors, corresponding = _split_authors_with_corresponding(raw_authors)
        extra = {"journal": journal_name, "feed": rss_url}
        if aliases:
            extra["journal_aliases"] = list(aliases)
        identifiers = list(dict.fromkeys(key for key in
                           [*issns, e.get("prism_issn"), e.get("prism_eissn")] if key))
        if identifiers:
            extra["issns"] = identifiers
        if content and content.casefold().strip() != title.casefold().strip():
            extra["abstract"] = content
        out.append(Item(
            title=title,
            url=link,
            summary=content[:1500] if "abstract" in extra else "",
            authors=authors,
            corresponding=corresponding,
            source=journal_name,
            kind="paper",
            date=parse_date_any(e.get("published", e.get("updated", ""))),
            doi=_doi(e),
            tags=["top-journal"],
            extra=extra,
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
        record_failure("RSS parsing is unavailable")
        return []
    opts = config.source_opts("journal")
    max_results = int(opts.get("max_results", 25))
    lookback = int(opts.get("lookback_days", 7))
    preview = opts.get("preview", False)
    plan = None
    if getattr(config, "search", None):
        from ..search import compile_search
        plan = compile_search(config.search, config.journals)
    advanced = bool(plan and plan.active)
    bounds = plan.date_range if advanced else None
    window = fixed_bounds(opts) and fixed_bounds(opts, bounds)
    if window and window[0] > window[1]:
        return []

    feeds = [journal for journal in config.journals if journal.rss]
    if not feeds:
        return []
    if preview and plan and plan.journals:
        feeds.sort(key=lambda journal: not plan.preferred_journal(Item(
            title=journal.name, extra={"journal": journal.name, "issns": journal.issns,
                                       "journal_aliases": journal.aliases})))
    mark_sampled(truncated=preview and len(feeds) > 8)
    if preview:
        feeds = feeds[:8]
    record_query(f"Journal RSS · {len(feeds)} feed(s)")

    all_items: list[Item] = []
    with ThreadPoolExecutor(max_workers=min(8, len(feeds))) as pool:
        futures = [
            pool.submit(copy_context().run, _parse_feed, config, journal.name, journal.rss,
                        advanced=advanced, preview=preview, aliases=journal.aliases, issns=journal.issns)
            for journal in feeds
        ]
        for f in futures:
            try:
                all_items.extend(f.result())
            except Exception:
                record_failure("A journal RSS feed returned incomplete paper metadata")

    seen: set[str] = set()
    deduped: list[Item] = []
    for it in all_items:
        if it.url and it.url in seen:
            continue
        if it.url:
            seen.add(it.url)
        deduped.append(it)
    # Strict same-day filter: journal feeds return dozens of historical articles,
    # so keep only entries published today (lookback_days=1 == today).
    if window:
        start, end = window
        deduped = [it for it in deduped if not it.date or start <= it.date[:10] <= end]
    elif not bounds:  # Explicit bounds and incomplete dates are checked by the advanced matcher.
        if lookback <= 1:
            today = datetime.now().strftime("%Y-%m-%d")
            deduped = [it for it in deduped if it.date.startswith(today)]
        else:
            cutoff = datetime.now() - timedelta(days=lookback)
            cutoff_s = cutoff.strftime("%Y-%m-%d")
            deduped = [it for it in deduped if it.date >= cutoff_s]
    deduped.sort(key=lambda i: i.date or "0000-00-00", reverse=True)
    if len(deduped) > max_results:
        mark_sampled(truncated=True)
    return deduped[:max_results]
