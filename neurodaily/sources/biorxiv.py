"""bioRxiv / medRxiv source via api.biorxiv.org / api.medrxiv.org detail API.

The detail API returns papers by date range. To focus on our disciplines we
filter by category + keyword matching client-side.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from .http import get, parse_date_any
from ..models import Item


def fetch(config, logger=None) -> list[Item]:
    opts = config.source_opts("biorxiv")
    lookback = int(opts.get("lookback_days", 7))

    end = datetime.now()
    start = end - timedelta(days=lookback)
    start_s = start.strftime("%Y-%m-%d")
    end_s = end.strftime("%Y-%m-%d")

    bio_cats = set()
    for d in config.active_disciplines():
        bio_cats.update(d.bio_cats)
    keywords = [k.lower() for k in config.all_keywords()]

    items: list[Item] = []
    seen: set[str] = set()

    # The details API pages 30 records at a time; cap the number of pages fetched.
    # bioRxiv serves ALL fields per day and each API call is slow (~15-17s), so
    # paging deep is expensive; 8 pages (~240 records) covers a full day of
    # neuroscience preprints and stays within a tolerable runtime.
    max_pages = 8
    for server in ("biorxiv", "medrxiv"):
        cursor = 0
        page = 0
        while page < max_pages and cursor < 200:
            page += 1
            resp = get(f"https://api.{server}.org/details/{server}/{start_s}/{end_s}/{cursor}")
            if resp is None:
                break
            try:
                data = resp.json()
            except ValueError:
                break
            collection = data.get("collection", [])
            if not collection:
                break
            for rec in collection:
                title = rec.get("title", "")
                abstract = rec.get("abstract", "")
                doi = rec.get("doi", "")
                if doi in seen:
                    continue
                cat = rec.get("category", "")
                hay = (title + " " + abstract).lower()
                cat_ok = (not bio_cats) or cat in bio_cats or not cat
                if not cat_ok:
                    continue
                # require a keyword match so we don't pull random bio preprints
                if keywords and not any(k in hay for k in keywords):
                    continue
                seen.add(doi)
                authors = [a.strip() for a in rec.get("authors", "").split(";") if a.strip()]
                inst = rec.get("author_corresponding_institution", "")
                affiliations = [inst] if inst else []
                corr = rec.get("author_corresponding", "") or ""
                corresponding = [corr.strip()] if corr.strip() else []
                items.append(Item(
                    title=title,
                    url=f"https://www.{server}.org/content/{doi}v1",
                    summary=abstract[:1200],
                    authors=authors,
                    affiliations=affiliations,
                    corresponding=corresponding,
                    source=server,
                    kind="paper",
                    date=parse_date_any(rec.get("date", "")),
                    doi=doi,
                    tags=[cat],
                    extra={"version": rec.get("version"), "license": rec.get("license")},
                ))
                if len(items) >= 100:
                    break
            cursor += 30
        if len(items) >= 100:
            break
    return items
