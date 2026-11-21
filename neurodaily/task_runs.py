"""Durable state shared by manual and scheduled desktop searches."""
from __future__ import annotations

import errno
import json
import os
from contextlib import closing
from datetime import datetime
from pathlib import Path

from . import delivery_receipts, history
from .config import Config
from .digest import DigestResult
from .models import Item
from .profile_exchange import export_profile


def acquire():
    """Hold through delivery. The OS releases the lock if a sidecar exits."""
    path = Path(history.db_path()).with_suffix(".run.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.open("a+b")
    try:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b"\0")
            lock.flush()
        lock.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        lock.close()
        if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
            return None
        raise
    return lock


def begin(config: Config, mode: str, due: datetime | None) -> dict:
    task = {"profile": config.profile, "mode": mode, "status": "running", "phase": "search",
            "started_at": datetime.now().isoformat(), "scheduled_for": due.isoformat() if due else None,
            "finished_at": None, "sources": {}, "stages": {}, "report_ready": False}
    stage(task, "search", "running")
    history.init_db()
    with history._LOCK, closing(history._connect()) as conn, conn:
        cur = conn.execute("INSERT INTO search_history (fingerprint, profile, started_at, status, task) "
                           "VALUES (?, ?, ?, ?, ?)", (history.compute_fingerprint(config, mode),
                           config.profile, task["started_at"], task["status"], _json(task)))
        task["id"] = cur.lastrowid
        conn.execute("UPDATE search_history SET task=? WHERE id=?", (_json(task), task["id"]))
    return task


def stage(task: dict, name: str, status: str, error: str = "") -> None:
    task["phase"] = name
    task["stages"][name] = {**task["stages"].get(name, {}),
                           "status": status, "updated_at": datetime.now().isoformat()}
    if error:
        task["stages"][name]["error"] = error


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False)


def _checkpoint(result: DigestResult) -> str:
    positions = {id(item): index for index, item in enumerate(result.items)}
    return _json({
        "items": [item.to_dict() for item in result.items],
        "sections": {key: [positions[id(item)] for item in items] for key, items in result.sections.items()},
        "health": result.health, "generated_at": result.generated_at,
        "config_profile": result.config_profile, "config": export_profile(result.config)["config"],
        "on_this_day": result.on_this_day, "on_this_day_lang": result.on_this_day_lang,
        "ai_summary": result.ai_summary, "ai_summary_meta": result.ai_summary_meta,
        "ai_summary_refs": result.ai_summary_refs,
        "report_locale": result.report_locale,
    })


def load_result(run_id: int) -> DigestResult | None:
    history.init_db()
    with history._LOCK, closing(history._connect()) as conn:
        row = conn.execute("SELECT checkpoint FROM search_history WHERE id=?", (run_id,)).fetchone()
    if not row or not row[0]:
        return None
    data = json.loads(row[0])
    items = [Item(**item) for item in data["items"]]
    data["items"] = items
    data["sections"] = {key: [items[index] for index in group] for key, group in data["sections"].items()}
    data["config"] = Config.from_dict(data["config"])
    return DigestResult(**data, history_id=run_id)


def _write(conn, task: dict) -> None:
    conn.execute("UPDATE search_history SET task=?, status=?, finished_at=?, skipped_reason=? WHERE id=?",
                 (_json(task), task["status"], task["finished_at"],
                  task.get("error", "") if task["status"] == "skipped" else "", task["id"]))
    if task["scheduled_for"] and task["finished_at"] and task["status"] != "interrupted":
        conn.execute("INSERT INTO desktop_schedule_runs VALUES (?, ?, ?, ?, ?) "
                     "ON CONFLICT(profile, due) DO UPDATE SET status=excluded.status, "
                     "finished_at=excluded.finished_at, error=excluded.error",
                     (task["profile"], task["scheduled_for"], task["status"],
                      task["finished_at"], task.get("error")))


def save(task: dict, *, result: DigestResult | None = None, snapshot: dict | None = None) -> None:
    checkpoint = _checkpoint(result) if result is not None and task["report_ready"] else None
    with history._LOCK, closing(history._connect()) as conn, conn:
        _write(conn, task)
        if result is not None:
            conn.execute("UPDATE search_history SET item_count=?, source_counts=?, "
                         "report_path=COALESCE(?, report_path), checkpoint=COALESCE(?, checkpoint), "
                         "snapshot=COALESCE(?, snapshot) WHERE id=?",
                         (len(result.items), _json(result.counts()),
                          Path(task["report_file"]).name if task["report_ready"] else None, checkpoint,
                          _json(snapshot) if snapshot is not None else None, task["id"]))


def finish(task: dict, status: str, error: str = "") -> None:
    if error:
        task["error"] = error
    task.update(status=status, finished_at=datetime.now().isoformat())
    with history._LOCK, closing(history._connect()) as conn, conn:
        if task["stages"].get("delivery", {}).get("status") == "failed":
            delivery_receipts.close_interrupted(conn, str(task["id"]))
        _write(conn, task)


def recover() -> None:
    """Call while holding the lock, so active work in another process is untouched."""
    history.init_db()
    with history._LOCK, closing(history._connect()) as conn, conn:
        rows = conn.execute("SELECT task FROM search_history WHERE status='running' AND task IS NOT NULL")
        for row in rows.fetchall():
            task = json.loads(row[0])
            ready = task["report_ready"] and Path(task["report_file"]).is_file()
            message = "上次退出时任务中断。"
            stage(task, task["phase"], "interrupted", message)
            task.update(status="completed" if ready else "interrupted", report_ready=ready,
                        finished_at=datetime.now().isoformat(), error=message)
            delivery_receipts.close_interrupted(conn, str(task["id"]))
            _write(conn, task)


def latest(*, profile: str | None = None, ready: bool = False) -> dict | None:
    history.init_db()
    with history._LOCK, closing(history._connect()) as conn:
        if ready:
            rows = conn.execute("SELECT task FROM search_history WHERE task IS NOT NULL AND profile=? "
                                "AND checkpoint IS NOT NULL ORDER BY id DESC", (profile,))
            for row in rows:
                task = json.loads(row[0])
                if task["report_ready"] and Path(task["report_file"]).is_file():
                    return task
            return None
        row = conn.execute("SELECT task FROM search_history WHERE task IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
    return json.loads(row[0]) if row else None


def reports_since(after: int) -> list[dict]:
    history.init_db()
    with history._LOCK, closing(history._connect()) as conn:
        rows = conn.execute("SELECT task FROM search_history WHERE id>? AND checkpoint IS NOT NULL "
                            "AND task IS NOT NULL ORDER BY id LIMIT 100", (after,)).fetchall()
    return [{key: task[key] for key in ("id", "status", "report_ready")}
            for row in rows if (task := json.loads(row[0]))["report_ready"]]
