"""Check the draft's search rules against adapter capabilities and local evidence."""
from __future__ import annotations

from .models import Item
from .search import Exclude, Group, Near, SearchPlan, Term, compile_scoped_search, compile_search
from .sources import registry_for

_COMMON = frozenset({"TI", "AB", "TIAB", "TS", "PD", "PY"})
_LITERATURE = frozenset({"pubmed", "europe_pmc", "openalex", "arxiv", "biorxiv", "journal"})
_FIELDS = {
    **{source: {"AU", "AK", "SO", "ISSN", "MH", "DT"} for source in ("pubmed", "europe_pmc", "openalex")},
    "arxiv": {"AU", "CAT"}, "biorxiv": {"AU", "CAT"}, "journal": {"SO", "ISSN", "AU"}, "trials": {"AK", "AU"},
}


def _terms(node):
    if isinstance(node, Group):
        yield from _terms(node.left)
        yield from _terms(node.right)
    elif isinstance(node, Exclude):
        yield from _terms(node.child)
    elif isinstance(node, Near):
        yield node.left
        yield node.right
    elif isinstance(node, Term):
        yield node


def _sources(config, plans):
    for name in sorted(registry_for(config)):
        options = config.source_opts(name)
        if not options.get("enabled", True):
            continue
        kinds = {options.get("kind")} if options.get("kind") else set()
        if name in _LITERATURE:
            kinds.add("paper")
        elif name == "trials":
            kinds.add("trial")
        elif name == "policy":
            kinds.update({"news", "policy"})
        elif name in {"gdelt", "google_news_zh", "nih_brain"}:
            kinds.add("news")
        for kind in sorted(kinds & plans.keys()):
            plan = plans[kind]
            fields = {term.field for term in _terms(plan.root)}
            if plan.journal_mode == "only":
                fields.add("SO")
            missing = fields - _COMMON - _FIELDS.get(name, set())
            hint = plan.remote_query(name)
            yield {"source": name, "kind": kind, "fields": sorted(fields), "metadata_gaps": sorted(missing),
                   "remote_filter": bool(hint), "query_preview": hint}


def _historical_records(profile):
    from .history import get_run, list_runs

    seen = set()
    for entry in list_runs(limit=6, profile=profile):
        run = get_run(entry["id"]) or {}
        for row in (run.get("snapshot") or {}).get("records", []):
            ids = set(row.get("ids", []))
            if not ids or ids & seen:
                continue
            seen.update(ids)
            yield row


def lint_config(config, records=None):
    """Run on the configured profile and a bounded local sample, with no remote calls."""
    paper = compile_search(config.search, config.journals)
    plans: dict[str, SearchPlan] = {"paper": paper, **compile_scoped_search(config.search)}
    plans = {kind: plan for kind, plan in plans.items() if plan.active}
    if not plans:
        return {"sources": [], "known_records": {"matched": 0, "missed": 0, "unknown": 0, "examples": []}}
    checked = {"matched": 0, "missed": 0, "unknown": 0, "examples": []}
    sample = _historical_records(config.profile) if records is None else records
    for row in sample:
        kind = row.get("kind", "paper")
        if kind not in plans:
            continue
        item = Item(title=row.get("title") or "", date=row.get("date") or "",
                    kind=kind, source=row.get("source") or "unknown",
                    extra={key: row[key] for key in ("journal", "publication_types", "issns") if key in row})
        result = plans[kind].match(item)
        status = {"match": "matched", "miss": "missed", "unknown": "unknown"}[result.status]
        checked[status] += 1
        if status != "matched" and len(checked["examples"]) < 10:
            checked["examples"].append({"title": item.title, "status": status,
                                        "missing_fields": list(result.missing_fields)})
        if sum(checked[key] for key in ("matched", "missed", "unknown")) >= 40:
            break
    return {"sources": list(_sources(config, plans)), "known_records": checked}
