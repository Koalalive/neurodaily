"""Store per-task delivery attempts in the local search-history database."""
from __future__ import annotations

import time
from contextlib import closing, contextmanager
from datetime import datetime

from . import history


@contextmanager
def _connect():
    with closing(history._connect()) as conn, conn:
        yield conn


def _init_db() -> None:
    history.init_db()
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS delivery_receipts (
                task_id TEXT NOT NULL,
                profile TEXT NOT NULL,
                destination TEXT NOT NULL,
                channel TEXT NOT NULL,
                label TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                error TEXT,
                PRIMARY KEY (task_id, destination),
                FOREIGN KEY (task_id) REFERENCES search_history(id) ON DELETE CASCADE
            )
        """)


def prepare(task_id: str, profile: str, targets: list[tuple[str, str, str]]) -> None:
    _init_db()
    now = datetime.now().isoformat()
    with _connect() as conn:
        conn.executemany("""
            INSERT OR IGNORE INTO delivery_receipts
              (task_id, profile, destination, channel, label, status, updated_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, ((task_id, profile, destination, channel, label, now)
              for destination, channel, label in targets))


def list_receipts(task_id: str) -> list[dict]:
    _init_db()
    with _connect() as conn:
        rows = conn.execute("""
            SELECT destination, channel, label, status, attempts, updated_at, error,
                   EXISTS(SELECT 1 FROM delivery_leases l WHERE l.profile=r.profile
                          AND l.destination=r.destination AND l.expires_at>?) AS active
            FROM delivery_receipts r WHERE task_id=? ORDER BY rowid
        """, (time.time(), task_id)).fetchall()
    receipts = []
    for row in rows:
        receipt = dict(row)
        active = receipt.pop("active")
        if receipt["status"] == "checking":
            receipt["status"] = "pending"
        elif receipt["status"] == "sending" and not active:
            receipt["status"] = "unknown"
            receipt["error"] = "投递中断，未能确认服务器是否接受。"
        receipts.append(receipt)
    return receipts


def close_interrupted(conn, task_id: str) -> None:
    """Resolve abandoned targets after acquiring the search task lock."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='delivery_receipts'").fetchone():
        return
    now = datetime.now().isoformat()
    conn.execute("UPDATE delivery_receipts SET status='failed', updated_at=?, error=? "
                 "WHERE task_id=? AND status IN ('pending','checking')",
                 (now, "上次任务在开始投递前中断，可以重试。", task_id))
    conn.execute("UPDATE delivery_receipts SET status='unknown', updated_at=?, error=? "
                 "WHERE task_id=? AND status='sending'",
                 (now, "投递中断，未能确认服务器是否接受。", task_id))


def recover_for_resume(conn, task_id: str) -> None:
    """Allow targets with no send attempt to continue; preserve uncertain outcomes."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='delivery_receipts'").fetchone():
        return
    now = datetime.now().isoformat()
    conn.execute("UPDATE delivery_receipts SET status='pending', updated_at=? "
                 "WHERE task_id=? AND status='checking'", (now, task_id))
    conn.execute("UPDATE delivery_receipts SET status='unknown', updated_at=?, error=? "
                 "WHERE task_id=? AND status='sending'",
                 (now, "投递中断，未能确认服务器是否接受。", task_id))


def transition(task_id: str, profile: str, destination: str, previous: str, status: str,
               *, error: str | None = None, sent: set[str] | None = None,
               expected_attempts: int | None = None) -> bool:
    """Compare and set the receipt; commit acknowledged record IDs with it."""
    now = datetime.now().isoformat()
    with _connect() as conn:
        updated = conn.execute("""
            UPDATE delivery_receipts
            SET status=?, updated_at=?, error=?, attempts=attempts+?
            WHERE task_id=? AND profile=? AND destination=? AND status=?
              AND (? IS NULL OR attempts=?)
        """, (status, now, error, int(status == "sending"), task_id, profile, destination, previous,
              expected_attempts, expected_attempts))
        if updated.rowcount and sent:
            history.mark_delivered(profile, destination, sent, connection=conn)
        return updated.rowcount == 1
