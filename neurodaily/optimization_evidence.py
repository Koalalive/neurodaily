"""Read-only captures, replay, and independent verification for search optimization."""

from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from copy import deepcopy
from datetime import date, timedelta
from time import monotonic
from typing import Iterable
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from .config import Config
from .models import Item
from .records import merge_records, normalize_doi, record_ids
from .search import compile_scoped_search, compile_search
from .security import allow_private_sources, validate_http_url
from .sources import BUILTIN, fda, pubmed, registry_for, trials
from .sources.http import capture_requests, get

# Source order provides a bounded mix of publication, registry, news and industry
# evidence. The local conference catalogue is inspected without a network request.
_SOURCE_ORDER = ("pubmed", "trials", "journal", "policy", "arxiv", "biorxiv",
                 "europe_pmc", "fda_drugs", "openalex", "nih_brain", "fda_devices",
                 "google_news_zh", "gdelt", "conferences")
_ALTERNATIVES = ("europe_pmc", "gdelt", "openalex", "nih_brain")
_CITATIONS = {
    "pubmed": "https://pubmed.ncbi.nlm.nih.gov/",
    "trials": "https://clinicaltrials.gov/",
    "arxiv": "https://arxiv.org/",
    "biorxiv": "https://www.biorxiv.org/",
    "europe_pmc": "https://europepmc.org/",
    "openalex": "https://openalex.org/",
    "fda_drugs": "https://www.fda.gov/drugs/drug-approvals-and-databases",
    "fda_devices": "https://www.fda.gov/medical-devices/device-advice-comprehensive-regulatory-assistance/medical-device-databases",
    "gdelt": "https://www.gdeltproject.org/",
    "nih_brain": "https://braininitiative.nih.gov/news-events",
    "google_news_zh": "https://news.google.com/",
}
_FAILED = {"failed", "limited", "timeout", "partial", "blocked"}
_METRICS = ("recall", "information_gain", "false_positives", "cost")
_MAX_SOURCE_SAMPLES = 24
CAPTURE_VERSION = 2
_EXTRA_FIELDS = {
    "abstract", "arxiv_categories", "author_keywords", "category", "categories",
    "conditions", "entry_date", "first_published", "interventions", "product_description",
    "issn", "issn_linking", "issns", "journal", "journal_abbreviation", "journal_aliases",
    "keywords", "mesh_terms", "nct", "nct_id", "pmcid", "pmid", "publication_types",
    "published_online", "published_print", "source_discovered_at", "status", "trial_dates",
    "trial_events", "version",
}


def _date(value) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except (ValueError, TypeError):
        return None


def _public_url(value) -> str:
    """Store only public link metadata and drop query values that can carry credentials."""
    try:
        parts = urlsplit(validate_http_url(value, allow_private=False, resolve=False))
    except (TypeError, ValueError):
        return ""
    query = [(key, value) for key, value in parse_qsl(parts.query)
             if (key.casefold() in {"applno", "id", "pmid"} and re.fullmatch(r"[A-Za-z0-9]{1,12}", value))
             or (parts.hostname == "www.accessdata.fda.gov" and key == "event" and value == "overview.process")]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def _safe_source_url(value) -> bool:
    if allow_private_sources():
        # The source transport must enforce public redirects during unattended probes.
        return False
    try:
        validate_http_url(value, allow_private=False, resolve=False)
    except ValueError:
        return False
    return True


def _enabled(config: Config, name: str) -> bool:
    return name in registry_for(config) and config.source_opts(name).get("enabled", True) is not False


def _source_options(config: Config, name: str, *, broad: bool, start: str, end: str) -> Config:
    probe = deepcopy(config)
    opts = {**probe.source_opts(name), "enabled": True, "preview": True,
            "max_results": (_MAX_SOURCE_SAMPLES if broad else
                            min(_MAX_SOURCE_SAMPLES, int(probe.source_opts(name).get("max_results") or _MAX_SOURCE_SAMPLES))),
            "evidence_date_range": (start, end),
            "lookback_days": max(1, (date.today() - date.fromisoformat(start)).days + 1)}
    probe.sources[name] = opts
    if broad:
        probe.search = ({"query": f"PD={start}:{end}"}
                        if name in {"journal", "pubmed", "arxiv", "biorxiv"} else {})
        for option in ("filter_keywords", "query"):
            opts.pop(option, None)
        if name in {"fda_drugs", "fda_devices"}:
            opts["filter_keywords"] = []
        if name == "trials":
            opts["query"] = f"AREA[LastUpdatePostDate]RANGE[{start},{end}]"
    if name == "journal":
        probe.journals = [journal for journal in probe.journals if _safe_source_url(journal.rss)]
    if name == "policy":
        probe.policy_feeds = [url for url in probe.policy_feeds if _safe_source_url(url)]
    if name in {"europe_pmc", "openalex"} or name not in BUILTIN:
        configured_dates = compile_search(probe.search, probe.journals).date_range
        opts["paper_date_range"] = (max(start, configured_dates[0]), min(end, configured_dates[1])) if (
            configured_dates and (name in {"europe_pmc", "openalex"} or opts.get("kind") == "paper")) else (start, end)
    return probe


