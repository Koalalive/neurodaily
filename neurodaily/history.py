"""Search history store (SQLite) + query-fingerprint dedup.

Every digest run is recorded so the web UI can list and re-open past searches.
A query *fingerprint* (derived from disciplines + keywords + source config) lets
us detect "duplicate" searches: the same query configuration run recently is
skipped, so an identical search isn't re-run on every manual click.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import hashlib
from contextlib import closing, contextmanager
from datetime import datetime
from uuid import uuid4

from .config import DEFAULT_DIRS
from .records import record_ids
from .search import QUERY_VERSION

_LOCK = threading.Lock()


def db_path() -> str:
    return os.path.join(DEFAULT_DIRS["output"], "search_history.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def desktop_schedule_result(profile: str, due: datetime | None = None) -> dict | None:
    """Read one slot, or the latest completed/failed slot for the profile."""
    init_db()
    with _LOCK, closing(_connect()) as conn, conn:
        if due is None:
            row = conn.execute("SELECT * FROM desktop_schedule_runs WHERE profile=? "
                               "ORDER BY finished_at DESC LIMIT 1", (profile,)).fetchone()
        else:
            row = conn.execute("SELECT * FROM desktop_schedule_runs WHERE profile=? AND due=?",
                               (profile, due.isoformat())).fetchone()
    return dict(row) if row else None


def save_desktop_schedule_result(profile: str, due: datetime, status: str, error=None) -> None:
    init_db()
    with _LOCK, closing(_connect()) as conn, conn:
        conn.execute("INSERT INTO desktop_schedule_runs VALUES (?, ?, ?, ?, ?) "
                     "ON CONFLICT(profile, due) DO UPDATE SET status=excluded.status, "
                     "finished_at=excluded.finished_at, error=excluded.error",
                     (profile, due.isoformat(), status, datetime.now().isoformat(), error))


def init_db() -> None:
    os.makedirs(os.path.dirname(db_path()), exist_ok=True)
    with _LOCK, closing(_connect()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT NOT NULL,
                profile TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,           -- 'completed' | 'skipped' | 'failed'
                skipped_reason TEXT,            -- e.g. 'duplicate'
                item_count INTEGER DEFAULT 0,
                source_counts TEXT,             -- JSON dict source->count
                report_path TEXT,               -- relative to output dir
                summary TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS delivery_leases (
                profile TEXT NOT NULL,
                destination TEXT NOT NULL,
                token TEXT NOT NULL,
                expires_at REAL NOT NULL,
                PRIMARY KEY (profile, destination)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS desktop_schedule_runs (
                profile TEXT NOT NULL,
                due TEXT NOT NULL,
                status TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                error TEXT,
                PRIMARY KEY (profile, due)
            )
        """)
        columns = {column["name"] for column in conn.execute("PRAGMA table_info(search_history)")}
        for column in ("snapshot", "task", "checkpoint"):
            if column not in columns:
                conn.execute(f"ALTER TABLE search_history ADD COLUMN {column} TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS history_task_status "
                     "ON search_history(status, id) WHERE task IS NOT NULL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS delivered_records (
                profile TEXT NOT NULL,
                destination TEXT NOT NULL,
                record_id TEXT NOT NULL,
                delivered_at TEXT NOT NULL,
                PRIMARY KEY (profile, destination, record_id)
            )
        """)


def compute_fingerprint(config, mode: str = "manual") -> str:
    """Fingerprint the profile and the inputs that determine search results."""
    query = {
        "profile": config.profile,
        "mode": mode,
        "disciplines": [d.to_dict() for d in config.disciplines],
        "global_keywords": config.global_keywords,
        "sources": config.sources,
        "windows": config.windows,
        "policy_feeds": config.policy_feeds,
        "journals": [(j.name, j.rss, j.aliases, j.issns) for j in config.journals],
        "query_version": QUERY_VERSION,
        "search": config.search,
    }
    raw = json.dumps(query, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def record_run(fingerprint: str, profile: str, status: str, started_at: str,
               finished_at: str, item_count: int = 0, source_counts: dict | None = None,
               report_path: str = "", skipped_reason: str = "", summary: str = "",
               snapshot: dict | None = None) -> int:
    init_db()
    with _LOCK, closing(_connect()) as conn, conn:
        cur = conn.execute(
            """INSERT INTO search_history
               (fingerprint, profile, started_at, finished_at, status, skipped_reason,
                item_count, source_counts, report_path, summary, snapshot)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (fingerprint, profile, started_at, finished_at, status, skipped_reason,
             item_count, json.dumps(source_counts or {}), report_path, summary,
             json.dumps(snapshot, ensure_ascii=False) if snapshot is not None else None),
        )
        return cur.lastrowid


