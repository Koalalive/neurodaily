"""Optional OpenAlex works metadata with a bounded keyless or authenticated search."""

import os
import re
from urllib.parse import quote

from ._discovery import date_value, http_url, mapping, paper_bounds, records, request_scope, strings, text
from .http import get, mark_sampled, record_candidates, record_failure, record_query, strip_html
from ..models import Item
from ..records import normalize_doi


BASE = "https://api.openalex.org/works"
_PAGE_SIZE = 50
_MAX_PAGES = 4


def _abstract(value) -> str:
    words = {}
    for word, positions in mapping(value).items():
        if not isinstance(word, str) or not isinstance(positions, list):
            continue
        for position in positions:
            if type(position) is int and 0 <= position < 4000:
                words.setdefault(position, word[:200])
    return strip_html(" ".join(words[index] for index in sorted(words)))[:24_000]


def _last_affiliations(row: dict) -> list[dict]:
    byline = row.get("authorships")
    if not isinstance(byline, list) or not byline or row.get("is_authors_truncated") is True:
        return []
    count = row.get("authors_count")
    last = mapping(byline[-1])
    author = mapping(last.get("author"))
    name = text(author.get("display_name"))
    byline_name = text(last.get("raw_author_name")) or name
    position = text(last.get("author_position"))
    if ((type(count) is int and count > len(byline)) or not name
            or re.search(r"\b(?:collaboration|consortium|working group)\b", byline_name, re.I)):
        return []
    if position and position != "last" and not (position == "first" and len(byline) == 1):
        return []
    if not position and len(byline) >= 100:
        return []

    institutions = records(last.get("institutions"))
    institutions_by_id = {text(inst.get("id")): inst for inst in institutions if text(inst.get("id"))}
    ids_by_address = {}
    for entry in records(last.get("affiliations")):
        if address := text(entry.get("raw_affiliation_string")):
            ids_by_address.setdefault(address, set()).update(strings(entry.get("institution_ids")))
    raw = strings([*strings(last.get("raw_affiliation_strings")), *ids_by_address])
    result = []
    for address in raw:
        identifiers = ids_by_address.get(address, set())
        matches = [institutions_by_id[identifier] for identifier in identifiers if identifier in institutions_by_id]
        if not identifiers:
            matches = [inst for inst in institutions if text(inst.get("display_name")).casefold() == address.casefold()]
        result.append(_affiliation(address, matches[0] if len(matches) == 1 and len(identifiers) <= 1 else {}))
    if not raw:
        for institution in institutions:
            if address := text(institution.get("display_name")):
                affiliation = _affiliation(address, institution)
                if affiliation not in result:
                    result.append(affiliation)
    return result


def _affiliation(address: str, institution: dict) -> dict:
    row = {"address": address}
    country = text(institution.get("country_code")).upper()
    if re.fullmatch(r"[A-Z]{2}", country):
        row["country"] = country
    if ror := text(institution.get("ror")):
        row["institution_id"] = ror
    return row