def _availability(item: Item) -> str:
    # Index date and public registry updates represent new information even when
    # the associated paper or trial originally appeared in a much earlier window.
    if item.kind == "paper":
        return max(item.date[:10], str(item.extra.get("source_discovered_at") or "")[:10])
    return item.date[:10]


def _safe_row(item: Item) -> dict:
    return {
        "title": item.title[:500], "url": _public_url(item.url), "summary": item.summary[:3_000],
        "authors": item.authors[:30], "source": item.source, "kind": item.kind, "date": item.date,
        "doi": normalize_doi(item.doi), "tags": item.tags[:30],
        "extra": {key: item.extra[key] for key in _EXTRA_FIELDS if key in item.extra},
    }


def _fetch(config: Config, name: str, start: str, end: str, *, broad: bool = False) -> tuple[list[dict], dict]:
    began = monotonic()
    probe = _source_options(config, name, broad=broad, start=start, end=end)
    opts = probe.source_opts(name)
    fetch = registry_for(probe).get(name)
    empty_config = ((name == "journal" and not probe.journals)
                    or (name == "policy" and not probe.policy_feeds)
                    or (name not in BUILTIN and not _safe_source_url(opts.get("url"))))
    if not fetch or empty_config:
        return [], {"status": "unavailable", "coverage": "unverified", "request_count": 0,
                    "source": name, "captured": 0, "reason": "no approved publication endpoint"}
    with capture_requests() as stats:
        try:
            items = fetch(probe)
        except Exception:
            # Upstream exceptions may contain URLs, local paths or credentials.
            return [], {"status": "failed", "coverage": "unverified", "request_count": stats.request_count,
                        "elapsed_seconds": round(monotonic() - began, 3),
                        "source": name, "captured": 0, "reason": "source adapter failed"}
        rows = [_safe_row(item) for item in items
                if item.kind == "conference" or not _date(_availability(item))
                or start <= _availability(item) <= end]
        if len(rows) > _MAX_SOURCE_SAMPLES:
            stats.sampled = stats.truncated = True
            rows = rows[:_MAX_SOURCE_SAMPLES]
        diagnostic = stats.as_dict(len(rows))
    diagnostic["source"] = name
    diagnostic["captured"] = len(rows)
    diagnostic["elapsed_seconds"] = round(monotonic() - began, 3)
    # Current feed archives usually expose their last entries only.
    if name in {"journal", "policy", "nih_brain", "google_news_zh"} or name not in BUILTIN:
        if diagnostic["status"] not in _FAILED:
            diagnostic["coverage"] = "sampled"
    elif name == "conferences":
        diagnostic["status"] = "catalogue"
    elif not diagnostic["request_count"]:
        diagnostic["status"] = "not_queried"
        diagnostic["coverage"] = "unverified"
    diagnostic["reason"] = "; ".join(diagnostic.pop("request_errors"))
    return rows, diagnostic


def _example(item: Item, status: str | None = None) -> dict:
    return {
        "ids": item.extra.get("record_ids") or list(record_ids(item)),
        "title": item.title, "url": item.url, "kind": item.kind, "date": item.date, "source": item.source,
        "available_on": _availability(item),
        "status": status or item.extra.get("search_match", "match"),
        "matched_rules": item.extra.get("matched_rules", []),
        "missing_fields": item.extra.get("missing_fields", []),
    }


def _plans(config: Config):
    return compile_search(config.search, config.journals), compile_scoped_search(config.search)


def _match(item: Item, plans, opts: dict) -> str:
    primary, scoped = plans
    plan = primary if item.kind == "paper" else scoped.get(item.kind)
    # These two adapter types support a baseline-approved local keyword filter.
    # Applying it again allows the broad feed capture to be replayed faithfully.
    if opts.get("type") in {"rss", "json", "json_api"} and opts.get("filter_keywords"):
        text = (item.title + " " + item.summary).casefold()
        matched = [word for word in opts["filter_keywords"] if word.casefold() in text]
        if not matched:
            return "miss"
        item.extra["matched_rules"] = matched
    if item.source in {"fda_drugs", "fda_devices"}:
        text = f"{item.title} {item.summary} {item.extra.get('product_description') or ''}"
        if not fda._focus_hit(text, opts.get("filter_keywords")):
            return "miss"
    if plan is None or not plan.active:
        return "match"
    result = plan.match(item)
    item.extra["matched_rules"] = [*item.extra.get("matched_rules", []), *result.evidence]
    item.extra["missing_fields"] = list(result.missing_fields)
    return result.status


