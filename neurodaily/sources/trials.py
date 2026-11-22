"""ClinicalTrials.gov API v2 study registry updates."""
from __future__ import annotations

from collections import deque
from collections.abc import Iterator
from datetime import datetime, timedelta
from time import monotonic
from urllib.parse import quote

from .http import get, mark_sampled, parse_date_any, record_candidates, record_failure, record_query
from ..models import Item
from ..search import compile_scoped_search

BASE = "https://clinicaltrials.gov/api/v2/studies"
_TERMS_PER_QUERY = 5
_QUERY_BYTES = 900
_PAGE_SIZE = 100
_REQUEST_LIMIT = 24
_PREVIEW_REQUEST_LIMIT = 4
_TIME_LIMIT = 90.0
_PREVIEW_TIME_LIMIT = 20.0


def _trial_sites(value) -> list[dict]:
    """Keep public facility metadata and the registry's optional location point."""
    sites = []
    if not isinstance(value, list):
        return sites
    for location in value:
        if not isinstance(location, dict):
            continue
        site = {key: location[key].strip() for key in ("facility", "city", "state", "country")
                if isinstance(location.get(key), str) and location[key].strip()}
        if not site:
            continue
        point = location.get("geoPoint")
        if isinstance(point, dict):
            lat, lon = point.get("lat"), point.get("lon")
            if (type(lat) in (float, int) and type(lon) in (float, int)
                    and -90 <= lat <= 90 and -180 <= lon <= 180 and (lat or lon)):
                site["geoPoint"] = {"lat": lat, "lon": lon}
        sites.append(site)
    return sites


def _queries(config) -> Iterator[str]:
    """Use short OR batches of literal phrases instead of dropping extra terms."""
    plan = compile_scoped_search(config.search).get("trial")
    native = config.source_opts("trials").get("query", "").strip() or (plan.remote_query("trials") if plan else "")
    if native and len(quote(native, safe="")) <= _QUERY_BYTES:
        yield native
        return
    if native:
        mark_sampled(truncated=True)
        record_failure("The trial-specific query exceeded the request length limit; used the discipline terms.")
    values = [term for discipline in config.active_disciplines()
              for term in (*discipline.mesh_terms, *discipline.keywords)]
    values.extend(config.global_keywords)
    seen = set()
    batch: list[str] = []
    for term in values:
        literal = " ".join(term.replace('"', " ").replace("\\", " ").split())
        key = literal.casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        quoted = f'"{literal}"'
        if len(quote(quoted, safe="")) > _QUERY_BYTES:
            mark_sampled(truncated=True)
            record_failure("A ClinicalTrials.gov search phrase exceeded the request length limit")
            continue
        combined = " OR ".join([*batch, quoted])
        if len(batch) == _TERMS_PER_QUERY or len(quote(combined, safe="")) > _QUERY_BYTES:
            yield " OR ".join(batch)
            batch = []
        batch.append(quoted)
    if batch:
        yield " OR ".join(batch)


def _date_field(module, field):
    value = module.get(field)
    if isinstance(value, dict):
        value = value.get("date")
    return parse_date_any(value) if isinstance(value, str) else ""


