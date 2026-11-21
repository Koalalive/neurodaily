"""openFDA source: new drug approvals (drugsfda) + device clearances (510k)."""
from __future__ import annotations

from datetime import datetime, timedelta

from .http import get, mark_sampled, parse_date_any, record_candidates, record_failure, record_query
from ..models import Item

DRUGS_URL = "https://api.fda.gov/drug/drugsfda.json"
DEVICE_URL = "https://api.fda.gov/device/510k.json"

# filter to neuro/psych relevant terms, else it floods with unrelated drugs
FOCUS_TERMS = [
    "brain", "neuro", "neuron", "psychiatr", "epilep", "seizure", "opioid",
    "addiction", "substance", "benzo", "antidep", "antipsych", "anxiol",
    "antiepileptic", "cognitive", "dementia", "alzheim", "parkinson", "multiple sclerosis",
    "migraine", "anesthesia", "analgesic", "schizophrenia", "bipolar", "depression",
    "anxiety", "insomnia", "neuromuscular", "spinal", "intracran", "gliom",
]


def _focus_hit(text: str) -> bool:
    t = text.lower()
    return any(term in t for term in FOCUS_TERMS)


def _date_range(back_days: int) -> tuple[str, str]:
    end = datetime.now()
    start = end - timedelta(days=back_days)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def _fetch_rows(url: str, search: str) -> list[dict]:
    record_query(search)
    response = get(url, params={"search": search, "limit": 100}, accepted_statuses=(404,))
    if response is None:
        return []
    try:
        data = response.json()
        if response.status_code == 404:
            error = data.get("error") or {}
            if (error.get("code") == "NOT_FOUND"
                    and str(error.get("message", "")).casefold().startswith("no matches found")):
                record_candidates(0)
                return []
            record_failure("openFDA endpoint returned HTTP 404")
            return []
        rows = data["results"]
        if not isinstance(rows, list):
            raise ValueError("invalid result list")
        total = int(data.get("meta", {}).get("results", {}).get("total", len(rows)))
    except (ValueError, KeyError, TypeError, AttributeError):
        record_failure("Invalid openFDA API response")
        return []
    record_candidates(total)
    if total > len(rows):
        mark_sampled(truncated=True)
    return rows


def fetch_drugs(config, logger=None, max_results: int = 8, lookback: int = 60) -> list[Item]:
    opts = config.source_opts("fda_drugs")
    max_results = int(opts.get("max_results", max_results))
    lookback = int(opts.get("lookback_days", lookback))
    s, e = _date_range(lookback)
    # openFDA interprets a literal "+" as %2B (HTTP 500); use space-separated TO.
    search = (f"submissions.submission_status_date:[{s} TO {e}] "
              f"AND submissions.submission_status:AP")
    rows = _fetch_rows(DRUGS_URL, search)
    items: list[Item] = []
    for r in rows:
        brand = r.get("openfda", {}).get("brand_name") or r.get("openfda", {}).get("generic_name") or []
        brand = brand if isinstance(brand, list) else [brand]
        generic = r.get("openfda", {}).get("generic_name") or []
        generic = generic if isinstance(generic, list) else [generic]
        name = ", ".join([b for b in brand if b]) or ", ".join([g for g in generic if g]) or r.get("application_number", "")
        sponsor = r.get("sponsor_name", "")
        appno = r.get("application_number", "")
        if not _focus_hit(f"{name} {generic} {sponsor}"):
            continue
        if len(items) >= max_results:
            mark_sampled(truncated=True)
            break
        sub_date = ""
        for sub in r.get("submissions", []):
            if sub.get("submission_status") == "AP":
                sub_date = sub.get("submission_status_date", "")
                break
        items.append(Item(
            title=f"{name} — {appno}",
            url=f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={appno[4:]}",
            summary=f"Applicant: {sponsor}. Generic name: {', '.join(generic)}.",
            authors=[sponsor] if sponsor else [],
            source="fda_drugs",
            kind="drug",
            date=parse_date_any(sub_date),
            doi="",
            tags=["fda", "drug"],
            extra={"application_number": appno},
        ))
    return items


def fetch_devices(config, logger=None, max_results: int = 8, lookback: int = 60) -> list[Item]:
    opts = config.source_opts("fda_devices")
    max_results = int(opts.get("max_results", max_results))
    lookback = int(opts.get("lookback_days", lookback))
    s, e = _date_range(lookback)
    rows = _fetch_rows(DEVICE_URL, f"decision_date:[{s} TO {e}]")
    items: list[Item] = []
    for r in rows:
        name = r.get("device_name", "")
        applicant = r.get("applicant", "")
        if not _focus_hit(f"{name} {applicant}"):
            continue
        if len(items) >= max_results:
            mark_sampled(truncated=True)
            break
        items.append(Item(
            title=name,
            url=f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?id={r.get('k_number','')}",
            summary=f"Applicant: {applicant}. K-number: {r.get('k_number','')}. "
                    f"Product code: {r.get('product_code','')}.",
            authors=[applicant] if applicant else [],
            source="fda_devices",
            kind="device",
            date=parse_date_any(r.get("decision_date", "")),
            doi="",
            tags=["fda", "device"],
            extra={"k_number": r.get("k_number"), "product_code": r.get("product_code"),
                   "product_description": r.get("product_description")},
        ))
    return items


def fetch(config, logger=None) -> list[Item]:
    return fetch_drugs(config) + fetch_devices(config)
