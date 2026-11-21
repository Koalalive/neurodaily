"""Replay exact matching and ranking against frozen, labelled paper candidates."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import fields, replace
from importlib.resources import files
from pathlib import Path

from .config import Config, DEFAULT_CONFIG
from .digest import _mark_match, _rank
from .models import Item, tag_items
from .records import merge_records, normalize_doi
from .search import compile_search


_ITEM_FIELDS = {field.name for field in fields(Item)}
_LIST_FIELDS = {"authors", "affiliations", "corresponding", "tags"}
_TEXT_FIELDS = _ITEM_FIELDS - _LIST_FIELDS - {"extra"}
_DERIVED = {"search_match", "matched_rules", "missing_fields", "record_ids", "provenance", "related_versions"}


def load_corpus(path: str | Path | None = None) -> dict:
    resource = Path(path) if path is not None else files("neurodaily").joinpath("data", "search_quality_sample.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def _identifier(value: str) -> str:
    if isinstance(value, str):
        if doi := normalize_doi(value):
            return f"doi:{doi}"
        if match := re.fullmatch(r"pmid:([0-9]+)", value.strip(), re.I):
            return f"pmid:{match[1]}"
    raise ValueError(f"invalid paper DOI or PMID: {value!r}")


def _items(rows: list[dict]) -> list[Item]:
    if not isinstance(rows, list):
        raise ValueError("candidates must be an array")
    items = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or row.keys() - _ITEM_FIELDS:
            raise ValueError(f"candidate {index} has invalid Item fields")
        if any(not isinstance(row[key], str) for key in row.keys() & _TEXT_FIELDS):
            raise ValueError(f"candidate {index} has invalid text fields")
        if any(not isinstance(row[key], list) or any(not isinstance(word, str) for word in row[key])
               for key in row.keys() & _LIST_FIELDS):
            raise ValueError(f"candidate {index} has invalid list fields")
        extra = row.get("extra", {})
        if (not row.get("title", "").strip() or not row.get("source", "").strip()
                or row.get("kind", "paper") != "paper" or not isinstance(extra, dict)):
            raise ValueError(f"candidate {index} needs a title, source, paper kind and object metadata")
        item = Item(**deepcopy(row))
        for key in _DERIVED:
            item.extra.pop(key, None)
        items.append(item)
    return items


def _labels(rows: list[dict]) -> list[dict]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("labels must be a nonempty array")
    labels, seen = [], set()
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get("ids"), list) or not row["ids"]
                or not isinstance(row.get("relevant"), bool)):
            raise ValueError("each label needs paper ids and a true/false relevance judgment")
        aliases = list(dict.fromkeys(_identifier(value) for value in row["ids"]))
        if seen.intersection(aliases):
            raise ValueError(f"paper IDs label more than one judgment: {aliases}")
        seen.update(aliases)
        expected = row.get("expected_sources", [])
        if not isinstance(expected, list) or any(not isinstance(name, str) for name in expected):
            raise ValueError("expected_sources must be an array of source names")
        labels.append({"ids": aliases, "relevant": row["relevant"], "expected_sources": list(expected)})
    if not any(label["relevant"] for label in labels):
        raise ValueError("at least one relevant paper is required to measure recall")
    return labels


def _replay(items: list[Item], labels: list[dict], config: Config, top: int) -> dict:
    plan = compile_search(config.search, config.journals)
    items = deepcopy(items)
    for item in items:
        _mark_match(item, plan)
    merged = merge_records(tag_items(items, config))
    matched, statuses, by_id = [], {}, {}
    for index, item in enumerate(merged):
        status = item.extra.get("search_match")
        statuses[index] = status if status == "match" else _mark_match(item, plan)
        if statuses[index] == "match":
            matched.append(index)
        by_id.update((identity, index) for identity in item.extra["record_ids"])
    matched.sort(key=lambda index: _rank(merged[index], plan), reverse=True)
    ranks = {index: rank for rank, index in enumerate(matched, 1)}

    judgments, diagnostics = {}, []
    for label in labels:
        found = {by_id[identity] for identity in label["ids"] if identity in by_id}
        if len(found) > 1 or found.intersection(judgments):
            raise ValueError(f"one judgment per deduplicated paper is required: {label['ids']}")
        if not found:
            diagnostics.append({**label, "status": "missing_from_capture"})
            continue
        index = found.pop()
        judgments[index] = label["relevant"]
        item = merged[index]
        rank = ranks.get(index)
        if rank is None:
            status = "unknown_metadata" if statuses[index] == "unknown" else "filtered"
        else:
            status = "in_top_k" if rank <= top else "below_top_k"
        diagnostics.append({**label, "status": status, "rank": rank, "title": item.title,
                            "sources": sorted({row["source"] for row in item.extra["provenance"]}),
                            "missing_fields": item.extra.get("missing_fields", []) if status == "unknown_metadata" else [],
                            "matched_rules": item.extra.get("matched_rules", [])})

    leading = matched[:top]
    relevant_count = sum(label["relevant"] for label in labels)
    relevant_top = sum(judgments.get(index, False) for index in leading)
    relevant_retrieved = sum(judgments.get(index, False) for index in matched)
    return {
        "profile": config.profile,
        "query": plan.expression,
        "sets": plan.sets,
        "sort": plan.sort,
        "journal_mode": plan.journal_mode,
        "journals": list(plan.journals),
        "metrics": {
            "relevant_papers": relevant_count,
            "retrieved_papers": len(matched),
            "relevant_retrieved": relevant_retrieved,
            "top_papers": len(leading),
            "relevant_top_papers": relevant_top,
            "unjudged_top_papers": sum(index not in judgments for index in leading),
            "precision_at_k": relevant_top / top,
            "known_paper_recall": relevant_retrieved / relevant_count,
            "known_paper_recall_at_k": relevant_top / relevant_count,
        },
        "judgments": diagnostics,
        "top_results": [
            {"rank": ranks[index], "title": merged[index].title, "ids": merged[index].extra["record_ids"],
             "relevant": judgments.get(index)} for index in leading
        ],
    }


def evaluate_corpus(corpus: dict, candidate: Config | None = None, *, baseline: Config | None = None,
                    top: int = 20) -> dict:
    """Evaluate rules on identical source and date-window candidates without network access."""
    if type(top) is not int or top < 1:
        raise ValueError("top must be a positive integer")
    if (not isinstance(corpus, dict) or type(corpus.get("version")) is not int or corpus["version"] != 1
            or not isinstance(corpus.get("cases"), list) or not corpus["cases"]):
        raise ValueError("a version 1 corpus with a nonempty cases array is required")
    results, names = [], set()
    for case in corpus["cases"]:
        if not isinstance(case, dict) or not isinstance(case.get("name"), str) or not case["name"].strip():
            raise ValueError("every case needs a name")
        name = case["name"]
        if name in names:
            raise ValueError(f"duplicate case name: {name}")
        names.add(name)
        sources = case.get("sources", {})
        if not isinstance(sources, dict):
            raise ValueError(f"{name}: sources must map names to capture diagnostics")
        try:
            items = _items(case.get("candidates"))
            labels = _labels(case.get("labels"))
            if candidate is None and not isinstance(case.get("search"), dict):
                raise ValueError("a case needs search rules or an explicit candidate config")
            current = candidate if candidate is not None else replace(DEFAULT_CONFIG(), profile=name, search=case["search"])
            result = {"name": name, "source_capture": deepcopy(sources), "captured_candidates": len(items),
                      "candidate": _replay(items, labels, current, top)}
            if baseline is not None:
                result["baseline"] = _replay(items, labels, baseline, top)
                result["delta"] = {
                    key: value - result["baseline"]["metrics"][key]
                    for key, value in result["candidate"]["metrics"].items()
                }
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"{name}: {exc}") from exc
        results.append(result)
    encoded = json.dumps(corpus, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"version": 1, "corpus_sha256": hashlib.sha256(encoded).hexdigest(),
            "description": corpus.get("description", ""), "top": top, "cases": results}
