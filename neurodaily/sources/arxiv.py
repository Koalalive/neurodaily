"""arXiv API source.

Fetch recent category pages for legacy profiles and bounded pages for advanced
fielded searches. Complete abstracts are retained for local rule evaluation.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from .http import get, mark_sampled, parse_date_any, record_candidates, record_failure, record_query
from ._discovery import fixed_bounds
from ..models import Item

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "open": "http://a9.com/-/spec/opensearch/1.1/",
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
        kw = [f'all:"{_escape_query(k)}"' for k in keywords if k.strip()]
        if kw:
            parts.append("(" + " OR ".join(kw) + ")")
    return " AND ".join(parts)


def _parse_entry(entry) -> Item | None:
    title = " ".join(entry.findtext("atom:title", "", NS).split())
    idurl = entry.findtext("atom:id", "", NS).strip()
    if not title or not idurl:
        return None
    summary = entry.findtext("atom:summary", "", NS).strip()
    published = entry.findtext("atom:published", "", NS)
    arxiv_id = idurl.rsplit("/abs/", 1)[-1]
    version = re.search(r"v(\d+)$", arxiv_id)
    extra = {"arxiv_id": re.sub(r"v\d+$", "", arxiv_id), "published_online": published}
    if version:
        extra["version"] = version[1]
    if summary:
        extra["abstract"] = summary
    doi = entry.findtext("arxiv:doi", "", NS).strip()
    if not doi:
        for link in entry.findall("atom:link", NS):
            href = link.get("href", "")
            if "doi.org/" in href:
                doi = href.split("doi.org/", 1)[1]
                break
    if doi and not doi.casefold().startswith("10.48550/arxiv."):
        extra["published_doi"] = doi
        doi = ""
    primary = entry.find("arxiv:primary_category", NS)
    category = primary.get("term", "") if primary is not None else ""
    if category:
        extra["category"] = category
    categories = [cat.get("term") for cat in entry.findall("atom:category", NS) if cat.get("term")]
    if categories:
        extra["categories"] = categories
    author_rows = entry.findall("atom:author", NS)
    authors = [author.findtext("atom:name", "", NS) for author in author_rows]
    byline_affiliations = [list(dict.fromkeys(aff.text.strip() for aff in author.findall("arxiv:affiliation", NS)
                                            if aff.text and aff.text.strip())) for author in author_rows]
    affiliations = list(dict.fromkeys(address for addresses in byline_affiliations for address in addresses))
    last_author = authors[-1].strip() if authors else ""
    collective = re.search(r"\b(?:collaboration|consortium|working group)\b", last_author, re.I)
    if last_author and not collective and byline_affiliations[-1]:
        extra["last_author_affiliations"] = [{"address": address} for address in byline_affiliations[-1]]
    return Item(
        title=title, url=idurl, summary=summary[:1200], authors=[a for a in authors if a],
        affiliations=affiliations,
        source="arxiv", kind="paper", date=parse_date_any(published), doi=doi,
        tags=[category] if category else [], extra=extra,
    )


def _page(query: str, offset: int, size: int, preview: bool):
    record_query(query)
    response = get("https://export.arxiv.org/api/query", params={
        "search_query": query,
        "start": offset,
        "max_results": size,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }, timeout=8.0 if preview else 60.0, retries=0 if preview else 2)
    if response is None:
        return None
    try:
        root = ET.fromstring(response.text)
        if root.tag != f"{{{NS['atom']}}}feed":
            raise ValueError("expected Atom feed")
        entries = root.findall("atom:entry", NS)
        if any(entry.findtext("atom:id", "", NS).startswith(("http://arxiv.org/api/errors", "https://arxiv.org/api/errors"))
               for entry in entries):
            raise ValueError("arXiv rejected the API query")
        total = root.findtext("open:totalResults", "", NS)
        return entries, int(total) if total.isdigit() else None
    except (ET.ParseError, ValueError):
        record_failure("Invalid arXiv API response")
        return None


def fetch(config, logger=None) -> list[Item]:
    opts = config.source_opts("arxiv")
    preview = opts.get("preview", False)
    max_results = int(opts.get("max_results", 60))
    lookback = int(opts.get("lookback_days", 14))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback)
    cats = config.all_arxiv_cats()
    plan = None
    if getattr(config, "search", None):
        from ..search import compile_search
        plan = compile_search(config.search)
    advanced = bool(plan and plan.active)
    window = fixed_bounds(opts, plan.date_range if advanced else None)
    if window and window[0] > window[1]:
        return []
    start, end = window or (cutoff.date().isoformat(), now.date().isoformat())
    date_term = f"submittedDate:[{start.replace('-', '')}0000 TO {end.replace('-', '')}2359]"
    if advanced:
        native = plan.remote_query("arxiv") or build_search_query(cats, [])
        queries = [f"({native}) AND {date_term}" if native else date_term]
        limit = min(max_results, 30 if preview else 240)
        keywords = []
    else:
        queries = [f"cat:{_escape_query(cat)}" for cat in cats]
        if window:
            queries = [f"{query} AND {date_term}" for query in queries]
            cutoff = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
        if preview and len(queries) > 4:
            queries = queries[:4]
            mark_sampled(truncated=True)
        limit = min(max_results, 30 if preview else 60)
        keywords = [k.casefold() for k in config.all_keywords()]

    items: list[Item] = []
    seen_urls: set[str] = set()
    for query in queries:
        offset = 0
        total = None
        while offset < limit:
            size = min(60, limit - offset)
            result = _page(query, offset, size, preview)
            if result is None:
                break
            entries, reported_total = result
            if offset == 0:
                total = reported_total
                if advanced and total is not None:
                    record_candidates(total)
            if not advanced or total is None:
                record_candidates(len(entries))
            for entry in entries:
                item = _parse_entry(entry)
                if item is None or item.url in seen_urls:
                    continue
                if not advanced and item.extra.get("published_online"):
                    try:
                        published = datetime.fromisoformat(item.extra["published_online"].replace("Z", "+00:00"))
                        if published.tzinfo is None:
                            published = published.replace(tzinfo=timezone.utc)
                        if published < cutoff:
                            continue
                    except ValueError:
                        pass
                if keywords:
                    hay = f"{item.title} {item.extra.get('abstract', '')}".casefold()
                    if not any(k in hay for k in keywords):
                        continue
                seen_urls.add(item.url)
                items.append(item)
            offset += len(entries)
            if not advanced or len(entries) < size or (total is not None and offset >= total):
                break
        if offset >= limit and (total is None or offset < total):
            mark_sampled(truncated=True)
    return items