def search_snapshot(config, mode, health, items, windows) -> dict:
    return {
        "query_version": QUERY_VERSION,
        "mode": mode,
        "search": config.search,
        "disciplines": [item.to_dict() for item in config.active_disciplines()],
        "global_keywords": config.global_keywords,
        "windows": windows,
        "sources": health,
        "journals": [{"name": j.name, "aliases": j.aliases, "issns": j.issns}
                     for j in config.journals],
        "records": [{"ids": item.extra.get("record_ids") or record_ids(item),
                     "title": item.title, "url": item.url,
                     "matched_rules": item.extra.get("matched_rules", []),
                     "missing_fields": item.extra.get("missing_fields", [])} for item in items],
    }


def compare_runs(before: dict, after: dict) -> dict:
    old = before.get("snapshot")
    new = after.get("snapshot")
    if old is None or new is None:
        raise ValueError("所选历史记录缺少检索快照")
    old_items, new_items = old["records"], new["records"]
    old_ids = {key for item in old_items for key in item["ids"]}
    new_ids = {key for item in new_items for key in item["ids"]}
    added = [item for item in new_items if old_ids.isdisjoint(item["ids"])]
    removed = [item for item in old_items if new_ids.isdisjoint(item["ids"])]
    return {"before": before["id"], "after": after["id"], "added": added, "removed": removed,
            "in_both": len(new_items) - len(added), "before_rules": old["search"],
            "after_rules": new["search"], "before_sources": old["sources"],
            "after_sources": new["sources"]}


def delivered_ids(profile: str, destination: str) -> set[str]:
    init_db()
    with _LOCK, closing(_connect()) as conn:
        return {row[0] for row in conn.execute(
            "SELECT record_id FROM delivered_records WHERE profile=? AND destination=?",
            (profile, destination),
        )}


@contextmanager
def delivery_lease(profile: str, destination: str, seconds: int = 900):
    """Serialize delivery for a profile/destination across desktop and CLI processes."""
    init_db()
    token = uuid4().hex
    now = time.time()
    with _LOCK, closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM delivery_leases WHERE profile=? AND destination=? AND expires_at<=?",
                     (profile, destination, now))
        acquired = conn.execute("INSERT OR IGNORE INTO delivery_leases VALUES (?, ?, ?, ?)",
                                (profile, destination, token, now + seconds)).rowcount == 1
    try:
        yield acquired
    finally:
        if acquired:
            with _LOCK, closing(_connect()) as conn, conn:
                conn.execute("DELETE FROM delivery_leases WHERE profile=? AND destination=? AND token=?",
                             (profile, destination, token))


def mark_delivered(profile: str, destination: str, ids, *,
                   connection: sqlite3.Connection | None = None) -> None:
    if connection is not None:
        now = datetime.now().isoformat()
        connection.executemany("INSERT OR IGNORE INTO delivered_records VALUES (?, ?, ?, ?)",
                               ((profile, destination, key, now) for key in ids))
        return
    init_db()
    with _LOCK, closing(_connect()) as conn, conn:
        mark_delivered(profile, destination, ids, connection=conn)


def is_duplicate(fingerprint: str, max_age_hours: int | None = None) -> dict | None:
    """Return the most recent completed/skipped run with the same fingerprint if it
    is 'recent enough' (default: within the same calendar day), else None."""
    init_db()
    cutoff = None
    if max_age_hours is not None:
        cutoff = datetime.fromtimestamp(time.time() - max_age_hours * 3600).isoformat()
    with _LOCK, closing(_connect()) as conn:
        if cutoff:
            row = conn.execute(
                """SELECT * FROM search_history
                   WHERE fingerprint=? AND status IN ('completed','skipped')
                     AND started_at >= ? ORDER BY id DESC LIMIT 1""",
                (fingerprint, cutoff),
            ).fetchone()
        else:
            # default: same calendar-day duplicate
            today_start = datetime.now().strftime("%Y-%m-%dT00:00:00")
            row = conn.execute(
                """SELECT * FROM search_history
                   WHERE fingerprint=? AND status IN ('completed','skipped')
                     AND started_at >= ? ORDER BY id DESC LIMIT 1""",
                (fingerprint, today_start),
            ).fetchone()
    if not row:
        return None
    result = dict(row)
    result.pop("checkpoint", None)
    return result