def _paper(row: dict) -> Item | None:
    title = strip_html(text(row.get("display_name")) or text(row.get("title")))
    identifiers = mapping(row.get("ids"))
    doi = normalize_doi(text(row.get("doi")) or text(identifiers.get("doi")))
    openalex_id = text(row.get("id")) or text(identifiers.get("openalex"))
    location = mapping(row.get("primary_location"))
    url = f"https://doi.org/{quote(doi, safe='/')}" if doi else (
        http_url(location.get("landing_page_url")) or http_url(openalex_id)
    )
    if not title or not url:
        return None

    authors, affiliations, corresponding = [], [], []
    country_codes = []
    for authorship in records(row.get("authorships")):
        author = text(mapping(authorship.get("author")).get("display_name"))
        if author:
            authors.append(author)
            if authorship.get("is_corresponding") is True:
                corresponding.append(author)
        raw = strings(authorship.get("raw_affiliation_strings"))
        institutions = records(authorship.get("institutions"))
        affiliations.extend(raw or strings([entry.get("display_name") for entry in institutions]))
        country_codes.extend(strings(authorship.get("countries")))
        country_codes.extend(strings([entry.get("country_code") for entry in institutions]))

    pub_date = date_value(row.get("publication_date"), row.get("publication_year"))
    source = mapping(location.get("source"))
    abstract = _abstract(row.get("abstract_inverted_index"))
    pmid = re.search(r"(?:^|/)(\d+)/?$", text(identifiers.get("pmid")))
    pmcid = re.search(r"(?:^|/)(PMC\d+)/?$", text(identifiers.get("pmcid")), flags=re.I)
    extra = {
        "openalex_id": openalex_id,
        "pmid": pmid[1] if pmid else "",
        "pmcid": pmcid[1].upper() if pmcid else "",
        "journal": text(source.get("display_name")),
        "issns": strings([*strings(source.get("issn")), source.get("issn_l")]),
        "publication_types": strings([row.get("type"), row.get("type_crossref")]),
        "keywords": strings([entry.get("display_name") for entry in records(row.get("keywords"))]),
        "mesh_terms": strings([entry.get("descriptor_name") for entry in records(row.get("mesh"))]),
        "abstract": abstract,
        "institution_countries": strings(country_codes),
        "last_author_affiliations": _last_affiliations(row),
    }
    citation_count = row.get("cited_by_count")
    oa = mapping(row.get("open_access")).get("is_oa")
    if type(citation_count) is int and citation_count >= 0:
        extra["openalex_cited_by_count"] = citation_count
    if type(oa) is bool:
        extra["is_open_access"] = oa
    if type(row.get("is_retracted")) is bool:
        extra["is_retracted"] = row["is_retracted"]
    return Item(title=title, url=url, doi=doi, authors=strings(authors), affiliations=strings(affiliations),
                corresponding=strings(corresponding), summary=abstract[:1200], source="openalex",
                kind="paper", date=pub_date,
                extra={key: value for key, value in extra.items() if value not in ("", [], None)})


def fetch(config, logger=None) -> list[Item]:
    opts, query, limit = request_scope(config, "openalex", _PAGE_SIZE * _MAX_PAGES)
    if not query:
        return []
    start, end = paper_bounds(config, opts)
    if start > end:
        return []
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    headers = {"Authorization": f"Bearer {key}"} if key else None
    record_query(f"{query} · {start} to {end}")
    params = {"search": query, "filter": f"from_publication_date:{start},to_publication_date:{end}",
              "sort": "publication_date:desc"}
    cursor = "*"
    seen_cursors = {cursor}
    fetched = 0
    items = []
    seen = set()
    for _ in range(_MAX_PAGES if key else 1):
        size = min(_PAGE_SIZE if key else 100, limit - fetched)
        page = {**params, "per_page": size}
        if key:
            page["cursor"] = cursor
        response = get(BASE, params=page, headers=headers, timeout=18, retries=1)
        if response is None:
            break
        try:
            payload = response.json()
            rows = payload["results"]
            if not isinstance(rows, list):
                raise ValueError("invalid OpenAlex result list")
        except (TypeError, ValueError, KeyError):
            record_failure("OpenAlex returned an invalid search response.")
            break
        record_candidates(len(rows))
        fetched += min(len(rows), size)
        for row in records(rows[:size]):
            item = _paper(row)
            if item and (identity := item.doi or item.url) not in seen:
                seen.add(identity)
                items.append(item)
        meta = mapping(payload.get("meta"))
        next_cursor = text(meta.get("next_cursor"))
        total = meta.get("count")
        more = (type(total) is int and fetched < total) or (type(total) is not int and bool(next_cursor))
        if len(rows) > size or (more and (not key or fetched >= limit or not next_cursor or next_cursor in seen_cursors)):
            mark_sampled(truncated=True)
        if not rows or not more or not key or fetched >= limit or not next_cursor or next_cursor in seen_cursors:
            break
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    else:
        mark_sampled(truncated=True)
    return items
