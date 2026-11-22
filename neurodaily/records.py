"""Identify records across sources and preserve their individual provenance."""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from .models import Item

_DOI = re.compile(r"10\.\d{4,9}/\S+", re.I)
_PREPRINTS = {"arxiv", "biorxiv", "medrxiv"}


def normalize_doi(value: str) -> str:
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I)
    value = unquote(value).casefold()
    return value if _DOI.fullmatch(value) else ""


def _clean_url(value: str) -> str:
    try:
        url = urlsplit(value)
    except ValueError:
        return value
    params = [(key, val) for key, val in parse_qsl(url.query, keep_blank_values=True)
              if not key.lower().startswith("utm_") and key not in ("fbclid", "gclid")]
    return urlunsplit((url.scheme.lower(), url.netloc.lower(), url.path.rstrip("/"),
                       urlencode(sorted(params)), ""))


def record_ids(item: Item) -> tuple[str, ...]:
    ids = []
    doi = normalize_doi(item.doi or "")
    if not doi and re.match(r"^https?://(?:dx\.)?doi\.org/", item.url, flags=re.I):
        doi = normalize_doi(item.url.split("?", 1)[0].split("#", 1)[0])
    if doi:
        ids.append(f"doi:{doi}")
    pmid = str(item.extra.get("pmid") or "")
    if not pmid:
        found_pmid = re.match(r"https?://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", item.url)
        pmid = found_pmid[1] if found_pmid else ""
    if pmid.isdigit():
        ids.append(f"pmid:{pmid}")
    pmcid = str(item.extra.get("pmcid") or "").upper()
    if not pmcid:
        matched = re.search(r"/(?:pmc/)?articles/(PMC\d+)(?:[/?#]|$)", item.url, re.I)
        pmcid = matched[1].upper() if matched else ""
    if re.fullmatch(r"PMC\d+", pmcid):
        ids.append(f"pmcid:{pmcid}")
    if item.source == "arxiv":
        arxiv = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#]+)", item.url)
        if arxiv:
            ids.append("arxiv:" + re.sub(r"v\d+$", "", arxiv[1].removesuffix(".pdf")))
    nct = str(item.extra.get("nct_id") or item.extra.get("nctId") or "")
    if item.kind == "trial" and not nct:
        trial = re.search(r"clinicaltrials\.gov/study/(NCT\d+)", item.url, re.I)
        nct = trial[1] if trial else ""
    if re.fullmatch(r"NCT\d+", nct, re.I):
        ids.append(f"nct:{nct.upper()}")
    if item.url:
        ids.append(f"url:{_clean_url(item.url)}")
    if not ids:
        ids.append(f"title:{item.source}:{' '.join(item.title.casefold().split())}")
    return tuple(ids)


def _version(item: Item) -> str:
    value = item.extra.get("version")
    if value is not None and str(value).isdigit():
        return str(value)
    match = re.search(r"v(\d+)(?:\.pdf)?(?:[?#].*)?$", item.url)
    return match[1] if item.source in _PREPRINTS and match else ""


def delivery_ids(item: Item) -> tuple[str, ...]:
    aliases = item.extra.get("record_ids") or record_ids(item)
    version = _version(item)
    return tuple(f"{alias}:v{version}" if version else alias for alias in aliases)


def _priority(item: Item) -> tuple[bool, bool, int, int, str]:
    return (item.extra.get("search_match") == "match", item.source not in _PREPRINTS,
            int(_version(item) or 0),
            len(item.summary) + len(item.authors), item.source)


def merge_records(items: list[Item]) -> list[Item]:
    """Merge records sharing an identifier, deterministically retaining the richer record."""
    groups: dict[int, list[Item]] = {}
    seen: dict[tuple[str, str], int] = {}
    for index, item in enumerate(items):
        family = "coverage" if item.kind in {"news", "policy"} else item.kind
        ids = [(family, key) for key in record_ids(item)]
        other = sorted({seen[key] for key in ids if key in seen})
        group = other[0] if other else index
        members = groups.setdefault(group, [])
        for duplicate in other[1:]:
            for previous in groups.pop(duplicate):
                members.append(previous)
                for key in record_ids(previous):
                    seen[(family, key)] = group
        members.append(item)
        seen.update({key: group for key in ids})

    merged = []
    for members in groups.values():
        preferred = max(members, key=_priority)
        for value in ("doi", "summary", "authors", "affiliations", "corresponding"):
            if not getattr(preferred, value):
                setattr(preferred, value,
                        next((getattr(item, value) for item in members if getattr(item, value)),
                             getattr(preferred, value)))
        preferred.tags = list(dict.fromkeys(tag for item in members for tag in item.tags))
        preferred.extra["record_ids"] = list(dict.fromkeys(
            key for item in members for key in record_ids(item)
        ))
        preferred.extra["provenance"] = [
            {"source": source, "url": url}
            for source, url in sorted({(item.source, item.url) for item in members})
        ]
        for key in ("matched_rules", "missing_fields"):
            values = list(dict.fromkeys(value for item in members for value in item.extra.get(key, [])))
            if values and (key != "missing_fields" or preferred.extra.get("search_match") != "match"):
                preferred.extra[key] = values
        for item in members:
            for key, value in item.extra.items():
                if key not in preferred.extra and value:
                    preferred.extra[key] = value
        merged.append(preferred)

    by_doi = {normalize_doi(item.doi or ""): item for item in merged if item.doi}
    for item in merged:
        published_doi = normalize_doi(str(item.extra.get("published_doi") or ""))
        if not published_doi or published_doi == normalize_doi(item.doi or ""):
            continue
        published = by_doi.get(published_doi)
        item.extra["related_versions"] = [{
            "title": published.title if published else "正式发表版本",
            "url": published.url if published else f"https://doi.org/{published_doi}",
            "kind": "published", "doi": published_doi,
        }]
        if published:
            published.extra.setdefault("related_versions", []).append({
                "title": item.title, "url": item.url, "kind": "preprint", "doi": item.doi,
            })
    return merged
