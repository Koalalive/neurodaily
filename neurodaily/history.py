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
from datetime import datetime

from .config import DEFAULT_DIRS

_LOCK = threading.Lock()


def db_path() -> str:
    return os.path.join(DEFAULT_DIRS["output"], "search_history.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    os.makedirs(os.path.dirname(db_path()), exist_ok=True)
    with _LOCK, _connect() as conn:
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
        conn.commit()


def compute_fingerprint(config) -> str:
    """Deterministic fingerprint of the query configuration (for dedup).

    Includes active disciplines (name+mesh+keywords+arxiv cats), global keywords,
    source enabled/max_results/lookback, and journals with RSS. Order-insensitive
    (sorted) so reordering config keys doesn't create false duplicates.
    """
    parts = []
    for d in config.active_disciplines():
        parts.append("|".join(sorted([d.name, *d.mesh_terms, *d.keywords, *d.arxiv_cats])))
    parts.append("|".join(sorted(config.global_keywords)))
    for name, opts in sorted(config.sources.items()):
        en = opts.get("enabled", True)
        parts.append(f"{name}:{en}:{opts.get('max_results', 20)}:{opts.get('lookback_days', 7)}")
    parts.append("|".join(sorted(j.name for j in config.journals if j.rss)))
    raw = "\n".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def record_run(fingerprint: str, profile: str, status: str, started_at: str,
               finished_at: str, item_count: int = 0, source_counts: dict | None = None,
               report_path: str = "", skipped_reason: str = "", summary: str = "") -> int:
    init_db()
    with _LOCK, _connect() as conn:
        cur = conn.execute(
            """INSERT INTO search_history
               (fingerprint, profile, started_at, finished_at, status, skipped_reason,
                item_count, source_counts, report_path, summary)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (fingerprint, profile, started_at, finished_at, status, skipped_reason,
             item_count, json.dumps(source_counts or {}), report_path, summary),
        )
        conn.commit()
        return cur.lastrowid


def is_duplicate(fingerprint: str, max_age_hours: int | None = None) -> dict | None:
    """Return the most recent completed/skipped run with the same fingerprint if it
    is 'recent enough' (default: within the same calendar day), else None."""
    init_db()
    cutoff = None
    if max_age_hours is not None:
        cutoff = datetime.fromtimestamp(time.time() - max_age_hours * 3600).isoformat()
    with _LOCK, _connect() as conn:
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
    return dict(row) if row else None


def list_runs(limit: int = 100, profile: str | None = None) -> list[dict]:
    init_db()
    with _LOCK, _connect() as conn:
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
        d["source_counts"] = json.loads(d.get("source_counts") or "{}")
        out.append(d)
    return out


def get_run(run_id: int) -> dict | None:
    init_db()
    with _LOCK, _connect() as conn:
        row = conn.execute(
            "SELECT * FROM search_history WHERE id=?", (run_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["source_counts"] = json.loads(d.get("source_counts") or "{}")
    return d


def set_report_path(run_id: int, report_path: str) -> None:
    init_db()
    with _LOCK, _connect() as conn:
        conn.execute("UPDATE search_history SET report_path=? WHERE id=?",
                     (report_path, run_id))
        conn.commit()


def delete_run(run_id: int) -> bool:
    """Delete one history record. Returns True if a row was removed."""
    init_db()
    with _LOCK, _connect() as conn:
        cur = conn.execute("DELETE FROM search_history WHERE id=?", (run_id,))
        conn.commit()
        return cur.rowcount > 0


def clear_history() -> int:
    """Delete all history records. Returns number of rows removed."""
    init_db()
    with _LOCK, _connect() as conn:
        cur = conn.execute("DELETE FROM search_history")
        conn.commit()
        return cur.rowcount


def count_runs(profile: str | None = None) -> int:
    init_db()
    with _LOCK, _connect() as conn:
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
 body{{font-family:-apple-system,'Segoe UI',Roboto,sans-serif;background:#0f1420;color:#e2e8f0;margin:0}}
 .wrap{{max-width:1080px;margin:0 auto;padding:24px}}
 h2{{color:#38bdf8;margin:0 0 12px}}
 a{{color:#38bdf8;text-decoration:none}} a:hover{{text-decoration:underline}}
 table{{width:100%;border-collapse:collapse;font-size:.85rem}}
 th,td{{text-align:left;padding:8px;border-bottom:1px solid #2a3550}}
 th{{color:#94a3b8}} .src{{color:#94a3b8;font-size:.75rem}}
 .ok{{color:#34d399}} .warn{{color:#fbbf24}} .bad{{color:#f87171}}
 .note{{color:#94a3b8;font-size:.75rem}}
 .empty{{color:#94a3b8;padding:12px;border:1px dashed #2a3550;border-radius:12px}}
</style></head><body>{body}</body></html>"""