def _combined_diagnostics(windows: list[dict]) -> dict:
    statuses = {row["status"] for row in windows}
    failed = statuses & (_FAILED | {"not_queried", "unavailable"})
    status = (windows[0]["status"] if len(statuses) == 1 else "partial" if failed else "ok")
    coverage = {row.get("coverage", "full") for row in windows}
    combined = {key: sum(row.get(key, 0) for row in windows)
                for key in ("captured", "request_count", "matches", "excluded", "unknown")}
    combined.update(status=status, coverage="partial" if failed else "sampled" if "sampled" in coverage else "full",
                    reason="; ".join(dict.fromkeys(row["reason"] for row in windows if row.get("reason"))),
                    truncated=any(row.get("truncated") for row in windows))
    return combined


def _publication(rows: list[dict], diagnostic: dict) -> dict:
    dates = {
        "published": sorted({row["date"][:10] for row in rows if row["kind"] not in {"trial", "conference"}
                             and _date(row["date"])}),
        "indexed": sorted({str(row["extra"]["source_discovered_at"])[:10] for row in rows
                           if row["kind"] == "paper" and _date(row["extra"].get("source_discovered_at"))}),
        "registry_updates": sorted({row["date"][:10] for row in rows if row["kind"] == "trial" and _date(row["date"])}),
        "scheduled_conferences": sorted({row["date"][:10] for row in rows
                                         if row["kind"] == "conference" and _date(row["date"])}),
    }
    observed = {}
    for row in rows:
        journal = row["extra"].get("journal")
        if journal and _date(row["date"]):
            observed.setdefault(journal, set()).add(row["date"][:10])
    return {**diagnostic, "dated_records": dates,
            "journal_publication_dates": {key: sorted(value) for key, value in sorted(observed.items())}}


def _diagnosis(publication: dict, configured: dict, examples: list[dict]) -> str:
    if configured["status"] in _FAILED:
        return "configured_search_failed"
    if publication["status"] in _FAILED:
        return "source_failed"
    if publication["status"] == "catalogue":
        return "catalogue"
    if publication["captured"] and any(row["status"] == "miss" for row in examples):
        return "published_items_filtered_by_rules"
    if publication["captured"] and not configured["captured"]:
        return "published_items_missing_from_configured_capture"
    if publication["captured"]:
        return "publication_observed"
    if publication["status"] == "empty" and publication["coverage"] == "full":
        return "no_publication_observed_in_query_scope"
    return "publication_unverified"


def _known_ids(history: Iterable[dict]) -> list[str]:
    ids = []
    for run in history:
        snapshot = run.get("snapshot") or run
        for item in (snapshot.get("records") or [])[:40]:
            identities = [value for value in item.get("ids", []) if isinstance(value, str)]
            identity = next((value for value in identities
                             if re.fullmatch(r"(?:pmid:[0-9]{1,12}|nct:NCT[0-9]{8})", value)), None)
            if not identity:
                identity = next((f"doi:{doi}" for value in identities if (doi := normalize_doi(value))), None)
            if identity and identity not in ids:
                ids.append(identity)
            if len(ids) >= 4:
                return ids
    return ids


def _recent_ids(history: Iterable[dict]) -> list[str]:
    identities = {}
    for run in history:
        snapshot = run.get("snapshot") or run
        for item in (snapshot.get("records") or [])[:120]:
            for identity in item.get("ids", []):
                if not isinstance(identity, str):
                    continue
                if identity.startswith("url:"):
                    if clean := _public_url(identity[4:]):
                        identities["url:" + clean] = None
                elif identity.startswith(("doi:", "nct:", "pmid:", "pmcid:", "arxiv:")):
                    identities[identity] = None
                if len(identities) >= 1_200:
                    return list(identities)
    return list(identities)


def _probe_known_id(identity: str) -> dict:
    prefix, value = identity.split(":", 1)
    if prefix == "nct":
        citation = f"https://clinicaltrials.gov/study/{value}"
        response = get(f"{trials.BASE}/{quote(value)}", timeout=6, retries=0, accepted_statuses=(404,))
    else:
        citation = f"https://doi.org/{quote(value, safe='/')}"
        response = get(f"https://api.crossref.org/works/{quote(value, safe='')}", timeout=6, retries=0,
                       accepted_statuses=(404,))
    status = "unavailable"
    if response is not None:
        try:
            payload = response.json()
            if response.status_code == 404:
                matched = False
            elif prefix == "nct":
                matched = value == payload["protocolSection"]["identificationModule"]["nctId"]
            else:
                matched = value == normalize_doi(payload["message"]["DOI"])
            status = "identity_confirmed" if matched else "identity_not_found"
        except (AttributeError, TypeError, KeyError, ValueError):
            status = "invalid_response"
    return {"id": identity, "citation": citation, "status": status, "relevance": "unjudged"}