def _item(study) -> Item | None:
    p = study.get("protocolSection", {})
    identification = p.get("identificationModule", {})
    status = p.get("statusModule", {})
    description = p.get("descriptionModule", {})
    sponsors = p.get("sponsorCollaboratorsModule", {})
    contacts = p.get("contactsLocationsModule", {})
    design = p.get("designModule", {})
    conditions = p.get("conditionsModule", {}).get("conditions", [])
    interventions = [entry["name"] for entry in p.get("armsInterventionsModule", {}).get("interventions", [])
                     if isinstance(entry, dict) and entry.get("name")]
    title = identification.get("briefTitle", "")
    nct = identification.get("nctId", "")
    if not isinstance(title, str) or not title.strip() or not isinstance(nct, str) or not nct.strip():
        return None
    nct = nct.strip().upper()
    dates = {name: _date_field(status, field) for name, field in (
        ("first_submitted", "studyFirstSubmitDate"),
        ("first_posted", "studyFirstPostDateStruct"),
        ("last_update_posted", "lastUpdatePostDateStruct"),
        ("results_first_submitted", "resultsFirstSubmitDate"),
        ("results_first_posted", "resultsFirstPostDateStruct"),
    )}
    events = [{"kind": kind, "date": dates[date_key]} for kind, date_key in (
        ("registered", "first_posted"), ("registry_updated", "last_update_posted"),
        ("results_posted", "results_first_posted"),
    ) if dates[date_key]]

    authors, affiliations, corresponding = [], [], []
    for official in contacts.get("overallOfficials", []):
        name = official.get("name", "")
        affiliation = official.get("affiliation", "")
        if name:
            authors.append(name)
            if official.get("role") == "PRINCIPAL_INVESTIGATOR":
                corresponding.append(name)
        if affiliation:
            affiliations.append(affiliation)
    sponsor = sponsors.get("leadSponsor", {}).get("name", "")
    if sponsor and sponsor not in affiliations:
        affiliations.append(sponsor)
    sites = _trial_sites(contacts.get("locations"))
    for site in sites:
        label = ", ".join(site[key] for key in ("facility", "city", "country") if site.get(key))
        if label and label not in affiliations:
            affiliations.append(label)

    extra = {
        "nct": nct, "status": status.get("overallStatus", ""), "conditions": conditions,
        "interventions": interventions,
        "phase": design.get("phases", []), "sponsor": sponsor, "trial_sites": sites,
        "enrollment": design.get("enrollmentInfo", {}).get("count"),
        "has_results": study.get("hasResults") is True or bool(dates["results_first_posted"]),
        "trial_dates": {name: date for name, date in dates.items() if date}, "trial_events": events,
    }
    if dates["first_posted"]:
        extra["source_discovered_at"] = dates["first_posted"]
    return Item(title=title, url=f"https://clinicaltrials.gov/study/{nct}",
                summary=description.get("briefSummary", "")[:1200], authors=authors,
                affiliations=affiliations, corresponding=corresponding, source="trials", kind="trial",
                date=dates["last_update_posted"] or dates["first_posted"], tags=conditions, extra=extra)


def fetch(config, logger=None) -> list[Item]:
    opts = config.source_opts("trials")
    preview = opts.get("preview", False)
    limit = _PREVIEW_REQUEST_LIMIT if preview else _REQUEST_LIMIT
    max_results = max(1, int(opts.get("max_results", 10)))
    if preview:
        max_results = min(max_results, 30)
    lookback = int(opts.get("lookback_days", 60))
    cutoff = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")
    filters = f"AREA[LastUpdatePostDate]RANGE[{cutoff},MAX]"

    pending = deque((query, "", set()) for query in _queries(config))
    initial_queries = len(pending)
    items: dict[str, Item] = {}
    requests = 0
    deadline = monotonic() + (_PREVIEW_TIME_LIMIT if preview else _TIME_LIMIT)
    # Inspect the first page for every topic batch before filling further pages.
    while pending and requests < limit and (requests < initial_queries or len(items) < max_results):
        remaining = deadline - monotonic()
        if remaining <= 0:
            break
        query, token, seen_tokens = pending.popleft()
        params = {"query.term": query, "pageSize": min(max_results, _PAGE_SIZE), "format": "json",
                  "sort": "LastUpdatePostDate:desc", "filter.advanced": filters}
        if token:
            params["pageToken"] = token
        else:
            record_query(f"{query} · {filters}")
        requests += 1
        timeout = min(8.0 if preview else 15.0, remaining)
        resp = get(BASE, params=params, connect_close=True, user_agent="python-httpx",
                   timeout=timeout, retries=1 if not preview and remaining >= timeout * 2 + 5 else 0)
        if resp is None:
            continue
        try:
            data = resp.json()
            studies = data["studies"]
            if not isinstance(studies, list):
                raise ValueError("invalid trial list")
        except (ValueError, TypeError, KeyError):
            record_failure("Invalid ClinicalTrials.gov API response")
            continue
        record_candidates(len(studies))
        invalid = False
        for study in studies:
            try:
                item = _item(study)
            except (AttributeError, TypeError):
                item = None
            if item is None:
                invalid = True
                continue
            nct = item.extra["nct"]
            if nct not in items or items[nct].date < item.date:
                items[nct] = item
        if invalid:
            record_failure("ClinicalTrials.gov returned a study without valid registry metadata")

        next_token = data.get("nextPageToken")
        if next_token:
            if not isinstance(next_token, str) or not next_token.strip() or next_token in seen_tokens:
                mark_sampled(truncated=True)
                record_failure("ClinicalTrials.gov returned an invalid or repeated page token")
            else:
                seen_tokens.add(next_token)
                pending.append((query, next_token, seen_tokens))

    if pending or len(items) > max_results:
        mark_sampled(truncated=True)
    budget_exhausted = requests >= limit or monotonic() >= deadline
    incomplete = requests < initial_queries or len(items) < max_results
    if pending and budget_exhausted and incomplete:
        record_failure("ClinicalTrials.gov request budget reached before all requested results were checked")
    ordered = sorted(items.values(), key=lambda item: (item.date, item.extra["nct"]), reverse=True)
    return ordered[:max_results]
