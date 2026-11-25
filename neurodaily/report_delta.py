"""Describe changes between comparable formal search reports."""
from __future__ import annotations

from datetime import datetime, timedelta

from .records import normalize_doi

_PUBLICATION_UPDATES = {"retraction", "correction", "expression-of-concern", "withdrawal"}
_INACTIVE_SOURCES = {"failed", "timeout", "limited", "disabled"}


def comparable(previous, current) -> bool:
    if not isinstance(previous, dict) or not isinstance(previous.get("records"), list):
        return False
    mode = current.get("mode")
    return (mode in {"manual", "daily"} and bool(previous.get("seen_dedup")) == bool(current.get("seen_dedup"))
            and all(previous.get(key) == current.get(key) for key in ("mode", "query_version", "windows")))


def _ids(record: dict):
    # A news story mentioning a DOI cannot stand in for the paper itself.
    kind = record.get("kind")
    family = "coverage" if kind in {"news", "policy"} else kind or ""
    return ((family, alias) for alias in record.get("ids", []) if isinstance(alias, str) and alias)


def _row(record: dict) -> dict:
    return {key: record.get(key, "") for key in ("title", "url", "source", "date", "kind")}


def _coverage(source: dict) -> str:
    status = source.get("status")
    if not source or status in _INACTIVE_SOURCES or (source.get("ok") is False and status != "partial"):
        return "unavailable"
    if source.get("coverage") != "full" or source.get("truncated") or status == "partial":
        return "incomplete"
    return "observed"


def _available(record, sources) -> bool:
    names = record.get("source_names") or [record.get("source")]
    return all(name and _coverage(sources.get(name, {})) == "observed" for name in names)


def _expired(record, current) -> bool:
    window = current.get("search_window") or {}
    end = window.get("end_at") or window.get("end")
    hours = (current.get("windows") or {}).get(record.get("kind"))
    # A paper expression with an explicit PY/PD constraint can admit older papers.
    if record.get("kind") == "paper" and (current.get("search") or {}).get("query"):
        return False
    try:
        cutoff = datetime.fromisoformat(end) - timedelta(hours=hours)
        dates = [datetime.fromisoformat(value[:10] + "T23:59:59" if len(value) == 10 else value)
                 for value in (record.get("seen_at"), record.get("date")) if value]
        return bool(dates and all((value if value.tzinfo else value.replace(tzinfo=cutoff.tzinfo)).timestamp()
                                  < cutoff.timestamp() for value in dates))
    except (TypeError, ValueError, OverflowError):
        return False


def _notices(record: dict):
    if record.get("kind") != "paper":
        return
    own_doi = next((alias[4:] for _, alias in _ids(record) if alias.startswith("doi:")), "")
    for notice in record.get("publication_updates") or []:
        if not isinstance(notice, dict) or notice.get("kind") not in _PUBLICATION_UPDATES:
            continue
        doi = normalize_doi(str(notice.get("doi") or ""))
        if doi:
            direction = notice.get("direction") or "notice"
            notice_id, target_id = (own_doi, doi) if direction == "notice_for" else (doi, own_doi)
            yield (notice_id or record.get("url", ""), notice["kind"], target_id), {
                "kind": notice["kind"], "date": str(notice.get("date") or ""),
                "notice_url": f"https://doi.org/{notice_id}" if notice_id else record.get("url", ""),
                "notice_id": notice_id, "provider": "Crossref", "direction": direction,
                "target_url": f"https://doi.org/{target_id}" if target_id else "",
            }
    # Index metadata is accepted only for the explicit publication types
    # supplied by biomedical catalogs, never the title or an LLM judgment.
    known_types = {str(value).casefold() for value in (record.get("publication_types") or [])}
    for category, direction in (("retracted publication", "retracted"), ("retraction of publication", "notice_for")):
        names = set(record.get("source_names") or [record.get("source")])
        if category in known_types and (names & {"pubmed", "europe_pmc"}):
            provider = "PubMed" if "pubmed" in names else "Europe PMC"
            yield (record.get("url", ""), "retraction", own_doi or direction), {
                                                   "kind": "retraction", "date": record.get("date", ""),
                                                   "notice_url": record.get("url", ""), "provider": provider,
                                                   "direction": direction}
            break


def compare(current: dict, previous_run: dict | None) -> dict:
    previous = previous_run["snapshot"] if previous_run else {}
    old_records = previous.get("records", [])
    new_records = current.get("records", [])
    old_by_id = {alias: row for row in old_records for alias in _ids(row)}
    known_new = {alias for row in new_records for alias in _ids(row)}
    old_health = {row["source"]: row for row in previous.get("sources", []) if row.get("source")}
    new_health = {row["source"]: row for row in current.get("sources", []) if row.get("source")}
    delta = {
        "baseline": {key: previous_run[key] for key in ("id", "started_at")} if previous_run else None,
        "added_papers": [], "trial_changes": [], "retractions": [], "publication_updates": [],
        "uncertain": [], "not_seen": [], "outside_window": 0,
        "source_limits": [{"source": name, "before": _coverage(old_health.get(name, {})),
                           "after": _coverage(new_health.get(name, {}))}
                          for name in sorted(old_health.keys() | new_health.keys())
                          if _coverage(new_health.get(name, {})) != "observed"
                          or (previous_run and _coverage(old_health.get(name, {})) != "observed")],
    }
    old_notices = {key for record in old_records for key, _ in _notices(record)}
    shown_notices = set()
    for record in new_records:
        aliases = list(_ids(record))
        old = next((old_by_id[key] for key in aliases if key in old_by_id), None)
        row = _row(record)
        if previous_run and old is None and record.get("kind") == "paper":
            delta["added_papers"].append({**row, "coverage_limited": not _available(record, old_health)})
        if old and record.get("kind") == "trial":
            before, after = old.get("trial_status"), record.get("trial_status")
            updated = record.get("trial_update")
            if (before and after and before != after and updated
                    and updated > (old.get("trial_update") or "")):
                delta["trial_changes"].append({**row, "before": before, "after": after, "date": updated})
        for key, notice in _notices(record):
            if key in old_notices or key in shown_notices:
                continue
            shown_notices.add(key)
            group = "retractions" if notice["kind"] == "retraction" else "publication_updates"
            delta[group].append({**row, **notice})

    for record in old_records:
        if any(alias in known_new for alias in _ids(record)):
            continue
        if _expired(record, current):
            delta["outside_window"] += 1
        elif current.get("seen_dedup") or not all(_available(record, sources) for sources in (old_health, new_health)):
            delta["uncertain"].append(_row(record))
        else:
            delta["not_seen"].append(_row(record))
    return delta
