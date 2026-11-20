"""Digest orchestrator: run all enabled sources, collect Items, tag, dedupe, sort.

Used by both the CLI (standalone script) and the web app.
"""
from __future__ import annotations

import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime

from .config import Config, DEFAULT_CONFIG
from .models import Item, tag_items
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
    ai_summary: str = ""                              # AI 每日摘要（可选）
    ai_summary_meta: dict = field(default_factory=dict)
    on_this_day_lang: str = "zh"
    history_id: int = 0            # id in search_history (0 = not recorded)
    skipped: bool = False          # True if this run was deduped (not executed)
    skipped_reason: str = ""
    fingerprint: str = ""

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


def run(config: Config | None = None, logger=None, check_duplicate: bool = True,
        record: bool = True, max_age_hours: int | None = None, force: bool = False,
        mode: str = "manual") -> DigestResult:
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

    errors: list[str] = []
    all_items: list[Item] = []
    health: list[dict] = []

    win = config.windows or {}

    def _win(key: str, default: int) -> int:
        try:
            return max(1, int(win.get(key, default)))
        except (TypeError, ValueError):
            return default

    hours_by_kind = {
        "paper": _win("daily_paper_hours" if mode == "daily" else "manual_paper_hours",
                      36 if mode == "daily" else 168),
        "trial": _win("trials_hours", 36),
        "conference": _win("trials_hours", 36),
        "funding": _win("funding_hours", 36),
        "industry": _win("funding_hours", 36),
        "drug": _win("news_hours", 36),
        "device": _win("news_hours", 36),
        "news": _win("news_hours", 36),
        "policy": _win("news_hours", 36),
    }
    other_hours = _win("other_lookback_days", 7) * 24
    needed_days = max(1, math.ceil(max(hours_by_kind.values()) / 24) + 1)
    import copy as _copy
    _orig_sources = _copy.deepcopy(config.sources)
    for _n, _o in list(config.sources.items()):
        if isinstance(_o, dict) and _o.get("enabled", True) is not False:
            _o["lookback_days"] = max(int(_o.get("lookback_days", 2) or 2), needed_days)

    registry = registry_for(config)
    enabled = [(n, f) for n, f in registry.items()
               if config.source_opts(n).get("enabled", True) is not False]

    def _fetch(name: str, fn):
        t0 = time.time()
        try:
            got = fn(config, logger=logger)
            return name, list(got), None, int((time.time() - t0) * 1000)
        except Exception as e:  # noqa: BLE001
            return name, [], str(e), int((time.time() - t0) * 1000)

    def _fetch_all_sources():
        items: list[Item] = []
        heal: list[dict] = []
        errs: list[str] = []
        if not enabled:
            return items, heal, errs
        with ThreadPoolExecutor(max_workers=min(8, len(enabled))) as ex:
            futures = [ex.submit(_fetch, n, f) for n, f in enabled]
            for fut in as_completed(futures):
                name, got, err, ms = fut.result()
                if err:
                    errs.append(f"{name}: {err}")
                    heal.append({"source": name, "ok": False, "count": 0,
                                 "ms": ms, "error": err})
                else:
                    heal.append({"source": name, "ok": True, "count": len(got), "ms": ms})
                    items.extend(got)
        heal.sort(key=lambda h: h["source"])
        return items, heal, errs

    all_items, health, errors = _fetch_all_sources()

    if not all_items and enabled:
        import copy
        original_sources = copy.deepcopy(config.sources)
        try:
            for name, opts in list(config.sources.items()):
                if isinstance(opts, dict):
                    cur = int(opts.get("lookback_days", 2) or 2)
                    opts["lookback_days"] = max(cur, 7)
            all_items, health, errors = _fetch_all_sources()
        finally:
            config.sources = original_sources
        if not all_items:
            errors.append("本次未抓取到新条目（可能是上游当日无更新或网络限流）；"
                          "可将各源 lookback_days 调大后重试。")


    config.sources = _orig_sources

    # Tag with discipline/keyword focus
    all_items = tag_items(all_items, config)

    # Dedupe by (source, title-lower) / (url)
    seen: set[str] = set()
    deduped: list[Item] = []
    for it in all_items:
        key = it.url or f"{it.source}:{it.title.lower()}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)

    # Sort: top-journal papers first, then peer-reviewed lit (pubmed/biorxiv),
    # then preprints (arxiv). With reverse=True, higher priority sorts first.
    def _sort_key(it: Item) -> tuple[int, str]:
        if it.kind == "paper" and "top-journal" in it.tags:
            priority = 2
        elif it.source in ("pubmed", "biorxiv", "medrxiv"):
            priority = 1
        else:
            priority = 0
        return (priority, it.date or "0000-00-00")

    deduped = _filter_by_windows(deduped, hours_by_kind, other_hours)
    deduped.sort(key=_sort_key, reverse=True)

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
            fingerprint, config.profile, "completed", started_at,
            datetime.now().isoformat(), item_count=len(deduped),
            source_counts=final.counts(),
            summary=f"{len(deduped)} items",
        )
    return final


def _filter_by_windows(items: list[Item], hours_by_kind: dict, other_hours: int = 7 * 24) -> list[Item]:
    """Keep each kind within its own window; undated items are kept."""
    from datetime import timedelta
    now = datetime.now()
    out = []
    for it in items:
        if not it.date:
            out.append(it)
            continue
        hours = max(1, int(hours_by_kind.get(it.kind, other_hours)))
        cutoff = now - timedelta(hours=hours)
        try:
            # date-only sources: treat as end of day so a 36h window still
            # includes yesterday's news/papers instead of dropping them at 00:00.
            dtv = datetime.fromisoformat(it.date if len(it.date) > 10 else it.date + "T23:59:59")
        except Exception:
            out.append(it)
            continue
        if dtv.tzinfo is not None:
            cutoff = cutoff.astimezone()
        if dtv < cutoff:
            continue
        out.append(it)
    return out


def _filter_papers_by_window(items: list[Item], hours: int) -> list[Item]:
    """Backward-compatible helper: filter papers only, keep every other kind."""
    return _filter_by_windows(items, {"paper": hours}, other_hours=10 ** 6)


def save_report(result: DigestResult, output_path: str) -> str:
    """Persist rendered HTML. Returns path."""
    from .render import render_html
    # A deduplicated (skipped) run has no content; don't overwrite an existing report.
    if result.skipped:
        return output_path
    html = render_html(result)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
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
    _write_static_history(os.path.dirname(output_path))
    keep = 60
    try:
        keep = int((getattr(result, "config", None).output or {}).get("keep_reports", 60))
    except Exception:
        pass
    _prune_reports(os.path.dirname(output_path), keep)
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
