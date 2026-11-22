"""Optional Europe PMC literature metadata through its public REST search."""

import re
from urllib.parse import quote

from ._discovery import date_value, mapping, paper_bounds, records, request_scope, strings, text
from .http import get, mark_sampled, record_candidates, record_failure, record_query, strip_html
from ..models import Item
from ..records import normalize_doi


BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_PAGE_SIZE = 50
_MAX_PAGES = 4


def _last_affiliations(author: dict, details: list[dict]) -> list[dict]:
    if not text(author.get("lastName")) or text(author.get("collectiveName")):
        return []
    affiliations = {}
    for entry in [author, *details]:
        address = text(entry.get("affiliation"))
        if not address:
            continue
        row = affiliations.setdefault(address, {"address": address})
        identifier = text(entry.get("affiliationOrgId"))
        if re.fullmatch(r"(?:https?://)?ror\.org/(0[a-z0-9]{6}[0-9]{2})/?", identifier, re.I):
            row["institution_id"] = identifier
    return list(affiliations.values())


def _paper(row: dict) -> Item | None:
    title = strip_html(text(row.get("title")))
    provider_id, provider_source = text(row.get("id")), text(row.get("source"))
    doi = normalize_doi(text(row.get("doi")))
    url = ""
    if provider_id and provider_source:
        url = f"https://europepmc.org/article/{quote(provider_source, safe='')}/{quote(provider_id, safe='')}"
    elif doi:
        url = f"https://doi.org/{quote(doi, safe='/')}"
    if not title or not url:
        return None

    authors, affiliations = [], []
    last_affiliations = []
    author_rows = mapping(row.get("authorList")).get("author")
    if not isinstance(author_rows, list):
        author_rows = []
    for index, entry in enumerate(author_rows):
        author = mapping(entry)
        name = text(author.get("fullName"))
        if name:
            authors.append(name)
        affiliation = text(author.get("affiliation"))
        if affiliation:
            affiliations.append(affiliation)
        details = mapping(author.get("authorAffiliationDetailsList")).get("authorAffiliation")
        raw_affiliations = records(details)
        affiliations.extend(text(record.get("affiliation")) for record in raw_affiliations)
        if index == len(author_rows) - 1:
            last_affiliations = _last_affiliations(author, raw_affiliations)
    if not authors:
        authors = strings(text(row.get("authorString")).split(","))
    affiliations = strings(affiliations)

    journal_info = mapping(row.get("journalInfo"))
    journal = mapping(journal_info.get("journal"))
    pmid = text(row.get("pmid")) or (provider_id if provider_source == "MED" else "")
    pmcid = text(row.get("pmcid")) or (provider_id if provider_source == "PMC" else "")
    online = date_value(journal_info.get("electronicPublicationDate"))
    printed = date_value(journal_info.get("printPublicationDate"))
    first = date_value(row.get("firstPublicationDate"), online, printed, row.get("pubYear"))
    abstract = strip_html(text(row.get("abstractText")))[:24_000]
    extra = {
        "europe_pmc_id": provider_id,
        "europe_pmc_source": provider_source,
        "pmid": pmid if pmid.isdigit() else "",
        "pmcid": pmcid,
        "journal": text(journal.get("title")) or text(row.get("journalTitle")),
        "journal_abbreviation": text(journal.get("medlineAbbreviation")),
        "issns": strings([journal.get("issn"), journal.get("essn"), row.get("journalIssn")]),
        "publication_types": strings(mapping(row.get("pubTypeList")).get("pubType"))
        or strings(text(row.get("pubType")).split(";")),
        "mesh_terms": strings([heading.get("descriptorName") for heading in
                               records(mapping(row.get("meshHeadingList")).get("meshHeading"))]),
        "keywords": strings(mapping(row.get("keywordList")).get("keyword")),
        "abstract": abstract,
        "published_online": online,
        "published_print": printed,
        "indexed_date": date_value(row.get("firstIndexDate")),
        "last_author_affiliations": last_affiliations,
    }
    if row.get("isOpenAccess") in ("Y", "N"):
        extra["is_open_access"] = row["isOpenAccess"] == "Y"
    return Item(title=title, url=url, doi=doi, authors=authors, affiliations=affiliations,
                summary=abstract[:1200], source="europe_pmc", kind="paper", date=first,
                extra={key: value for key, value in extra.items() if value or value is False})


def last_author_metadata(dois: list[str]) -> dict[str, list[dict]]:
    """Look up missing affiliations by DOI independently of the discovery window."""
    eligible = {doi for doi in dois[:24] if re.fullmatch(r"10\.\d{4,9}/[\w./:()-]{1,100}", doi)}
    ordered = sorted(eligible)
    found = {}
    for offset in range(0, len(ordered), 8):
        query = " OR ".join(f'DOI:"{doi}"' for doi in ordered[offset:offset + 8])
        response = get(BASE, params={"query": query, "pageSize": 32, "format": "json", "resultType": "core"},
                       timeout=8, retries=0)
        if response is None:
            continue
        try:
            rows = response.json()["resultList"]["result"]
        except (KeyError, TypeError, ValueError):
            continue
        for row in records(rows):
            item = _paper(row)
            if item and item.doi in eligible and (addresses := item.extra.get("last_author_affiliations")):
                found.setdefault(item.doi, addresses)
    return found


def fetch(config, logger=None) -> list[Item]:
    opts, query, limit = request_scope(config, "europe_pmc", _PAGE_SIZE * _MAX_PAGES)
    if not query:
        return []
    start, end = paper_bounds(config, opts)
    if start > end:
        return []
    query = f"({query}) AND FIRST_PDATE:[{start} TO {end}] sort_date:y"
    record_query(query)
    cursor = "*"
    seen_cursors = {cursor}
    fetched = 0
    items = []
    seen = set()
    for _ in range(_MAX_PAGES):
        size = min(_PAGE_SIZE, limit - fetched)
        response = get(BASE, params={"query": query, "pageSize": size, "cursorMark": cursor,
                                     "format": "json", "resultType": "core"}, timeout=18, retries=1)
        if response is None:
            break
        try:
            payload = response.json()
            rows = payload["resultList"]["result"]
            if not isinstance(rows, list):
                raise ValueError("invalid Europe PMC result list")
        except (TypeError, ValueError, KeyError):
            record_failure("Europe PMC returned an invalid search response.")
            break
        record_candidates(len(rows))
        fetched += min(len(rows), size)
        for row in records(rows[:size]):
            item = _paper(row)
            if item and (key := item.doi or item.url) not in seen:
                seen.add(key)
                items.append(item)
        next_cursor = text(payload.get("nextCursorMark"))
        total = payload.get("hitCount")
        more = (type(total) is int and fetched < total) or (type(total) is not int and bool(next_cursor) and len(rows) >= size)
        if len(rows) > size or (more and (fetched >= limit or not next_cursor or next_cursor in seen_cursors)):
            mark_sampled(truncated=True)
        if not rows or not more or fetched >= limit or not next_cursor or next_cursor in seen_cursors:
            break
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    else:
        mark_sampled(truncated=True)
    return items
