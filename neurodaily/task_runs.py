"""Durable state shared by manual and scheduled desktop searches."""
from __future__ import annotations

import errno
import json
import os
from contextlib import closing
from datetime import datetime
from pathlib import Path

from . import delivery_receipts, history
from .config import Config, revision_for
from .digest import DigestResult
from .models import Item
from .profile_exchange import export_profile


class Cancelled(Exception):
    pass


class ResumeConflict(ValueError):
    pass


def _workflow_tables(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS search_task_controls ("
                 "run_id INTEGER PRIMARY KEY REFERENCES search_history(id) ON DELETE CASCADE)")
    conn.execute("CREATE TABLE IF NOT EXISTS search_task_sources ("
                 "run_id INTEGER REFERENCES search_history(id) ON DELETE CASCADE, "
                 "pass TEXT NOT NULL, source TEXT NOT NULL, payload TEXT NOT NULL, "
                 "PRIMARY KEY (run_id, pass, source))")


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


def begin(config: Config, mode: str, due: datetime | None, *, force: bool = False,
          hours: int | None = None, profile_revision: str | None = None) -> dict:
    start = datetime.now().astimezone()
    task = {"profile": config.profile, "mode": mode, "status": "running", "phase": "search",
            "started_at": start.replace(tzinfo=None).isoformat(),
            "retrieval_anchor": start.isoformat(), "scheduled_for": due.isoformat() if due else None,
            "finished_at": None, "sources": {}, "stages": {}, "report_ready": False,
            "workflow": 1, "force": force, "hours": hours,
            "profile_revision": profile_revision or revision_for(config)}
    stage(task, "search", "running")
    history.init_db()
    with history._LOCK, closing(history._connect()) as conn, conn:
        _workflow_tables(conn)
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
    else:
        task["stages"][name].pop("error", None)


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False)


