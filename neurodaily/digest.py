"""Digest orchestrator: run all enabled sources, collect Items, tag, dedupe, sort.

Used by both the CLI (standalone script) and the web app.
"""
from __future__ import annotations

import math
import logging
import os
import tempfile
import time
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from html import escape

from .config import Config, DEFAULT_CONFIG
from .models import Item, tag_items
from .records import merge_records
from .search import compile_scoped_search, compile_search
from .sources import registry_for
from . import history as hist


@dataclass
class DigestResult:
    items: list[Item]
    sections: dict[str, list[Item]]
    health: list[dict]
    generated_at: str
    config_profile: str = "neuro"
    config: object = None          # the Config used (so renderer can show prompt)
    errors: list[str] = field(default_factory=list)
    on_this_day: list = field(default_factory=list)   # 中文“历史上的今天”条目
    ai_summary: str = ""                              # AI 每日摘要（默认语言）
    ai_summaries: dict = field(default_factory=dict)  # language -> summary
    ai_summary_meta: dict = field(default_factory=dict)
    on_this_day_lang: str = "zh"
    history_id: int = 0            # id in search_history (0 = not recorded)
    skipped: bool = False          # True if this run was deduped (not executed)
    skipped_reason: str = ""
    fingerprint: str = ""
    ai_summary_refs: dict = field(default_factory=dict)
    report_base_url: str = ""
    report_revision: int = 1
    report_locale: str = "zh"
    geography: dict | None = None
    topics: dict | None = None

    def counts(self) -> dict[str, int]:
        c: dict[str, int] = {}
        for it in self.items:
            c[it.source] = c.get(it.source, 0) + 1
        return c

    def section_counts(self) -> dict[str, int]:
        return {k: len(v) for k, v in self.sections.items()}


_SECTION_BY_KIND = {
    "paper": "papers",
    "drug": "industry",
    "device": "industry",
    "trial": "trials_conferences",
    "news": "policy",
    "policy": "policy",
    "conference": "trials_conferences",
    "funding": "industry",
}

_LITERATURE_SOURCES = {"journal", "pubmed", "arxiv", "biorxiv", "europe_pmc", "openalex"}


def _literature_source(config: Config, name: str) -> bool:
    return name in _LITERATURE_SOURCES or config.source_opts(name).get("kind") == "paper"


def _preview_source(config: Config, name: str) -> bool:
    return (_literature_source(config, name) or name in {"policy", "trials", "gdelt", "nih_brain"}
            or config.source_opts(name).get("kind") in {"news", "policy", "trial"})


def _windows(config: Config, mode: str) -> tuple[dict, int]:
    win = config.windows

    def hours(key, default):
        try:
            return max(1, int(win.get(key, default)))
        except (ValueError, TypeError):
            return default

    daily = mode == "daily"
    return {
        "paper": hours("daily_paper_hours" if daily else "manual_paper_hours", 36 if daily else 240),
        "trial": hours("trials_hours", 36),
        "conference": hours("trials_hours", 36),
        "funding": hours("funding_hours", 36),
        "industry": hours("funding_hours", 36),
        "drug": hours("news_hours", 36),
        "device": hours("news_hours", 36),
        "news": hours("news_hours", 36),
        "policy": hours("news_hours", 36),
    }, hours("other_lookback_days", 7) * 24


def _candidate_config(config, windows, other, *, preview=False, fallback=False, date_range=None):
    cfg = deepcopy(config)
    for name in registry_for(cfg):
        options = cfg.sources.setdefault(name, {})
        literature = _literature_source(cfg, name)
        hours = windows["paper"] if literature else max(windows.values())
        days = math.ceil(hours / 24) + 1
        if not literature:
            days = max(days, math.ceil(other / 24))
        options["lookback_days"] = max(int(options.get("lookback_days") or 2), days, 7 if fallback else 1)
        if literature and options.get("type") in ("rss", "json", "json_api"):
            options["paper_date_range"] = date_range
        if preview:
            options["preview"] = True
            options["max_results"] = min(int(options.get("max_results") or 30), 30)
    return cfg


def _mark_match(item, plan, scoped=None) -> str:
    selected = plan if item.kind == "paper" else (scoped or {}).get(item.kind)
    if selected is None or not selected.active:
        return "match"
    matched = selected.match(item)
    item.extra.update(search_match=matched.status, matched_rules=list(matched.evidence),
                      missing_fields=list(matched.missing_fields))
    return matched.status


