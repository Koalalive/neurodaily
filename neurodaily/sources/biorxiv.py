"""bioRxiv / medRxiv source via api.biorxiv.org / api.medrxiv.org detail API.

The detail API returns papers by date range. To focus on our disciplines we
filter by category + keyword matching client-side.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import re
import unicodedata

from .http import get, mark_sampled, parse_date_any, record_candidates, record_failure, record_query
from ..models import Item


def _native_categories(node) -> tuple[str, ...]:
    """Select a conservative set of exact categories for this source."""
    from ..search import Group, Term

    if isinstance(node, Term) and node.field == "CAT":
        name = " ".join(unicodedata.normalize("NFKC", node.value).casefold().split())
        return (name,) if name else ()
    if isinstance(node, Group):
        left = _native_categories(node.left)
        right = _native_categories(node.right)
        if node.operator == "AND":
            return left or right
        if left and right:
            return tuple(dict.fromkeys((*left, *right)))
    return ()


def _version(value) -> int:
    text = str(value or "")
    return int(text) if text.isdecimal() else 0


def fetch(config, logger=None) -> list[Item]:
    opts = config.source_opts("biorxiv")
    lookback = int(opts.get("lookback_days", 7))
    preview = opts.get("preview", False)
    plan = None
    if getattr(config, "search", None):
        from ..search import compile_search
        plan = compile_search(config.search)
    advanced = bool(plan and plan.active)

    end = datetime.now()
    start = end - timedelta(days=lookback)
    bounds = plan.date_range if advanced else None
    start_s, end_s = bounds or (start.date().isoformat(), end.date().isoformat())

    bio_cats = {cat.casefold() for d in config.active_disciplines() for cat in d.bio_cats}
    keywords = [] if advanced else [k.casefold() for k in config.all_keywords()]
    exact = _native_categories(plan.root) if advanced else ()
    category_limit = 2 if preview else 4
    categories = exact if 0 < len(exact) <= category_limit else ("",)
    max_results = min(int(opts.get("max_results", 100)), 30 if preview else 100)
    max_pages = 1 if preview else 7 // len(categories)
    items: dict[str, Item] = {}

    for server in ("biorxiv", "medrxiv"):
        server_limit = (max_results + 1) // 2 if preview and server == "biorxiv" else max_results
        for category in categories:
            description = f"{server}: {start_s} – {end_s}"
            record_query(f"{description} · category={category}" if category else description)
            offset = 0
            total = None
            stream_complete = False
            for _ in range(max_pages):
                response = get(
                    f"https://api.{server}.org/details/{server}/{start_s}/{end_s}/{offset}",
                    params={"category": category} if category else None,
                    timeout=8.0 if preview else 20.0,
                    retries=0 if preview else 2,
                )
                if response is None:
                    break
                try:
                    data = response.json()
                    collection = data["collection"]
                    if not isinstance(collection, list):
                        raise ValueError("invalid collection")
                    messages = data.get("messages") or []
                    raw_total = str(messages[0].get("total", "")) if messages else ""
                except (ValueError, KeyError, TypeError, AttributeError):
                    record_failure(f"Invalid {server} API response")
                    break
                if offset == 0 and raw_total.isdecimal():
                    total = int(raw_total)
                    record_candidates(total)
                if total is None:
                    record_candidates(len(collection))
                for record in collection:
                    if not isinstance(record, dict):
                        record_failure(f"Invalid {server} paper metadata")
                        continue
                    title = record.get("title") or ""
                    if not title:
                        continue
                    abstract = record.get("abstract") or ""
                    doi = record.get("doi") or ""
                    category_name = record.get("category") or ""
                    if not advanced and bio_cats and category_name and category_name.casefold() not in bio_cats:
                        continue
                    hay = f"{title} {abstract}".casefold()
                    if keywords and not any(k in hay for k in keywords):
                        continue
                    identifier = doi.casefold() or f"{server}:{title.casefold()}"
                    previous = items.get(identifier)
                    version = _version(record.get("version"))
                    if previous and _version(previous.extra.get("version")) >= version:
                        continue
                    if not previous and len(items) >= server_limit:
                        mark_sampled(truncated=True)
                        continue
                    items[identifier] = _item(server, record, title, abstract, doi, category_name)
                offset += len(collection)
                if len(collection) < 30 or (total is not None and offset >= total):
                    stream_complete = True
                    break
                if len(items) >= server_limit:
                    break
            if not stream_complete and offset:
                mark_sampled(truncated=True)
    return list(items.values())


def _name_key(value: str) -> tuple[str, ...]:
    display = unicodedata.normalize("NFKC", value).casefold()
    if "," in display:
        last, first = display.split(",", 1)
        display = f"{first} {last}"
    return tuple(re.findall(r"[^\W_]+", display))


def _matches_contact(author: tuple[str, ...], contact: tuple[str, ...]) -> bool:
    if len(author) != len(contact) or author[-1] != contact[-1]:
        return False
    # Preprint bylines may use given-name initials while the contact has the full name.
    return all(part == full or (len(part) == 1 and full.startswith(part))
               for part, full in zip(author, contact))


def _item(server: str, record: dict, title: str, abstract: str, doi: str, category: str) -> Item:
    authors = [a.strip() for a in (record.get("authors") or "").split(";") if a.strip()]
    institution = record.get("author_corresponding_institution") or ""
    contact = (record.get("author_corresponding") or "").strip()
    published = (record.get("published") or "").strip()
    version = record.get("version")
    extra = {"version": version, "license": record.get("license")}
    if authors and isinstance(institution, str) and institution.strip() and contact:
        key = _name_key(contact)
        if len(key) >= 2 and key[-1] not in {"collaboration", "consortium", "group"}:
            matches = [_matches_contact(_name_key(author), key) for author in authors]
            if matches[-1] and matches.count(True) == 1:
                extra["last_author_affiliations"] = [{"address": institution.strip()}]
    if abstract:
        extra["abstract"] = abstract
    if category:
        extra["category"] = category
    if re.fullmatch(r"10\.\d+/\S+", published, re.I):
        extra["published_doi"] = published
    date = parse_date_any(record.get("date"))
    if date:
        extra["published_online"] = date
    suffix = f"v{_version(version)}" if _version(version) else ""
    return Item(
        title=title, url=f"https://www.{server}.org/content/{doi}{suffix}" if doi else "",
        summary=abstract[:1200], authors=authors, affiliations=[institution] if institution else [],
        corresponding=[contact] if contact else [], source=server, kind="paper", date=date,
        doi=doi, tags=[category] if category else [], extra=extra,
    )