def _checkpoint(result: DigestResult) -> str:
    positions = {id(item): index for index, item in enumerate(result.items)}
    return _json({
        "items": [item.to_dict() for item in result.items],
        "sections": {key: [positions[id(item)] for item in items] for key, items in result.sections.items()},
        "health": result.health, "generated_at": result.generated_at,
        "config_profile": result.config_profile, "config": export_profile(result.config)["config"],
        "errors": result.errors, "fingerprint": result.fingerprint,
        "on_this_day": result.on_this_day, "on_this_day_lang": result.on_this_day_lang,
        "ai_summary": result.ai_summary, "ai_summaries": result.ai_summaries,
        "ai_summary_meta": result.ai_summary_meta,
        "ai_summary_refs": result.ai_summary_refs,
        "report_locale": result.report_locale,
        "geography": result.geography,
        "topics": result.topics,
        "search_window": result.search_window,
        "delta": result.delta, "profile_revision": result.profile_revision,
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
    if task["scheduled_for"] and task["finished_at"] and task["status"] not in {"interrupted", "superseded"}:
        conn.execute("INSERT INTO desktop_schedule_runs VALUES (?, ?, ?, ?, ?) "
                     "ON CONFLICT(profile, due) DO UPDATE SET status=excluded.status, "
                     "finished_at=excluded.finished_at, error=excluded.error",
                     (task["profile"], task["scheduled_for"], task["status"],
                      task["finished_at"], task.get("error")))


def save(task: dict, *, result: DigestResult | None = None, snapshot: dict | None = None) -> None:
    checkpoint = _checkpoint(result) if result is not None else None
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
        if status == "cancelled" or task["stages"].get("delivery", {}).get("status") == "failed":
            delivery_receipts.close_interrupted(conn, str(task["id"]))
        _write(conn, task)
        _workflow_tables(conn)
        if status != "interrupted":
            _clear_search_work(conn, task["id"])


def _clear_search_work(conn, run_id: int) -> None:
    conn.execute("DELETE FROM search_task_sources WHERE run_id=?", (run_id,))
    conn.execute("DELETE FROM search_task_controls WHERE run_id=?", (run_id,))


def recover() -> None:
    """Call while holding the lock, so active work in another process is untouched."""
    history.init_db()
    with history._LOCK, closing(history._connect()) as conn, conn:
        _workflow_tables(conn)
        rows = conn.execute("SELECT task FROM search_history WHERE status='running' AND task IS NOT NULL")
        for row in rows.fetchall():
            task = json.loads(row[0])
            ready = task["report_ready"] and Path(task["report_file"]).is_file()
            message = "上次退出时任务中断。"
            if task.get("workflow"):
                cancelled = _cancel_requested(conn, task["id"])
                status = "cancelled" if cancelled else "interrupted"
                if cancelled:
                    message = "检索已停止。"
                    _clear_search_work(conn, task["id"])
                    delivery_receipts.close_interrupted(conn, str(task["id"]))
                else:
                    delivery_receipts.recover_for_resume(conn, str(task["id"]))
            else:
                status = "completed" if ready else "interrupted"
                delivery_receipts.close_interrupted(conn, str(task["id"]))
            if task["stages"].get(task["phase"], {}).get("status") == "running":
                stage(task, task["phase"], status if task.get("workflow") else "interrupted", message)
            task.update(status=status, report_ready=ready, finished_at=datetime.now().isoformat(), error=message)
            _write(conn, task)


def resume(config: Config, mode: str, *, run_id: int | None = None,
           due: datetime | None = None) -> dict | None:
    """Claim an interrupted run while holding the global run guard."""
    history.init_db()
    due_iso = due.isoformat() if due else None
    fingerprint = history.compute_fingerprint(config, mode)
    with history._LOCK, closing(history._connect()) as conn, conn:
        where = " AND id=?" if run_id is not None else ""
        values = (config.profile, run_id) if run_id is not None else (config.profile,)
        rows = conn.execute("SELECT task, fingerprint FROM search_history WHERE status='interrupted' "
                            f"AND profile=? AND task IS NOT NULL{where} ORDER BY id DESC", values)
        for row in rows:
            task = json.loads(row["task"])
            if (not task.get("workflow") or task["mode"] != mode or task["scheduled_for"] != due_iso):
                continue
            if row["fingerprint"] != fingerprint:
                if run_id is not None or due is None:
                    raise ResumeConflict("检索配置已更改，请恢复原配置后继续此任务。")
                # Closing this attempt leaves the original schedule slot unclaimed.
                task.update(status="superseded", error="检索配置已更改。此定时时段将按新配置重新执行。")
                _write(conn, task)
                _clear_search_work(conn, task["id"])
                delivery_receipts.close_interrupted(conn, str(task["id"]))
                return None
            task.pop("error", None)
            task.update(status="running", finished_at=None)
            _write(conn, task)
            return task
    return None


def _cancel_requested(conn, run_id: int) -> bool:
    return conn.execute("SELECT 1 FROM search_task_controls WHERE run_id=?", (run_id,)).fetchone() is not None


def request_cancel(run_id: int) -> bool:
    history.init_db()
    with history._LOCK, closing(history._connect()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        _workflow_tables(conn)
        row = conn.execute("SELECT task FROM search_history WHERE id=? AND status='running'", (run_id,)).fetchone()
        if row is None or not row["task"] or not json.loads(row["task"]).get("workflow"):
            return False
        conn.execute("INSERT OR IGNORE INTO search_task_controls VALUES (?)", (run_id,))
        return True


def check_cancelled(run_id: int) -> None:
    with history._LOCK, closing(history._connect()) as conn:
        if _cancel_requested(conn, run_id):
            raise Cancelled("检索已停止。")


def save_source(run_id: int, pass_name: str, source: str, items: list[Item], diagnostics: dict) -> None:
    payload = _json({"items": [item.to_dict() for item in items], "diagnostics": diagnostics})
    with history._LOCK, closing(history._connect()) as conn, conn:
        conn.execute("INSERT OR REPLACE INTO search_task_sources VALUES (?, ?, ?, ?)",
                     (run_id, pass_name, source, payload))


def load_sources(run_id: int) -> dict:
    with history._LOCK, closing(history._connect()) as conn:
        rows = conn.execute("SELECT pass, source, payload FROM search_task_sources WHERE run_id=?", (run_id,))
        checkpoints = {}
        for row in rows:
            data = json.loads(row["payload"])
            checkpoints.setdefault(row["pass"], {})[row["source"]] = (
                [Item(**item) for item in data["items"]], data["diagnostics"])
    return checkpoints


def latest(*, profile: str | None = None, ready: bool = False) -> dict | None:
    history.init_db()
    with history._LOCK, closing(history._connect()) as conn:
        if ready:
            rows = conn.execute("SELECT task FROM search_history WHERE task IS NOT NULL AND profile=? "
                                "AND checkpoint IS NOT NULL AND report_path IS NOT NULL ORDER BY id DESC", (profile,))
            for row in rows:
                task = json.loads(row[0])
                if task["report_ready"] and Path(task["report_file"]).is_file():
                    return task
            return None
        condition = " AND profile=?" if profile is not None else ""
        args = (profile,) if profile is not None else ()
        row = conn.execute("SELECT task FROM search_history WHERE status='running' AND task IS NOT NULL "
                           f"{condition} ORDER BY id DESC LIMIT 1", args).fetchone()
        if row is None:
            row = conn.execute("SELECT task FROM search_history WHERE task IS NOT NULL "
                               f"{condition} ORDER BY id DESC LIMIT 1", args).fetchone()
    return json.loads(row[0]) if row else None


def reports_since(after: int, *, profile: str | None = None) -> list[dict]:
    history.init_db()
    with history._LOCK, closing(history._connect()) as conn:
        condition = " AND profile=?" if profile is not None else ""
        args = (after, profile) if profile is not None else (after,)
        rows = conn.execute("SELECT task FROM search_history WHERE id>? AND checkpoint IS NOT NULL "
                            f"AND report_path IS NOT NULL AND task IS NOT NULL{condition} ORDER BY id LIMIT 100",
                            args).fetchall()
    return [{**{key: task[key] for key in ("id", "status", "report_ready")},
             "report_revision": task.get("report_revision", 1)}
            for row in rows if (task := json.loads(row[0]))["report_ready"]]


def archived_run_ids(profile: str) -> list[int]:
    history.init_db()
    with history._LOCK, closing(history._connect()) as conn:
        rows = conn.execute("SELECT id FROM search_history WHERE profile=? AND checkpoint IS NOT NULL "
                            "AND report_path IS NOT NULL AND finished_at IS NOT NULL ORDER BY id", (profile,))
        return [row[0] for row in rows]
