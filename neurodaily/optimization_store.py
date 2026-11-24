"""Local conversation, judgement and trial records for search optimisation."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .config import DEFAULT_DIRS

_SCHEMA = """
CREATE TABLE IF NOT EXISTS preferences (scope TEXT PRIMARY KEY, enabled INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY, scope TEXT NOT NULL, profile TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS conversations_scope ON conversations(scope, created_at DESC);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id),
  role TEXT NOT NULL, text TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id),
  scope TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS runs_status ON runs(status, created_at);
CREATE TABLE IF NOT EXISTS labelled_records (
  scope TEXT NOT NULL, record_id TEXT NOT NULL, label_id TEXT NOT NULL, relevant INTEGER NOT NULL, report_date TEXT,
  PRIMARY KEY(scope, record_id)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Conflict(ValueError):
    """A concurrent change or the current status prevents an operation."""


class Store:
    def __init__(self, path: Path | None = None):
        self.path = path or Path(DEFAULT_DIRS["output"]) / "search_optimization.db"

    @contextmanager
    def connect(self, *, write=False):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=10)) as conn, conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.executescript(_SCHEMA)
            if write:
                conn.execute("BEGIN IMMEDIATE")
            yield conn

    def enabled(self, scope):
        with self.connect() as conn:
            row = conn.execute("SELECT enabled FROM preferences WHERE scope=?", (scope,)).fetchone()
        return row is None or bool(row[0])

    def preference(self, scope, enabled):
        with self.connect(write=True) as conn:
            conn.execute("INSERT OR REPLACE INTO preferences VALUES (?, ?)", (scope, enabled))

    def conversation(self, scope, profile, conversation_id=None, *, new=False):
        with self.connect(write=True) as conn:
            if conversation_id:
                row = conn.execute("SELECT id FROM conversations WHERE id=? AND scope=?",
                                   (conversation_id, scope)).fetchone()
                if row is None:
                    raise LookupError("Conversation not found")
                return row[0]
            if not new:
                row = conn.execute("SELECT id FROM conversations WHERE scope=? ORDER BY created_at DESC LIMIT 1",
                                   (scope,)).fetchone()
                if row:
                    return row[0]
            conversation_id = uuid4().hex
            conn.execute("INSERT INTO conversations VALUES (?, ?, ?, ?)",
                         (conversation_id, scope, profile, _now()))
            return conversation_id

    def conversations(self, scope):
        with self.connect() as conn:
            rows = conn.execute("""SELECT c.id, c.created_at, (
                    SELECT substr(text, 1, 80) FROM messages WHERE conversation_id=c.id
                    AND role='user' ORDER BY id LIMIT 1) AS title FROM conversations c
                    WHERE c.scope=? ORDER BY c.created_at DESC LIMIT 30""", (scope,)).fetchall()
        return [dict(row) for row in rows]

    def messages(self, scope, conversation_id=None, *, limit=60):
        with self.connect() as conn:
            rows = conn.execute("""SELECT m.role, m.text, m.created_at FROM messages m
                JOIN conversations c ON c.id=m.conversation_id WHERE c.scope=?
                AND (? IS NULL OR c.id=?) ORDER BY m.id DESC LIMIT ?""",
                (scope, conversation_id, conversation_id, limit)).fetchall()
        return [dict(row) for row in reversed(rows)]

    def launch(self, scope, conversation_id, data, text):
        data = {**data, "id": uuid4().hex, "conversation_id": conversation_id,
                "status": "queued", "created_at": _now()}
        with self.connect(write=True) as conn:
            enabled = conn.execute("SELECT enabled FROM preferences WHERE scope=?", (scope,)).fetchone()
            if enabled is not None and not enabled[0]:
                raise Conflict("AI search optimisation is disabled")
            active = conn.execute("""SELECT 1 FROM runs WHERE scope=? AND status IN
                ('queued','running','applying','rolling_back')""", (scope,)).fetchone()
            if active:
                raise Conflict("A search optimisation is already running")
            conn.execute("INSERT INTO messages(conversation_id, role, text, created_at) VALUES (?, 'user', ?, ?)",
                         (conversation_id, text, _now()))
            conn.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?)",
                         (data["id"], conversation_id, scope, data["status"], data["created_at"], json.dumps(data)))
        return data

    def get(self, scope, run_id=None, *, conversation_id=None):
        with self.connect() as conn:
            row = conn.execute("""SELECT data FROM runs WHERE scope=? AND (? IS NULL OR id=?)
                AND (? IS NULL OR conversation_id=?) ORDER BY created_at DESC LIMIT 1""",
                (scope, run_id, run_id, conversation_id, conversation_id)).fetchone()
        if row is None and run_id:
            raise LookupError("Optimisation run not found")
        return json.loads(row[0]) if row else None

    def update(self, scope, run_id, changes, *, expect=None, message=None):
        with self.connect(write=True) as conn:
            row = conn.execute("SELECT data FROM runs WHERE scope=? AND id=?", (scope, run_id)).fetchone()
            if row is None:
                raise LookupError("Optimisation run not found")
            data = json.loads(row[0])
            if expect is not None and data["status"] not in expect:
                raise Conflict("The optimisation run changed status")
            next_status = changes.get("status")
            if next_status in {"queued", "applying", "rolling_back"} and conn.execute("""
                    SELECT 1 FROM runs WHERE scope=? AND id<>? AND status IN
                    ('queued','running','applying','rolling_back')""", (scope, run_id)).fetchone():
                raise Conflict("Another optimisation is active for this profile")
            data.update(changes)
            conn.execute("UPDATE runs SET status=?, data=? WHERE id=?", (data["status"], json.dumps(data), run_id))
            if message:
                role, text = message
                conn.execute("INSERT INTO messages(conversation_id, role, text, created_at) VALUES (?, ?, ?, ?)",
                             (data["conversation_id"], role, text, _now()))
        return data

    def pending(self, scope):
        with self.connect() as conn:
            row = conn.execute("""SELECT data FROM runs WHERE scope=? AND status IN
                ('queued','running','applying','rolling_back') ORDER BY created_at LIMIT 1""", (scope,)).fetchone()
        return json.loads(row[0]) if row else None

    def label(self, scope, ids, relevant, date=None):
        ids = set(ids)
        markers = ",".join("?" for _ in ids)
        with self.connect(write=True) as conn:
            groups = conn.execute(f"SELECT DISTINCT label_id, report_date FROM labelled_records WHERE scope=? "
                                  f"AND record_id IN ({markers})", (scope, *ids)).fetchall()
            recorded_dates = [when for _, when in groups if when]
            for group, _ in groups:
                ids.update(row[0] for row in conn.execute(
                    "SELECT record_id FROM labelled_records WHERE scope=? AND label_id=?", (scope, group)))
            group = uuid4().hex
            effective = min([date, *recorded_dates] if date else recorded_dates, default=None)
            conn.executemany("INSERT OR REPLACE INTO labelled_records VALUES (?, ?, ?, ?, ?)",
                             [(scope, identifier, group, relevant, effective) for identifier in ids])

    def labels(self, scope):
        with self.connect() as conn:
            rows = conn.execute("SELECT record_id, label_id, relevant, report_date FROM labelled_records "
                                "WHERE scope=? ORDER BY record_id",
                                (scope,)).fetchall()
        grouped = {}
        for identifier, label_id, relevant, date in rows:
            label = grouped.setdefault(label_id, {"ids": [], "relevant": bool(relevant)})
            if date:
                label["date"] = date
            label["ids"].append(identifier)
        return list(grouped.values())