def _fetch_sources(config, plan, windows, other, *, scoped=None, logger=None, preview=False, progress=None):
    from .sources.http import capture_requests

    registry = registry_for(config)
    enabled = [(name, fetch) for name, fetch in registry.items()
               if config.source_opts(name).get("enabled", True) is not False
               and (not preview or _preview_source(config, name))]
    if progress:
        progress({name: {"status": "pending"} for name, _ in enabled})
    if not enabled:
        return [], []
    bounds = plan.date_range

    def fetch_one(name, fetch):
        started = time.monotonic()
        error = None
        literature = _literature_source(config, name)
        with capture_requests() as stats:
            try:
                items = [] if bounds and bounds[0] > bounds[1] and literature else list(
                    fetch(config, logger=logger))
            except Exception as exc:
                items, error = [], str(exc)
        diagnostics = stats.as_dict(len(items))
        if error is not None:
            diagnostics.update(status="failed", ok=False, error=error)
        filtered = _filter_by_windows(items, windows, other, keep_dated_papers=bool(bounds))
        matches, uncertain, excluded = [], [], []
        for item in filtered:
            status = _mark_match(item, plan, scoped)
            if status == "match":
                matches.append(item)
            elif status == "unknown":
                uncertain.append(item)
            else:
                excluded.append(item)
        if diagnostics["status"] == "ok" and not matches:
            diagnostics["status"] = "empty"
        diagnostics.update(source=name, count=len(matches), fetched=len(items),
                           candidates=diagnostics.get("candidate_count") if diagnostics.get("candidate_count") is not None else len(items),
                           unknown=len(uncertain), excluded=len(excluded), ms=int((time.monotonic() - started) * 1000),
                           lookback_days=config.source_opts(name).get("lookback_days"))
        if bounds and literature:
            diagnostics["date_range"] = list(bounds)
        if preview:
            diagnostics["examples"] = [
                {"title": it.title, "url": it.url, "kind": it.kind, "matched_rules": it.extra.get("matched_rules", []),
                 "missing_fields": it.extra.get("missing_fields", []),
                 "search_match": it.extra.get("search_match", "match")}
                for it in matches[:4] + uncertain[:2] + excluded[:2]
            ]
        return filtered, diagnostics

    items, health = [], []
    with ThreadPoolExecutor(max_workers=min(8, len(enabled))) as executor:
        futures = [executor.submit(fetch_one, name, fetch) for name, fetch in enabled]
        for future in as_completed(futures):
            found, diagnostics = future.result()
            items.extend(found)
            health.append(diagnostics)
            if progress:
                progress({diagnostics["source"]: {key: diagnostics[key] for key in
                          ("status", "count", "fetched", "ms")}})
    health.sort(key=lambda row: row["source"])
    return items, health


def preview_search(config: Config) -> dict:
    """Fetch bounded research samples without history, reports, AI or delivery."""
    plan = compile_search(config.search, config.journals)
    scoped = compile_scoped_search(config.search)
    windows, other = _windows(config, "manual")
    candidates = _candidate_config(config, windows, other, preview=True, date_range=plan.date_range)
    items, sources = _fetch_sources(candidates, plan, windows, other, scoped=scoped, preview=True)
    counts = {"match": 0, "unknown": 0, "miss": 0}
    by_kind = {}
    for item in merge_records(items):
        status = item.extra.get("search_match")
        match = "match" if status == "match" else _mark_match(item, plan, scoped)
        counts[match] += 1
        by_kind.setdefault(item.kind, dict.fromkeys(counts, 0))[match] += 1
    return {"profile": config.profile, "sources": sources, "unique_candidates": counts,
            "by_kind": by_kind}


def _rank(item: Item, plan) -> tuple:
    date_key = item.date or "0000-00-00"
    journal = (item.kind == "paper" and plan.journal_mode == "prefer"
               and plan.preferred_journal(item))
    top = item.kind == "paper" and "top-journal" in item.tags
    evidence = item.extra.get("matched_rules") or item.tags
    if plan.sort == "latest":
        return journal, date_key, item.title.casefold()
    if plan.sort == "relevance":
        return journal, len(evidence), date_key, item.title.casefold()
    if plan.sort == "journal":
        return journal, top, date_key, item.title.casefold()
    priority = 2 if top else int(item.source in ("pubmed", "biorxiv", "medrxiv"))
    return journal, priority, date_key, item.title.casefold()