def _probe_mesh(term: str) -> dict:
    citation = "https://id.nlm.nih.gov/mesh/lookup"
    response = get(f"{citation}/descriptor",
                   params={"label": term, "match": "exact", "limit": 3}, timeout=6, retries=0)
    if response is None:
        return {"term": term, "citation": citation, "status": "unavailable"}
    try:
        rows = response.json()
        if not isinstance(rows, list):
            raise ValueError("expected a descriptor list")
        for row in rows:
            if row.get("label", "").casefold() == term.casefold():
                identifier = str(row.get("resource", "")).rsplit("/", 1)[-1]
                if re.fullmatch(r"D[0-9]+", identifier):
                    return {"term": term, "citation": f"https://id.nlm.nih.gov/mesh/{identifier}.html",
                            "status": "descriptor_confirmed"}
    except (AttributeError, TypeError, ValueError):
        return {"term": term, "citation": citation, "status": "invalid_response"}
    return {"term": term, "citation": citation, "status": "descriptor_not_found"}


def _probe_pubmed_ids(identities: list[str]) -> list[dict]:
    if not identities:
        return []
    values = [identity.split(":", 1)[1] for identity in identities]
    response = get(f"{pubmed.BASE}/esearch.fcgi", params={
        "db": "pubmed", "term": " OR ".join(f"{value}[uid]" for value in values),
        "retmode": "json", "retmax": len(values),
    }, timeout=6, retries=0)
    found, issue = set(), "unavailable"
    if response is not None:
        try:
            found = set(response.json()["esearchresult"]["idlist"])
            issue = None
        except (TypeError, KeyError, ValueError):
            issue = "invalid_response"
    return [{"id": identity, "citation": f"https://pubmed.ncbi.nlm.nih.gov/{value}/",
             "status": issue or ("identity_confirmed" if value in found else "identity_not_found"),
             "relevance": "unjudged"} for identity, value in zip(identities, values)]


