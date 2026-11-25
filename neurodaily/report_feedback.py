"""Bind report votes to saved search evidence and the active profile."""
from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path
import re

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from starlette.responses import JSONResponse

from . import history
from .records import record_ids

ASSET_URL = "/static/report/feedback.js"
_RUN_META = re.compile(r'<meta name="nd-report-run-id" content="([1-9][0-9]{0,17})">')
_KINDS = {"paper", "trial", "news", "policy", "funding", "drug", "device", "conference"}


def record_key(record: dict) -> str:
    kind = record.get("kind", "")
    aliases = sorted(_aliases(record))
    if not aliases or kind not in _KINDS:
        return ""
    return sha256(("\0".join([kind, *aliases])).encode("utf-8")).hexdigest()


def item_key(item) -> str:
    return record_key({"kind": item.kind, "ids": item.extra.get("record_ids") or record_ids(item)})


def _aliases(record: dict) -> list[str]:
    return list(dict.fromkeys(alias for alias in (record.get("ids") or ())
                              if isinstance(alias, str) and 0 < len(alias) <= 500
                              and all(ord(char) >= 32 for char in alias)))[:12]


def _formal_report(run_id: int, profile: str) -> dict | None:
    if not 0 < run_id <= 2**63 - 1:
        return None
    row = history.get_run(run_id)
    if not row or row["profile"] != profile or not row.get("report_path"):
        return None
    snapshot = row.get("snapshot") or {}
    if snapshot.get("mode") not in {"manual", "daily"} or not isinstance(snapshot.get("records"), list):
        return None
    task = row.get("task")
    if (task and not task.get("report_ready")) or (not task and row["status"] != "completed"):
        return None
    return row


def attach_controls(html: str, path: Path, profile: str) -> tuple[str, bool]:
    """Add local application code only when the file matches formal history."""
    meta = _RUN_META.search(html)
    if not meta or "data-report-record=" not in html or not (row := _formal_report(int(meta[1]), profile)):
        return html, False
    task_path = (row.get("task") or {}).get("report_file")
    if path.name != row["report_path"] or (task_path and Path(task_path).resolve() != path.resolve()):
        return html, False
    controls = (f'<div id="nd-report-feedback" data-run-id="{int(meta[1])}" hidden></div>'
                f'<script src="{ASSET_URL}" defer></script>')
    if "</body>" not in html:
        return html, False
    return html.replace("</body>", controls + "</body>", 1), True


class Vote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    relevant: StrictBool


def _record_date(record: dict) -> str | None:
    candidates = []
    for value in (record.get("date"), record.get("seen_at")):
        if isinstance(value, str):
            try:
                candidates.append(date.fromisoformat(value[:10]).isoformat())
            except ValueError:
                pass
    return max(candidates, default=None)


def router(optimizer):
    api = APIRouter(prefix="/api/history")

    def unavailable():
        return JSONResponse({"error": "Report evidence not found"}, status_code=404)

    @api.get("/{run_id}/feedback")
    def report_feedback(run_id: int):
        scope, config = optimizer.current()
        if not _formal_report(run_id, config.profile):
            return unavailable()
        return JSONResponse({"feedback": optimizer.store.report_feedback(scope, run_id)},
                            headers={"Cache-Control": "no-store"})

    @api.post("/{run_id}/feedback")
    def vote(run_id: int, payload: Vote, request: Request):
        origin = request.headers.get("origin")
        if origin and origin != f"{request.url.scheme}://{request.url.netloc}":
            return JSONResponse({"error": "Cross-origin feedback is blocked"}, status_code=403)
        scope, config = optimizer.current()
        row = _formal_report(run_id, config.profile)
        if not row:
            return unavailable()
        record = next((item for item in row["snapshot"]["records"]
                       if record_key(item) == payload.record_key), None)
        if record is None:
            return unavailable()
        rules = [rule for rule in (record.get("matched_rules") or []) if isinstance(rule, str)]
        optimizer.store.record_feedback(scope, _aliases(record), payload.relevant, _record_date(record),
                                        report_id=run_id, record_key=payload.record_key,
                                        title=str(record.get("title") or ""), source=str(record.get("source") or ""),
                                        journal=str(record.get("journal") or ""), rules=rules)
        return JSONResponse({"ok": True, "relevant": payload.relevant}, headers={"Cache-Control": "no-store"})

    return api