def run(config: Config | None = None, logger=None, check_duplicate: bool = True,
        record: bool = True, max_age_hours: int | None = None, force: bool = False,
        mode: str = "manual", *, progress=None) -> DigestResult:
    """Run a digest. Optionally skip if an identical query ran recently (dedup),
    and record the run into search_history."""
    config = config or DEFAULT_CONFIG()
    fingerprint = hist.compute_fingerprint(config, mode=mode)
    started_at = datetime.now().isoformat()

    # Duplicate check: refuse to re-run the same query config within the window.
    if check_duplicate and not force:
        dup = hist.is_duplicate(fingerprint, max_age_hours=max_age_hours)
        if dup:
            final = DigestResult(
                items=[], sections={p: [] for p in ("papers", "industry",
                                                    "trials_conferences", "policy")},
                health=[], generated_at=datetime.now().isoformat(),
                config_profile=config.profile, config=config,
                skipped=True, skipped_reason=f"duplicate of run #{dup['id']} "
                                              f"({dup.get('started_at', '')})",
                fingerprint=fingerprint,
            )
            if record:
                final.history_id = hist.record_run(
                    fingerprint, config.profile, "skipped", started_at,
                    datetime.now().isoformat(), skipped_reason=final.skipped_reason,
                )
            return final

    plan = compile_search(config.search, config.journals)
    scoped = compile_scoped_search(config.search)
    windows, other = _windows(config, mode)
    candidates = _candidate_config(config, windows, other, date_range=plan.date_range)
    items, health = _fetch_sources(candidates, plan, windows, other, scoped=scoped, logger=logger, progress=progress)
    if (not items and health and not plan.active
            and all(row["status"] == "empty" for row in health)
            and any(row["lookback_days"] < 7 for row in health)):
        candidates = _candidate_config(config, windows, other, fallback=True)
        items, health = _fetch_sources(candidates, plan, windows, other, scoped=scoped, logger=logger, progress=progress)
    errors = [
        f'{row["source"]}: {row.get("error") or ", ".join(row.get("request_errors", [])) or row["status"]}'
        for row in health if row["status"] in ("timeout", "limited", "failed", "partial")
    ]

    deduped = [item for item in merge_records(tag_items(items, config))
               if item.extra.get("search_match") == "match" or _mark_match(item, plan, scoped) == "match"]
    deduped.sort(key=lambda item: _rank(item, plan), reverse=True)
    try:
        from .seen import filter_seen
        deduped = filter_seen(deduped, config)
    except Exception:
        logging.getLogger(__name__).exception("Optional seen deduplication failed")

    from .research_events import link_records, track_trial_changes
    from .sources import crossref

    link_records(deduped)
    try:
        track_trial_changes(deduped, config.profile)
    except Exception:
        logging.getLogger(__name__).exception("Could not record trial status changes")
    if deduped and config.source_opts("crossref").get("enabled"):
        from .sources.http import capture_requests
        started = time.monotonic()
        with capture_requests() as stats:
            enriched = crossref.enrich(deduped, config)
        health.append({"source": "crossref", "count": enriched,
                       "ms": int((time.monotonic() - started) * 1000), **stats.as_dict(enriched)})

    try:
        from .journal_metrics import for_item
        for _it in deduped:
            _m = for_item(_it, config)
            if _m:
                _it.extra["metrics"] = _m
    except Exception:
        pass

    # Build sections (uncapped — all items shown)
    sections: dict[str, list[Item]] = {
        "papers": [], "industry": [], "trials_conferences": [], "policy": [],
    }
    for it in deduped:
        sec = _SECTION_BY_KIND.get(it.kind, "papers")
        if sec in sections:
            sections[sec].append(it)

    _lang = "zh"
    try:
        _lang = (config.scheduled.get("on_this_day") or {}).get("lang", "zh")
    except Exception:
        _lang = "zh"
    try:
        from .onthisday import today_events, is_enabled as _otd_enabled
        on_this_day = today_events(lang=_lang) if _otd_enabled(config) else []
    except Exception:
        on_this_day = []

    final = DigestResult(
        items=deduped,
        sections=sections,
        health=health,
        generated_at=datetime.now().isoformat(),
        config_profile=config.profile,
        config=config,
        errors=errors,
        on_this_day=on_this_day,
        on_this_day_lang=_lang,
        fingerprint=fingerprint,
    )
    if record:
        final.history_id = hist.record_run(
            fingerprint, config.profile,
            "failed" if health and all(not row["ok"] for row in health) else "completed",
            started_at, datetime.now().isoformat(), item_count=len(deduped),
            source_counts=final.counts(),
            summary=f"{len(deduped)} items",
            snapshot=hist.search_snapshot(config, mode, health, deduped, windows),
        )
    return final


