"""Link research coverage to canonical records and identify changes in tracked trials."""
from __future__ import annotations

from collections import defaultdict
from contextlib import closing
from difflib import SequenceMatcher
import json
import re
from urllib.parse import quote

from . import history
from .models import Item
from .records import _clean_url, normalize_doi, record_ids

_NCT = re.compile(r"\bNCT\d{8}\b", re.I)
_PUBMED = re.compile(r"\bPMID\s*[:：]?\s*(\d+)\b", re.I)
_DOI = re.compile(r"\b10\.\d{4,9}/[^\s<>\"']+", re.I)
_WORDS = re.compile(r"[^\W_]+", re.UNICODE)
_RESEARCH = {"paper", "trial"}
_COVERAGE = {"news", "policy"}


def _entry(item: Item, method: str) -> dict:
    return {"title": item.title, "url": item.url, "kind": item.kind, "method": method}


def _external_references(identifiers: set[str], by_id: dict) -> list[dict]:
    roots = {"doi": "https://doi.org/", "pmid": "https://pubmed.ncbi.nlm.nih.gov/",
             "pmcid": "https://pmc.ncbi.nlm.nih.gov/articles/", "nct": "https://clinicaltrials.gov/study/"}
    references = []
    for identifier in sorted(identifiers - by_id.keys()):
        namespace, _, value = identifier.partition(":")
        if value and namespace in roots:
            references.append({"title": identifier, "url": roots[namespace] + quote(value, safe="/:"),
                               "method": "reference"})
    return references[:4]


def _links(item: Item) -> set[str]:
    links = set()
    if doi := normalize_doi(item.doi):
        links.add(f"doi:{doi}")
    text = f"{item.title} {item.summary}"
    links.update(f"nct:{token.upper()}" for token in _NCT.findall(text))
    links.update(f"pmid:{token}" for token in _PUBMED.findall(text))
    for doi in _DOI.findall(text):
        # The exact match takes priority. A second candidate handles prose punctuation.
        links.add(f"doi:{normalize_doi(doi)}")
        links.add(f"doi:{normalize_doi(doi.rstrip('),.;:，。；）'))}")
    for url in item.extra.get("reference_urls") or []:
        if not isinstance(url, str):
            continue
        links.add("url:" + _clean_url(url))
        links.update(record_ids(Item("", url=url)))
        links.update(f"nct:{token.upper()}" for token in _NCT.findall(url))
    return links


def link_records(items: list[Item]) -> None:
    """Keep exact links distinct from similar headlines that require review."""
    sources = [item for item in items if item.kind in _RESEARCH]
    by_id = {}
    title_prefixes = defaultdict(list)
    for item in sources:
        for identifier in item.extra.get("record_ids") or record_ids(item):
            by_id.setdefault(identifier, item)
        heading = " ".join(_WORDS.findall(item.title.casefold()))
        if len(heading) >= 30:
            title_prefixes[heading[:20]].append((heading, item))
    seen = defaultdict(set)
    for coverage in items:
        if coverage.kind not in _COVERAGE:
            continue
        identifiers = _links(coverage)
        exact = {id(item): item for identifier in sorted(identifiers) if (item := by_id.get(identifier))}
        matches = [(item, "verified") for item in exact.values()]
        if not matches:
            title = " ".join(_WORDS.findall(coverage.title.casefold()))
            if len(title) >= 30:
                similar = [(SequenceMatcher(None, title, candidate).ratio(), item)
                           for candidate, item in title_prefixes.get(title[:20], [])[:40]]
                matches = [(item, "possible") for score, item in sorted(similar, key=lambda row: -row[0])[:2]
                           if score >= .92]
        related = [_entry(item, method) for item, method in matches] + _external_references(identifiers, by_id)
        if related:
            coverage.extra["related_evidence"] = related
        for item, method in matches:
            url = coverage.url or coverage.title
            if url not in seen[id(item)]:
                item.extra.setdefault("related_evidence", []).append(_entry(coverage, method))
                seen[id(item)].add(url)


def track_trial_changes(items: list[Item], profile: str) -> None:
    trials = [item for item in items if item.kind == "trial" and item.extra.get("nct")
              and (item.extra.get("trial_dates") or {}).get("last_update_posted")]
    if not trials:
        return
    history.init_db()
    with history._LOCK, closing(history._connect()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""CREATE TABLE IF NOT EXISTS trial_observations (
            profile TEXT NOT NULL, nct TEXT NOT NULL, posted TEXT NOT NULL, status TEXT NOT NULL,
            status_change TEXT, PRIMARY KEY(profile, nct)
        )""")
        for item in trials:
            nct = item.extra["nct"]
            last = item.extra["trial_dates"]["last_update_posted"]
            status = item.extra.get("status") or ""
            past = conn.execute("SELECT posted, status, status_change FROM trial_observations "
                                "WHERE profile=? AND nct=?", (profile, nct)).fetchone()
            if past and last < past[0]:
                continue
            change = None
            if past and last == past[0] and status == past[1]:
                change = json.loads(past[2]) if past[2] else None
            elif past and past[1] and status and past[1] != status:
                change = {"kind": "status_changed", "date": last, "from": past[1], "to": status}
            if change:
                events = item.extra.setdefault("trial_events", [])
                if change not in events:
                    events.append(change)
            conn.execute("INSERT OR REPLACE INTO trial_observations VALUES (?, ?, ?, ?, ?)",
                         (profile, nct, last, status or (past[1] if past else ""), json.dumps(change) if change else None))