def _hash(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_jobs(pool, callback, values):
    jobs = [pool.submit(copy_context().run, callback, value) for value in values]
    return (job.result() for job in jobs)


def _source_plan(baseline: Config, max_sources: int, extra_sources: Iterable[str]) -> tuple[list[str], list[str]]:
    registry = registry_for(baseline)
    enabled = [name for name in dict.fromkeys((*_SOURCE_ORDER, *registry)) if _enabled(baseline, name)]
    requested = [name for name in extra_sources if name in registry]
    alternatives = [name for name in _ALTERNATIVES if name not in enabled]
    reserved = max(1, max_sources - bool(alternatives))
    order = list(dict.fromkeys((*requested, *enabled[:reserved], *alternatives, *enabled)))
    selected = order[:max_sources]
    return selected, sorted(set(enabled) - set(selected))


def capture_evidence(baseline: Config, *, days: int = 30, history: Iterable[dict] = (),
                     max_sources: int = 6, today: date | None = None,
                     extra_sources: Iterable[str] = (), check_cancel=None) -> dict:
    """Gather dated controls and current results once for a versioned trial."""
    if type(days) is not int or not 8 <= days <= 90:
        raise ValueError("Evidence lookback must be 8–90 days")
    if type(max_sources) is not int or not 1 <= max_sources <= len(_SOURCE_ORDER):
        raise ValueError("Evidence source budget is outside the supported range")
    end_day = today or date.today()
    start = (end_day - timedelta(days=days - 1)).isoformat()
    end = end_day.isoformat()
    held_start = end_day - timedelta(days=max(2, days // 3) - 1)
    window = {"start": start, "end": end, "development_end": (held_start - timedelta(days=1)).isoformat(),
              "holdout_start": held_start.isoformat()}
    source_names, skipped = _source_plan(baseline, max_sources, extra_sources)
    plans = _plans(baseline)
    check = check_cancel or (lambda: None)
    history = tuple(history)

    def capture_source(name):
        enabled = _enabled(baseline, name)
        all_broad, all_configured, examples, windows = [], [], [], {}
        counts = {"match": "matches", "miss": "excluded", "unknown": "unknown"}
        for phase, phase_start, phase_end in (("development", start, window["development_end"]),
                                             ("holdout", window["holdout_start"], end)):
            check()
            broad, publication = _fetch(baseline, name, phase_start, phase_end, broad=True)
            check()
            if enabled and name != "conferences":
                configured, actual = _fetch(baseline, name, phase_start, phase_end)
            elif enabled:
                configured, actual = broad, {**publication, "request_count": 0}
            else:
                configured, actual = [], {"status": "disabled", "request_count": 0, "captured": 0}
            actual = {**actual, "matches": 0, "excluded": 0, "unknown": 0}
            for row in configured:
                actual[counts[_match(Item(**deepcopy(row)), plans, baseline.source_opts(name))]] += 1
            windows[phase] = {"publication": publication, "configured": actual}
            for item in merge_records([Item(**deepcopy(row)) for row in (*broad[:6], *configured[:6])]):
                examples.append(_example(item, _match(item, plans, baseline.source_opts(name))))
            all_broad.extend(broad)
            all_configured.extend(configured)
        publication = _combined_diagnostics([phase["publication"] for phase in windows.values()])
        actual = _combined_diagnostics([phase["configured"] for phase in windows.values()])
        summary = {"source": name, "enabled": enabled, "publication": _publication(all_broad, publication),
                   "configured": actual, "examples": examples, "windows": windows, "citation": _CITATIONS.get(name)
                   or next((example["url"] for example in examples if example["url"]), "")
                   or _public_url(baseline.source_opts(name).get("url")),
                   "status": _diagnosis(publication, actual, examples)}
        return name, summary, {"broad": all_broad, "configured": all_configured}

    with ThreadPoolExecutor(max_workers=4) as pool:
        groups = list(_source_jobs(pool, capture_source, source_names))
        check()
        ids = _known_ids(history)
        pmids = [identity for identity in ids if identity.startswith("pmid:")]
        native = pool.submit(copy_context().run, _probe_pubmed_ids, pmids)
        known = list(_source_jobs(pool, _probe_known_id, (identity for identity in ids if not identity.startswith("pmid:"))))
        known.extend(native.result())
    check()
    citations = _corroborating_records({name: rows for name, _, rows in groups})
    source_reports = [row for _, row, _ in groups]
    known_requests = len(ids) - len(pmids) + bool(pmids)
    requests = sum(row[key].get("request_count", 0) for row in source_reports
                   for key in ("publication", "configured")) + known_requests
    snapshot = {"version": CAPTURE_VERSION, "profile": baseline.profile, "window": window, "sources": source_reports,
                "uncaptured_sources": skipped, "known_id_probes": known, "corroboration": citations,
                "budget": {"source_limit": max_sources, "sample_limit_per_source_per_window": _MAX_SOURCE_SAMPLES,
                           "planned_sources": len(source_names), "logical_requests": requests,
                           "known_id_requests": known_requests},
                "history_ids": _recent_ids(history),
                "captures": {name: rows for name, _, rows in groups}}
    snapshot["snapshot_id"] = _hash(snapshot)
    return snapshot


def public_evidence(snapshot: dict) -> dict:
    """Provide citations and match diagnostics without storing full captures in prompts."""
    return {key: deepcopy(value) for key, value in snapshot.items() if key not in {"captures", "history_ids"}}


def _corroborating_records(captures: dict) -> list[dict]:
    all_items = [Item(**deepcopy(row)) for capture in captures.values()
                 for row in (*capture["broad"], *capture["configured"])]
    related = []
    for item in merge_records(all_items):
        provenance = item.extra["provenance"]
        if len({row["source"] for row in provenance}) < 2:
            continue
        related.append({**_example(item), "checked_by": provenance, "relevance": "unjudged"})
        if len(related) >= 12:
            break
    return related


def _label_rows(labels: Iterable[dict]) -> list[dict]:
    unique = set()
    output = []
    for label in labels:
        if (not isinstance(label, dict) or type(label.get("relevant")) is not bool
                or not isinstance(label.get("ids"), (list, tuple)) or not label["ids"]
                or any(not isinstance(value, str) or not value.strip() for value in label["ids"])):
            raise ValueError("Every judgment needs record IDs and an explicit relevance value")
        ids = list(dict.fromkeys(label["ids"]))
        if unique.intersection(ids):
            raise ValueError("Record IDs appear in more than one judgment")
        unique.update(ids)
        output.append({**label, "ids": ids})
    return output


def _record_key(item: Item) -> str:
    # Publisher syndication often uses multiple URLs for identical headlines.
    if item.kind in {"news", "policy"}:
        return "coverage:" + " ".join(re.findall(r"\w+", item.title.casefold()))
    return item.extra.get("record_ids", record_ids(item))[0]


def _capture_identities(captures: dict) -> dict:
    # A removed source can change which alias is first in a merged record.
    # Resolve aliases across the shared capture before comparing configurations.
    shared = [Item(**deepcopy(row)) for rows in captures.values()
              for row in (*rows.get("broad", []), *rows.get("configured", []))]
    return {(item.kind, alias): _record_key(item) for item in merge_records(shared)
            for alias in item.extra["record_ids"]}


def _attribution(items: list[Item]) -> list[dict]:
    grouped = {}
    for item in items:
        for rule in item.extra.get("matched_rules", []):
            row = grouped.setdefault(rule, {"rule": rule, "count": 0, "examples": []})
            row["count"] += 1
            if len(row["examples"]) < 5:
                row["examples"].append(_example(item))
    return sorted(grouped.values(), key=lambda row: (-row["count"], row["rule"]))[:50]


def _replay(config: Config, captures: dict, start: str, end: str, *, identities: dict) -> tuple[dict, dict]:
    items = []
    plans = _plans(config)
    counts = {"included": 0, "filtered": 0, "unknown": 0, "undated": 0}
    for name, capture in captures.items():
        if not _enabled(config, name):
            continue
        opts = config.source_opts(name)
        for row in capture.get("configured", []):
            item = Item(**deepcopy(row))
            available = _availability(item)
            if not _date(available):
                counts["undated"] += 1
                continue
            if not start <= available <= end:
                continue
            item.extra["search_match"] = _match(item, plans, opts)
            items.append(item)
    merged = merge_records(items)
    matched = {}
    for item in merged:
        status = item.extra["search_match"]
        if status != "match":
            counts["unknown" if status == "unknown" else "filtered"] += 1
            continue
        key = _record_key(item)
        if item.kind not in {"news", "policy"}:
            key = identities.get((item.kind, key), key)
        if key in matched:
            old = matched[key]
            old.extra["record_ids"] = list(dict.fromkeys((*old.extra["record_ids"], *item.extra["record_ids"])))
            old.extra["matched_rules"] = list(dict.fromkeys((*old.extra.get("matched_rules", []),
                                                             *item.extra.get("matched_rules", []))))
        else:
            matched[key] = item
    counts["included"] = len(matched)
    return matched, counts


def _timed_labels(labels: list[dict], captures: dict, start: str, end: str) -> tuple[list[dict], int]:
    available_dates = {}
    for capture in captures.values():
        for row in (*capture.get("broad", []), *capture.get("configured", [])):
            item = Item(**row)
            when = _availability(item)
            if _date(when):
                for identity in record_ids(item):
                    dates = available_dates.setdefault(identity, set())
                    dates.add(when)
    placed, unplaced = [], 0
    for label in labels:
        explicit_date = label.get("date")
        if explicit_date is not None and not _date(explicit_date):
            raise ValueError("Judgment dates must be ISO calendar dates")
        dates = set().union(*(available_dates.get(identity, set()) for identity in label["ids"]))
        effective = min(dates) if dates else (explicit_date or "")[:10]
        if effective and start <= effective <= end:
            placed.append(label)
        elif not effective:
            unplaced += 1
    return placed, unplaced


def _relevance(items: dict, labels: list[dict]) -> dict:
    aliases = {identity: index for index, label in enumerate(labels) for identity in label["ids"]}
    matched = {}
    measured = set()
    for key, item in items.items():
        votes = {aliases[identity] for identity in item.extra["record_ids"] if identity in aliases}
        if len(votes) > 1:
            raise ValueError("One judgment is allowed per deduplicated record")
        if votes:
            index = votes.pop()
            if index in measured:
                raise ValueError("A judgment matches multiple unrelated records")
            measured.add(index)
            matched[key] = labels[index]["relevant"]
    return matched


def _new_information(item: Item, history_ids: set[str], start: str, end: str) -> bool:
    if history_ids.isdisjoint(item.extra["record_ids"]):
        return True
    return item.kind == "trial" and any(
        event.get("kind") in {"registered", "results_posted", "status_changed"}
        and start <= event.get("date", "") <= end for event in item.extra.get("trial_events", []))


def _metrics(items: dict, judged: dict, labels: list[dict], requests: int,
             history_ids: set[str], start: str, end: str) -> dict:
    positives = sum(label["relevant"] for label in labels)
    relevant = sum(judged.values())
    # Live relevance is user-judged. Known-ID corroboration or raw candidate
    # count may prove availability but never creates a relevance judgment.
    return {"recall": relevant / positives if positives else None,
            "information_gain": sum(_new_information(items[key], history_ids, start, end)
                                    for key, vote in judged.items() if vote) if positives else None,
            "false_positives": sum(not value for value in judged.values()) if labels else None,
            "cost": requests}


def _changed_sources(before: Config, after: Config) -> set[str]:
    names = set(registry_for(before)) | set(registry_for(after))
    changed = {name for name in names if _enabled(before, name) != _enabled(after, name)
               or ((_enabled(before, name) or _enabled(after, name))
                   and before.source_opts(name) != after.source_opts(name))}
    old_paper, old_scoped = _plans(before)
    new_paper, new_scoped = _plans(after)
    if (old_paper.expression, old_paper.journal_mode, old_paper.journals, old_paper.sets) != (
            new_paper.expression, new_paper.journal_mode, new_paper.journals, new_paper.sets):
        changed.update(name for name in ("pubmed", "arxiv", "biorxiv", "europe_pmc", "openalex", "journal")
                       if _enabled(before, name) or _enabled(after, name))
        if any(_enabled(config, "policy") and config.policy_feeds and (
                "paper" in (config.source_opts("policy").get("feed_kinds") or {}).values()
                or set(config.policy_feeds).intersection(journal.rss for journal in config.journals))
               for config in (before, after)):
            changed.add("policy")
        changed.update(name for name in names if name not in BUILTIN and
                       "paper" in {before.source_opts(name).get("kind"), after.source_opts(name).get("kind")}
                       and (_enabled(before, name) or _enabled(after, name)))
    if old_scoped.get("trial") != new_scoped.get("trial"):
        if _enabled(before, "trials") or _enabled(after, "trials"):
            changed.add("trials")
    for kind, known_sources in (("news", ("policy", "nih_brain", "google_news_zh", "gdelt")),
                                ("policy", ("policy",))):
        if old_scoped.get(kind) != new_scoped.get(kind):
            changed.update(name for name in known_sources if _enabled(before, name) or _enabled(after, name))
            changed.update(name for name in names if name not in BUILTIN
                           and kind in {before.source_opts(name).get("kind"), after.source_opts(name).get("kind")}
                           and (_enabled(before, name) or _enabled(after, name)))
    if before.disciplines != after.disciplines or before.global_keywords != after.global_keywords:
        changed.update(name for name in ("pubmed", "arxiv", "biorxiv", "europe_pmc", "openalex", "trials",
                                         "journal", "gdelt", "nih_brain", "google_news_zh")
                       if _enabled(before, name) or _enabled(after, name))
    if before.journals != after.journals:
        changed.add("journal")
    if before.policy_feeds != after.policy_feeds:
        changed.add("policy")
    return changed


def _sources_authorized(before: Config, after: Config) -> bool:
    if not {journal.rss for journal in after.journals if journal.rss}.issubset(
            {journal.rss for journal in before.journals if journal.rss}):
        return False
    if not set(after.policy_feeds).issubset(before.policy_feeds):
        return False
    registry = registry_for(before)
    for name, opts in after.sources.items():
        old = before.sources.get(name, {})
        if name not in registry and opts != old:
            return False
        if any(opts.get(field) != old.get(field) for field in ("url", "type", "items_path", "map")):
            return False
    return True


def _phase(snapshot: dict, phase: str) -> tuple[str, str]:
    window = snapshot["window"]
    if phase == "development":
        return window["start"], window["development_end"]
    if phase == "holdout":
        return window["holdout_start"], window["end"]
    raise ValueError("Unknown optimization evaluation phase")


def _trial_sources(snapshot: dict, baseline: Config, candidate: Config, phase: str) -> tuple[set[str], dict, list[str]]:
    changed_sources = _changed_sources(baseline, candidate)
    summaries = {row["source"]: row["windows"][phase] for row in snapshot["sources"]}
    reasons = []
    if not _sources_authorized(baseline, candidate):
        reasons.append("source_endpoint_not_preapproved")
    if not {journal.name.casefold() for journal in baseline.journals}.issubset(
            {journal.name.casefold() for journal in candidate.journals}):
        reasons.append("subscribed_journal_removed")
    if changed_sources - summaries.keys():
        reasons.append("changed_source_missing_from_frozen_capture")
    for name in changed_sources & summaries.keys():
        publication = summaries[name]["publication"]
        configured = summaries[name]["configured"]
        unusable = _FAILED | {"unavailable", "not_queried"}
        if (publication["status"] in unusable if not _enabled(baseline, name)
                else configured["status"] in unusable):
            reasons.append("changed_source_unavailable")
        limits_differ = candidate.source_opts(name).get("max_results") != baseline.source_opts(name).get("max_results")
        if (_enabled(candidate, name) and limits_differ
                and int(candidate.source_opts(name).get("max_results") or 0) > _MAX_SOURCE_SAMPLES
                and (publication.get("truncated") or publication.get("coverage") != "full")):
            reasons.append("requested_source_limit_exceeds_capture")
    return changed_sources, summaries, list(dict.fromkeys(reasons))


def _source_comparisons(snapshot, baseline, candidate, before, after, diagnostics, probes, changed, start, end, identities):
    observed = {probe["source"]: probe["candidate"] for probe in probes}
    citations = {row["source"]: row.get("citation") for row in snapshot["sources"]}
    incomplete = _FAILED | {"not_queried", "unavailable"}

    def measure(config, name, captures, diagnostic):
        summary = {key: diagnostic.get(key) for key in ("status", "coverage", "request_count", "elapsed_seconds")}
        if diagnostic["status"] in incomplete:
            return {**summary, "matched": None, "filtered": None, "unknown": None, "undated": None}
        _, counts = _replay(config, {name: captures[name]}, start, end, identities=identities)
        return {**summary, "matched": counts["included"], "filtered": counts["filtered"],
                "unknown": counts["unknown"], "undated": counts["undated"]}

    results = []
    for name, windows in diagnostics.items():
        original = windows["configured"]
        new = observed.get(name) or ({"status": "not_queried"} if name in changed else original)
        results.append({"source": name, "citation": citations[name],
                        "baseline": measure(baseline, name, before, original),
                        "candidate": measure(candidate, name, after, new)})
    return results


def evaluate_candidate(snapshot: dict, baseline: Config, candidate: Config, *, labels: Iterable[dict] = (),
                       phase: str = "development", check_cancel=None) -> dict:
    """Score a bounded native trial against the frozen baseline for the same window."""
    if (snapshot.get("version") != CAPTURE_VERSION or snapshot.get("profile") != baseline.profile
            or candidate.profile != baseline.profile):
        raise ValueError("Evidence and configurations must use the same profile and capture schema")
    start, end = _phase(snapshot, phase)
    baseline_rows = snapshot["captures"]
    candidate_rows = dict(baseline_rows)
    sources, diagnostics, reasons = _trial_sources(snapshot, baseline, candidate, phase)
    baseline_cost = {name: windows["configured"].get("request_count", 0) for name, windows in diagnostics.items()}
    candidate_cost = baseline_cost.copy()
    probes = []
    vocabulary_checks = []
    check = check_cancel or (lambda: None)

    def sample(name):
        check()
        if not _enabled(candidate, name):
            return name, [], {"status": "disabled", "request_count": 0}
        rows, diagnostic = _fetch(candidate, name, start, end)
        check()
        return name, rows, diagnostic

    if not reasons:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for name, rows, diagnostic in _source_jobs(pool, sample, sorted(sources)):
                if diagnostic["status"] in _FAILED | {"not_queried", "unavailable"}:
                    reasons.append("native_trial_incomplete")
                else:
                    candidate_rows[name] = {"configured": rows}
                candidate_cost[name] = diagnostic.get("request_count", 0)
                probes.append({"source": name, "baseline": diagnostics[name]["configured"], "candidate": diagnostic})
            new_mesh = sorted(set(candidate.all_mesh_terms()) - set(baseline.all_mesh_terms()), key=str.casefold)
            if phase == "holdout" and new_mesh:
                check()
                vocabulary_checks = list(_source_jobs(pool, _probe_mesh, new_mesh[:4]))

    combined = {**baseline_rows, **{f"trial:{name}": candidate_rows[name] for name in sources
                                    if name in candidate_rows and candidate_rows[name] is not baseline_rows[name]}}
    identities = _capture_identities(combined)
    before, before_counts = _replay(baseline, baseline_rows, start, end, identities=identities)
    # Transport or scope problems prevent a comparison. Do not show a source
    # outage as a proposed deletion or ask the user to label a fabricated loss.
    if reasons:
        after, after_counts = before, before_counts
    else:
        after, after_counts = _replay(candidate, candidate_rows, start, end, identities=identities)
    judgments, unplaced = _timed_labels(_label_rows(labels), baseline_rows, start, end)
    old_votes, new_votes = _relevance(before, judgments), _relevance(after, judgments)
    history_ids = set(snapshot.get("history_ids", []))
    before_metrics = _metrics(before, old_votes, judgments, sum(baseline_cost.values()), history_ids, start, end)
    after_metrics = _metrics(after, new_votes, judgments, sum(candidate_cost.values()), history_ids, start, end)
    new, lost = sorted(after.keys() - before.keys()), sorted(before.keys() - after.keys())
    unjudged_change = sum(key not in new_votes for key in new) + sum(key not in old_votes for key in lost)
    if not any(label["relevant"] for label in judgments):
        reasons.append("no_positive_relevance_judgment_in_window")
    if unjudged_change:
        reasons.append("native_trial_changes_need_relevance_judgments")
    if any(probe["status"] != "descriptor_confirmed" for probe in vocabulary_checks):
        reasons.append("proposed_mesh_descriptor_unverified")
    check()
    return {"phase": phase, "snapshot_id": snapshot["snapshot_id"], "window": {"start": start, "end": end},
            "metrics": after_metrics, "baseline_metrics": before_metrics,
            "delta": {key: after_metrics[key] - before_metrics[key] if after_metrics[key] is not None else None
                      for key in _METRICS},
            "eligible": not reasons, "reasons": list(dict.fromkeys(reasons)),
            "added": [_example(after[key]) for key in new], "lost": [_example(before[key]) for key in lost],
            "attribution": _attribution(list(after.values())),
            "details": {"baseline": before_counts, "candidate": after_counts, "unjudged_changes": unjudged_change,
                        "judgments": len(judgments), "undated_judgments": unplaced,
                        "added_count": len(new), "lost_count": len(lost),
                        "uncaptured_changed_sources": sorted(sources - diagnostics.keys()),
                        "native_probes": probes, "vocabulary_probes": vocabulary_checks,
                        "sources": _source_comparisons(snapshot, baseline, candidate, baseline_rows, candidate_rows,
                                                       diagnostics, probes, sources, start, end, identities),
                        "cost_basis": "native request counts against the frozen baseline"}}


def verify_candidate(snapshot: dict, baseline: Config, candidate: Config, *, labels: Iterable[dict] = (),
                     check_cancel=None) -> dict:
    """Verify native performance against the independently captured holdout window."""
    return evaluate_candidate(snapshot, baseline, candidate, labels=labels, phase="holdout", check_cancel=check_cancel)