def snapshot(result: DigestResult, mode: str) -> dict:
    windows, _ = _windows(result.config, mode)
    return hist.search_snapshot(result.config, mode, result.health, result.items, windows)


def _filter_by_windows(items: list[Item], hours_by_kind: dict, other_hours: int = 7 * 24,
                       *, keep_dated_papers: bool = False) -> list[Item]:
    """Keep each kind within its own window; undated items are kept."""
    from datetime import timedelta
    now = datetime.now()
    out = []
    for it in items:
        if not it.date or (keep_dated_papers and it.kind == "paper"):
            out.append(it)
            continue
        hours = max(1, int(hours_by_kind.get(it.kind, other_hours)))
        cutoff = now - timedelta(hours=hours)
        try:
            # date-only sources: treat as end of day so a 36h window still
            # includes yesterday's news/papers instead of dropping them at 00:00.
            dtv = datetime.fromisoformat(it.date.replace("Z", "+00:00") if len(it.date) > 10
                                         else it.date + "T23:59:59")
        except Exception:
            out.append(it)
            continue
        if dtv.tzinfo is not None:
            cutoff = cutoff.astimezone()
        if dtv >= cutoff or _within_window(it.extra.get("source_discovered_at"), cutoff):
            out.append(it)
    return out


def _within_window(value, cutoff: datetime) -> bool:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00") if len(value) > 10
                                    else value + "T23:59:59")
    except (AttributeError, TypeError, ValueError):
        return False
    return dt.timestamp() >= cutoff.timestamp()


def _filter_papers_by_window(items: list[Item], hours: int) -> list[Item]:
    """Backward-compatible helper: filter papers only, keep every other kind."""
    return _filter_by_windows(items, {"paper": hours}, other_hours=10 ** 6)


def index_saved_report(result: DigestResult) -> None:
    if result.skipped:
        return
    try:
        from .archive_search import index_report
        index_report(result)
    except Exception:
        logging.getLogger(__name__).exception("Could not index the saved report")


def save_report(result: DigestResult, output_path: str) -> str:
    """Persist rendered HTML. Returns path."""
    from .render import render_html
    # A deduplicated (skipped) run has no content; don't overwrite an existing report.
    if result.skipped:
        return output_path
    html = render_html(result)
    if result.report_base_url:
        html = html.replace('<meta name="nd-base" content="">',
                            f'<meta name="nd-base" content="{escape(result.report_base_url, quote=True)}">', 1)
    outdir = os.path.dirname(output_path) or "."
    os.makedirs(outdir, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=outdir, delete=False) as f:
        temp_path = f.name
        try:
            f.write(html)
            f.close()
            os.replace(temp_path, output_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    # attach the (relative) report path to the history record for re-opening
    if result.history_id:
        rel = os.path.basename(output_path)
        hist.set_report_path(result.history_id, rel)
    stem, _ = os.path.splitext(output_path)
    formats = []
    try:
        formats = (getattr(result, "config", None).output or {}).get("extra_formats") or []
    except Exception:
        formats = []
    try:
        if "json" in formats:
            from .exporters import write_json
            write_json(result, stem + ".json")
        if "bibtex" in formats:
            from .exporters import write_bibtex
            write_bibtex(result, stem + ".bib")
    except Exception:
        pass
    _write_static_history(outdir)
    keep = 60
    try:
        keep = int((getattr(result, "config", None).output or {}).get("keep_reports", 60))
    except Exception:
        pass
    _prune_reports(outdir, keep)
    return output_path


def _prune_reports(outdir: str, keep: int = 60) -> None:
    """Keep the newest `keep` reports plus any still referenced by history."""
    import glob
    try:
        referenced = {os.path.basename(r.get("report_path") or "")
                      for r in hist.list_runs(limit=5000)}
    except Exception:
        referenced = set()
    files = sorted(glob.glob(os.path.join(outdir, "neurodaily_*.html")),
                   key=os.path.getmtime, reverse=True)
    for f in files[max(1, keep):]:
        if os.path.basename(f) in referenced:
            continue
        try:
            os.remove(f)
        except Exception:
            pass


def _write_static_history(outdir: str) -> None:
    """Write output/history.html so the report is browsable without the web app
    (e.g. when the report is opened directly from disk via file://)."""
    try:
        page = hist.render_history_page()
        with open(os.path.join(outdir, "history.html"), "w", encoding="utf-8") as f:
            f.write(page)
    except Exception:
        pass


def render_html_for(result: DigestResult) -> str:
    from .render import render_html
    return render_html(result, getattr(result, "config", None))