def list_runs(limit: int = 100, profile: str | None = None) -> list[dict]:
    init_db()
    with _LOCK, closing(_connect()) as conn:
        if profile:
            rows = conn.execute(
                "SELECT * FROM search_history WHERE profile=? ORDER BY id DESC LIMIT ?",
                (profile, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM search_history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d.pop("checkpoint", None)
        d["task"] = json.loads(d["task"]) if d["task"] else None
        d["source_counts"] = json.loads(d.get("source_counts") or "{}")
        d["has_snapshot"] = bool(d.pop("snapshot", None))
        out.append(d)
    return out


def get_run(run_id: int) -> dict | None:
    init_db()
    with _LOCK, closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM search_history WHERE id=?", (run_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d.pop("checkpoint", None)
    d["task"] = json.loads(d["task"]) if d["task"] else None
    d["source_counts"] = json.loads(d.get("source_counts") or "{}")
    d["snapshot"] = json.loads(d["snapshot"]) if d.get("snapshot") else None
    return d


def set_report_path(run_id: int, report_path: str) -> None:
    init_db()
    with _LOCK, closing(_connect()) as conn:
        conn.execute("UPDATE search_history SET report_path=? WHERE id=?",
                     (report_path, run_id))
        conn.commit()


def delete_run(run_id: int) -> bool:
    """Delete one history record. Returns True if a row was removed."""
    init_db()
    with _LOCK, closing(_connect()) as conn:
        cur = conn.execute("DELETE FROM search_history WHERE id=? AND status!='running'", (run_id,))
        conn.commit()
        return cur.rowcount > 0


def clear_history() -> int:
    """Delete all history records. Returns number of rows removed."""
    init_db()
    with _LOCK, closing(_connect()) as conn:
        cur = conn.execute("DELETE FROM search_history WHERE status!='running'")
        conn.commit()
        return cur.rowcount


def count_runs(profile: str | None = None) -> int:
    init_db()
    with _LOCK, closing(_connect()) as conn:
        if profile:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM search_history WHERE profile=?", (profile,)
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) AS n FROM search_history").fetchone()
    return int(row["n"]) if row else 0


def render_history_page(limit: int = 200) -> str:
    """Self-contained HTML history page (works when opened via file://).

    Each row links to the saved report HTML file relative to the output dir, so
    the page is fully browsable without the FastAPI server running.
    """
    runs = list_runs(limit=limit)
    rows = []
    for r in runs:
        status = r.get("status", "")
        cls = "ok" if status == "completed" else ("warn" if status == "skipped" else "bad")
        src_summary = ", ".join(f"{k}:{v}" for k, v in sorted(r.get("source_counts", {}).items()))
        fin = (r.get("finished_at") or "")[:19].replace("T", " ")
        report = r.get("report_path", "")
        link = f"<a href='{report}'>view report</a>" if report else "—"
        note = f" <span class='note'>({r.get('skipped_reason')})</span>" if r.get("skipped_reason") else ""
        rows.append(
            f"<tr><td>#{r['id']}</td><td>{fin}</td>"
            f"<td><span class='{cls}'>{status}</span>{note}</td>"
            f"<td>{r.get('item_count')}</td>"
            f"<td class='src'>{src_summary}</td><td>{link}</td></tr>"
        )
    body = "<div class='wrap'><h2>Search History</h2>"
    if rows:
        body += ("<table><thead><tr><th>#</th><th>Time</th><th>Status</th>"
                 "<th>Items</th><th>Sources</th><th>Report</th></tr></thead>"
                 f"<tbody>{''.join(rows)}</tbody></table>")
    else:
        body += "<div class='empty'>No searches recorded yet.</div>"
    body += "</div>"
    return f"""<!DOCTYPE html><html><head><meta charset='utf-8'>
<title>NeuroDaily — History</title>
<style>
 body{{font-family:-apple-system,'Segoe UI',Roboto,sans-serif;background:#000;color:#e8e8e8;margin:0}}
 .wrap{{max-width:1080px;margin:0 auto;padding:24px}}
 h2{{color:#38bdf8;margin:0 0 12px}}
 a{{color:#38bdf8;text-decoration:none}} a:hover{{text-decoration:underline}}
 table{{width:100%;border-collapse:collapse;font-size:.85rem}}
 th,td{{text-align:left;padding:8px;border-bottom:1px solid #222}}
 th{{color:#8a8a8a}} .src{{color:#8a8a8a;font-size:.75rem}}
 .ok{{color:#34d399}} .warn{{color:#fbbf24}} .bad{{color:#f87171}}
 .note{{color:#8a8a8a;font-size:.75rem}}
 .empty{{color:#8a8a8a;padding:12px;border:1px dashed #222;border-radius:12px}}
</style></head><body>{body}</body></html>"""
