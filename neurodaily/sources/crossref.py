"""Opt-in DOI enrichment from Crossref metadata."""
from __future__ import annotations

from urllib.parse import quote

from ..models import Item
from ..records import normalize_doi
from .http import get, mark_sampled, record_failure

BASE = "https://api.crossref.org/works"
_VERSION_LINKS = {"is-preprint-of": "published", "has-preprint": "preprint"}
_UPDATE_LINKS = {"correction", "retraction", "expression-of-concern", "withdrawal"}


def _update_links(rows, direction=""):
    if not isinstance(rows, list):
        return []
    links = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        doi = normalize_doi(str(row.get("DOI") or ""))
        kind = row.get("type")
        if doi and kind in _UPDATE_LINKS:
            links.append({"doi": doi, "url": f"https://doi.org/{doi}", "kind": kind,
                          "date": str(row.get("updated", {}).get("date-time", ""))[:10]
                          if isinstance(row.get("updated"), dict) else "", "direction": direction})
    return links


def _message(response):
    if response is None:
        return {}
    try:
        row = response.json()["message"]
        if isinstance(row, dict):
            return row
    except (ValueError, KeyError, TypeError):
        pass
    record_failure("Crossref returned an invalid metadata response")
    return {}


def _notices(dois):
    dois = [doi for doi in dois if "," not in doi]
    found = {}
    for offset in range(0, len(dois), 5):
        batch = dois[offset:offset + 5]
        if not batch:
            continue
        response = get(BASE, {"filter": ",".join(f"updates:{doi}" for doi in batch), "rows": 25},
                       timeout=5, retries=0)
        page = _message(response)
        if isinstance(page.get("total-results"), int) and page["total-results"] > 25:
            mark_sampled(truncated=True)
        rows = page.get("items")
        for row in rows if isinstance(rows, list) else ():
            if not isinstance(row, dict):
                continue
            notice_doi = normalize_doi(str(row.get("DOI") or ""))
            if not notice_doi:
                continue
            for target in _update_links(row.get("update-to")):
                if target["doi"] in batch:
                    found.setdefault(target["doi"], []).append(
                        {**target, "doi": notice_doi, "url": f"https://doi.org/{notice_doi}", "direction": "notice"})
    return found


def enrich(items: list[Item], config) -> int:
    opts = config.source_opts("crossref")
    if not opts.get("enabled"):
        return 0
    budget = max(1, int(opts.get("max_results", 1_000_000)))
    lookups = {}
    applied = 0
    for item in items:
        doi = normalize_doi(item.doi)
        if not doi or item.kind != "paper":
            continue
        if doi not in lookups:
            if len(lookups) >= budget:
                break
            lookups[doi] = _message(get(f"{BASE}/{quote(doi, safe='')}", timeout=5, retries=0))
        row = lookups[doi]
        if not row:
            continue
        relations = row.get("relation") or {}
        if isinstance(relations, dict):
            versions = item.extra.setdefault("related_versions", [])
            for relation, kind in _VERSION_LINKS.items():
                for related in relations.get(relation) or []:
                    if not isinstance(related, dict) or related.get("id-type") != "doi":
                        continue
                    target = normalize_doi(str(related.get("id") or ""))
                    if target and target != doi and not any(info.get("doi") == target for info in versions):
                        versions.append({"doi": target, "url": f"https://doi.org/{target}", "kind": kind})
        updates = (_update_links(row.get("update-to"), "notice_for")
                   + _update_links(row.get("updated-by"), "notice"))
        if updates:
            item.extra["publication_updates"] = updates
        applied += 1
    notices = _notices(list(lookups))
    for item in items:
        doi = normalize_doi(item.doi)
        if item.kind == "paper" and doi in notices:
            updates = item.extra.setdefault("publication_updates", [])
            merged = {(entry["doi"], entry["kind"], entry["direction"]): entry
                      for entry in updates + notices[doi]}
            item.extra["publication_updates"] = list(merged.values())
    return applied
