"""arXiv API source.

Atom feed from http://export.arxiv.org/api/query
Query strategy: one or more category filters ANDed with keyword filters for
the configured disciplines, sorted by submission time.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from .http import get, parse_date_any
from ..models import Item

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def _escape_query(q: str) -> str:
    # arXiv query uses all: or cat: terms; quote phrases, escape double quotes.
    q = q.replace('"', r'\"')
    return q


def build_search_query(cats: list[str], keywords: list[str]) -> str:
    """Build `(cat:A OR cat:B) AND (all:"kw1" OR all:"kw2")` style query."""
    parts = []
    if cats:
        parts.append("(" + " OR ".join(f"cat:{_escape_query(c)}" for c in cats) + ")")
    if keywords:
        kw = [f"all:\"{k}\"" for k in keywords if k.strip()]
        if kw:
            parts.append("(" + " OR ".join(kw) + ")")
    return " AND ".join(parts)


def fetch(config, logger=None) -> list[Item]:
    opts = config.source_opts("arxiv")
    lookback = int(opts.get("lookback_days", 14))

    cats = config.all_arxiv_cats()
    keywords = [k.lower() for k in config.all_keywords()]
    if not cats:
        return []

    # Simple per-category query (fast, ~1-2s) then filter by recency + keywords
    # client-side. arXiv's API is slow when given long keyword OR queries, so we
    # let the date-sorted category feed provide candidates and filter locally.
    items: list[Item] = []
    seen_urls: set[str] = set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback)

    for cat in cats:
        params = {
            "search_query": f"cat:{cat}",
            "start": 0,
            # arXiv API response time grows sharply with max_results (500 entries
            # took ~80s vs ~2s for 20). A single day has few papers, so 60 covers
            # the full day; the digest shows ALL of them (no cap downstream).
            "max_results": 60,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        resp = get("https://export.arxiv.org/api/query", params=params, timeout=60.0)
        if resp is None:
            continue
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError:
            continue
        for entry in root.findall("atom:entry", NS):
            title = (entry.findtext("atom:title", "", NS) or "").strip().replace("\n", " ")
            idurl = (entry.findtext("atom:id", "", NS) or "").strip()
            if idurl in seen_urls:
                continue
            summary = (entry.findtext("atom:summary", "", NS) or "").strip()
            published = entry.findtext("atom:published", "", NS)
            # recency filter
            if published:
                try:
                    pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    if pub_dt < cutoff:
                        continue
                except ValueError:
                    pass
            # keyword filter (client-side)
            if keywords:
                hay = (title + " " + summary).lower()
                if not any(k in hay for k in keywords):
                    continue
            seen_urls.add(idurl)
            doi = ""
            for l in entry.findall("atom:link", NS):
                if l.get("title") == "doi" or "doi.org" in (l.get("href") or ""):
                    doi = l.get("href", "").split("doi.org/")[-1]
                    break
            authors = [a.findtext("atom:name", "", NS) for a in entry.findall("atom:author", NS)]
            primary = entry.find("arxiv:primary_category", NS)
            cat_label = primary.get("term", "") if primary is not None else ""
            items.append(Item(
                title=title,
                url=idurl,
                summary=summary[:1200],
                authors=[a for a in authors if a],
                source="arxiv",
                kind="paper",
                date=parse_date_any(published),
                doi=doi,
                tags=[cat_label] if cat_label else [],
                extra={"category": cat_label},
            ))
    return items
