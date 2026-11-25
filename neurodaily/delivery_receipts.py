"""Store per-task delivery attempts in the local search-history database."""
from __future__ import annotations

import hashlib
import json
import time
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path

from . import history


def destination_id(channel: str, address: str) -> str:
    return channel + ":" + hashlib.sha256(address.encode()).hexdigest()


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
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS email_delivery_queue (
                task_id TEXT NOT NULL,
                destination TEXT NOT NULL,
                report_path TEXT NOT NULL,
                address TEXT NOT NULL,
                language TEXT NOT NULL,
                due TEXT NOT NULL,
                PRIMARY KEY (task_id, destination),
                FOREIGN KEY (task_id, destination) REFERENCES delivery_receipts(task_id, destination)
                    ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS email_delivery_due ON email_delivery_queue (due);
            CREATE TABLE IF NOT EXISTS migrated_email_queue (path TEXT PRIMARY KEY);
        """)


def _put_email(conn, *, task_id, report_path, profile, address, language, due) -> None:
    destination = destination_id("email", address.casefold())
    conn.execute("""
        INSERT OR IGNORE INTO email_delivery_queue (task_id, destination, report_path, address, language, due)
        SELECT task_id, destination, ?, ?, ?, ? FROM delivery_receipts
        WHERE task_id=? AND destination=? AND channel='email' AND (?='' OR profile=?)
          AND status IN ('pending', 'checking', 'sending')
    """, (report_path, address, language, due, task_id, destination, profile, profile))


def enqueue_email(**entry) -> None:
    _init_db()
    with _connect() as conn:
        _put_email(conn, **entry)


def queued_emails(legacy_path: Path, *, now: datetime | None = None) -> list[dict]:
    _init_db()
    with _connect() as conn:
        marker = str(legacy_path.absolute())
        if not conn.execute("SELECT 1 FROM migrated_email_queue WHERE path=?", (marker,)).fetchone():
            _migrate_queue(conn, legacy_path, marker)
        sql = """
            SELECT q.*, r.profile FROM email_delivery_queue q
            JOIN delivery_receipts r USING (task_id, destination)
            JOIN search_history h ON h.id=q.task_id
        """
        params = ()
        if now is not None:
            sql += "WHERE q.due<=? AND h.status NOT IN ('running','interrupted')"
            params = (now.isoformat(),)
        return [dict(row) for row in conn.execute(sql + " ORDER BY q.due, q.rowid", params)]


def _migrate_queue(conn, path: Path, marker: str) -> None:
    try:
        legacy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(legacy, list):
        return
    if not conn.execute("INSERT OR IGNORE INTO migrated_email_queue VALUES (?)", (marker,)).rowcount:
        return
    for row in legacy:
        if not isinstance(row, dict):
            continue
        task_id = str(row.get("task_id", ""))
        address = row.get("address")
        report_path = row.get("report_path")
        if not task_id.isascii() or not task_id.isdecimal() or not all(
            isinstance(value, str) and value.strip() for value in (address, report_path)
        ):
            continue
        try:
            due = datetime.fromisoformat(str(row.get("due"))).isoformat()
        except ValueError:
            due = ""
        _put_email(conn, task_id=task_id, report_path=report_path, profile=str(row.get("profile") or ""),
                   address=address.strip(), language=str(row.get("language") or "zh"), due=due)


def claim_queued_email(task_id: str, profile: str, destination: str) -> bool:
    """Resolve a previous crashed claimant while holding the destination lease."""
    now = datetime.now().isoformat()
    with _connect() as conn:
        updated = conn.execute("""
            UPDATE delivery_receipts SET status='checking', updated_at=?, error=NULL
            WHERE task_id=? AND destination=? AND profile=? AND status IN ('pending','checking')
              AND EXISTS (SELECT 1 FROM email_delivery_queue WHERE task_id=? AND destination=?)
              AND EXISTS (SELECT 1 FROM search_history WHERE id=? AND status='completed')
        """, (now, task_id, destination, profile, task_id, destination, task_id))
        if updated.rowcount:
            return True
        conn.execute("""
            UPDATE delivery_receipts SET status='unknown', updated_at=?, error=?
            WHERE task_id=? AND destination=? AND profile=? AND status='sending'
        """, (now, "投递中断，未能确认服务器是否接受。", task_id, destination, profile))
        return False


def remove_queued_email(task_id: str, destination: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM email_delivery_queue WHERE task_id=? AND destination=?", (task_id, destination))


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
