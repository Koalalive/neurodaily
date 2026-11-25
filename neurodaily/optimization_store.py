"""Local conversation, judgement and trial records for search optimisation."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import time
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
CREATE INDEX IF NOT EXISTS runs_conversation ON runs(scope, conversation_id, created_at DESC);
CREATE TABLE IF NOT EXISTS revisions (scope TEXT PRIMARY KEY, revision INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS run_progress (
  run_id TEXT PRIMARY KEY REFERENCES runs(id) ON DELETE CASCADE,
  stage TEXT NOT NULL, round_number INTEGER NOT NULL, rounds INTEGER NOT NULL, trial_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS network_budgets (
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE, phase TEXT NOT NULL,
  request_limit INTEGER NOT NULL, seconds_limit INTEGER NOT NULL, started REAL NOT NULL,
  requests INTEGER NOT NULL DEFAULT 0, finished REAL, reason TEXT,
  PRIMARY KEY(run_id, phase)
);
CREATE TABLE IF NOT EXISTS labelled_records (
  scope TEXT NOT NULL, record_id TEXT NOT NULL, label_id TEXT NOT NULL, relevant INTEGER NOT NULL, report_date TEXT,
  PRIMARY KEY(scope, record_id)
);
CREATE TABLE IF NOT EXISTS report_feedback (
  id INTEGER PRIMARY KEY, scope TEXT NOT NULL, report_id INTEGER NOT NULL, record_key TEXT NOT NULL,
  relevant INTEGER NOT NULL, record_ids TEXT NOT NULL, report_date TEXT, title TEXT NOT NULL,
  source TEXT NOT NULL, journal TEXT NOT NULL, rules TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS feedback_report ON report_feedback(scope, report_id, id DESC);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Conflict(ValueError):
    """A concurrent change or the current status prevents an operation."""


class LabelsChanged(Conflict):
    def __init__(self):
        super().__init__("相关性标注已修改。请用最新标注重新试跑，再应用方案。")


class Store:
    def __init__(self, path: Path | None = None):
        self.path = path or Path(DEFAULT_DIRS["output"]) / "search_optimization.db"
        self._schema_lock = Lock()
        self._initialized = False

    @contextmanager
    def connect(self, *, write=False):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=10)) as conn, conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            if not self._initialized:
                with self._schema_lock:
                    if not self._initialized:
                        conn.executescript(_SCHEMA)
                        self._initialized = True
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
            self._touch(conn, scope)

    @staticmethod
    def _touch(conn, scope):
        conn.execute("INSERT INTO revisions VALUES (?, 1) ON CONFLICT(scope) DO UPDATE SET revision=revision+1", (scope,))

    @staticmethod
    def _progress(conn, data):
        conn.execute("INSERT OR REPLACE INTO run_progress VALUES (?, ?, ?, ?, ?)",
                     (data["id"], data["stage"], data.get("round", 0), data.get("rounds", 0), data.get("trial_count", 0)))

    def summary(self, scope, conversation_id):
        """Read only the persisted polling projection and network budget columns."""
        with self.connect() as conn:
            row = conn.execute("SELECT revision FROM revisions WHERE scope=?", (scope,)).fetchone()
            revision = row[0] if row else 0
            row = conn.execute("SELECT enabled FROM preferences WHERE scope=?", (scope,)).fetchone()
            enabled = row is None or bool(row[0])
            row = conn.execute("""SELECT r.id, r.status, p.stage, p.round_number AS round, p.rounds, p.trial_count
                FROM runs AS r LEFT JOIN run_progress AS p ON p.run_id=r.id
                WHERE r.scope=? AND r.conversation_id=? ORDER BY r.created_at DESC LIMIT 1""",
                (scope, conversation_id)).fetchone()
            budgets = self._budgets(conn, row["id"]) if row else []
            return revision, enabled, dict(row) if row else None, budgets

    def conversation(self, scope, profile, conversation_id=None, *, new=False):
        if conversation_id:
            with self.connect() as conn:
                row = conn.execute("SELECT id FROM conversations WHERE id=? AND scope=?",
                                   (conversation_id, scope)).fetchone()
            if row is None:
                raise LookupError("Conversation not found")
            return row[0]
        with self.connect(write=True) as conn:
            if not new:
                row = conn.execute("SELECT id FROM conversations WHERE scope=? ORDER BY created_at DESC LIMIT 1",
                                   (scope,)).fetchone()
                if row:
                    return row[0]
            conversation_id = uuid4().hex
            conn.execute("INSERT INTO conversations VALUES (?, ?, ?, ?)",
                         (conversation_id, scope, profile, _now()))
            self._touch(conn, scope)
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
            self._progress(conn, data)
            self._touch(conn, scope)
        return data

    def get(self, scope, run_id=None, *, conversation_id=None):
        with self.connect() as conn:
            row = conn.execute("""SELECT data FROM runs WHERE scope=? AND (? IS NULL OR id=?)
                AND (? IS NULL OR conversation_id=?) ORDER BY created_at DESC LIMIT 1""",
                (scope, run_id, run_id, conversation_id, conversation_id)).fetchone()
        if row is None and run_id:
            raise LookupError("Optimisation run not found")
        return json.loads(row[0]) if row else None

    def update(self, scope, run_id, changes, *, expect=None, message=None, expected_labels=None, finish_budget=None):
        with self.connect(write=True) as conn:
            row = conn.execute("SELECT data FROM runs WHERE scope=? AND id=?", (scope, run_id)).fetchone()
            if row is None:
                raise LookupError("Optimisation run not found")
            data = json.loads(row[0])
            if expect is not None and data["status"] not in expect:
                raise Conflict("The optimisation run changed status")
            if expected_labels is not None and self._labels(conn, scope) != expected_labels:
                raise LabelsChanged()
            next_status = changes.get("status")
            if next_status in {"queued", "applying", "rolling_back"} and conn.execute("""
                    SELECT 1 FROM runs WHERE scope=? AND id<>? AND status IN
                    ('queued','running','applying','rolling_back')""", (scope, run_id)).fetchone():
                raise Conflict("Another optimisation is active for this profile")
            data.update(changes)
            conn.execute("UPDATE runs SET status=?, data=? WHERE id=?", (data["status"], json.dumps(data), run_id))
            self._progress(conn, data)
            self._touch(conn, scope)
            if finish_budget is not None:
                self._budget_progress(conn, run_id, finish_budget, finish=True)
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

    def running(self, scope, run_id):
        with self.connect() as conn:
            return self._running(conn, scope, run_id)

    @staticmethod
    def _running(conn, scope, run_id):
        return conn.execute("""SELECT 1 FROM runs AS r LEFT JOIN preferences AS p ON p.scope=r.scope
            WHERE r.id=? AND r.scope=? AND r.status='running' AND COALESCE(p.enabled, 1)""",
            (run_id, scope)).fetchone() is not None

    def begin_budget(self, run_id, phase, request_limit, seconds_limit):
        with self.connect(write=True) as conn:
            conn.execute("""INSERT OR IGNORE INTO network_budgets(run_id, phase, request_limit, seconds_limit, started)
                VALUES (?, ?, ?, ?, ?)""", (run_id, phase, request_limit, seconds_limit, time()))

    def reserve_request(self, scope, run_id, phase):
        with self.connect(write=True) as conn:
            if not self._running(conn, scope, run_id):
                return 0.0, "cancelled"
            row = self._budget(conn, run_id, phase)
            remaining = row["seconds_limit"] - (time() - row["started"])
            reason = row["reason"]
            if reason is None and row["finished"] is not None:
                return 0.0, "finished"
            if reason is None and remaining <= 0:
                reason = "online_time_budget_exhausted"
            if reason is None and row["requests"] >= row["request_limit"]:
                reason = "online_request_budget_exhausted"
            if reason:
                conn.execute("UPDATE network_budgets SET reason=? WHERE run_id=? AND phase=?", (reason, run_id, phase))
                return 0.0, reason
            conn.execute("UPDATE network_budgets SET requests=requests+1 WHERE run_id=? AND phase=?", (run_id, phase))
            return remaining, None

    def budget_progress(self, run_id, phase, *, finish=False):
        with self.connect(write=True) as conn:
            return self._budget_progress(conn, run_id, phase, finish=finish)

    @classmethod
    def _budget_progress(cls, conn, run_id, phase, *, finish):
        row = cls._budget(conn, run_id, phase)
        if row is None:
            return None
        now = time()
        elapsed = max(0, (row["finished"] if row["finished"] is not None else now) - row["started"])
        reason = row["reason"] or ("online_time_budget_exhausted" if elapsed >= row["seconds_limit"] else None)
        if reason != row["reason"] or (finish and row["finished"] is None):
            conn.execute("UPDATE network_budgets SET reason=?, finished=COALESCE(finished, ?) WHERE run_id=? AND phase=?",
                         (reason, now if finish else None, run_id, phase))
        return cls._public_budget({**dict(row), "reason": reason}, now)

    @staticmethod
    def _budget(conn, run_id, phase):
        return conn.execute("SELECT * FROM network_budgets WHERE run_id=? AND phase=?", (run_id, phase)).fetchone()

    @staticmethod
    def _public_budget(row, now):
        end = row["finished"] if row["finished"] is not None else now
        elapsed = max(0.0, end - row["started"])
        return {"phase": row["phase"], "request_limit": row["request_limit"], "requests": row["requests"],
                "seconds_limit": row["seconds_limit"], "elapsed_seconds": round(elapsed, 1), "reason": row["reason"]}

    @classmethod
    def _budgets(cls, conn, run_id):
        now = time()
        return [cls._public_budget(row, now) for row in conn.execute(
            "SELECT * FROM network_budgets WHERE run_id=? ORDER BY started", (run_id,))]

    @staticmethod
    def _label(conn, scope, ids, relevant, date):
        ids = set(ids)
        markers = ",".join("?" for _ in ids)
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

    def label(self, scope, ids, relevant, date=None):
        with self.connect(write=True) as conn:
            self._label(conn, scope, ids, relevant, date)
            self._touch(conn, scope)

    def record_feedback(self, scope, ids, relevant, date, *, report_id, record_key, title, source, journal, rules):
        """Keep each report vote and update its effective evaluation label atomically."""
        with self.connect(write=True) as conn:
            self._label(conn, scope, ids, relevant, date)
            conn.execute("""INSERT INTO report_feedback(scope, report_id, record_key, relevant, record_ids,
                report_date, title, source, journal, rules, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (scope, report_id, record_key, relevant, json.dumps(ids), date, title[:500], source[:160],
                 journal[:240], json.dumps([rule[:180] for rule in rules[:20]]), _now()))
            self._touch(conn, scope)

    def report_feedback(self, scope, report_id):
        with self.connect() as conn:
            rows = conn.execute("""SELECT record_key, relevant FROM report_feedback WHERE scope=? AND report_id=?
                ORDER BY id ASC""", (scope, report_id)).fetchall()
        return {row[0]: bool(row[1]) for row in rows}

    def recent_feedback(self, scope, limit=50):
        with self.connect() as conn:
            rows = conn.execute("""SELECT f.title, f.source, f.journal, f.rules, f.relevant, f.report_date
                FROM report_feedback AS f INNER JOIN (
                    SELECT MAX(id) AS latest FROM report_feedback WHERE scope=? GROUP BY report_id, record_key
                ) AS last ON last.latest=f.id ORDER BY f.id DESC LIMIT ?""", (scope, limit)).fetchall()
        return [{**dict(row), "rules": json.loads(row["rules"]), "relevant": bool(row["relevant"])} for row in rows]

    def labels(self, scope):
        with self.connect() as conn:
            return self._labels(conn, scope)

    @contextmanager
    def hold_labels(self, scope, expected):
        with self.connect(write=True) as conn:
            if self._labels(conn, scope) != expected:
                raise LabelsChanged()
            yield

    @staticmethod
    def _labels(conn, scope):
        rows = conn.execute("SELECT record_id, label_id, relevant, report_date FROM labelled_records "
                            "WHERE scope=? ORDER BY record_id", (scope,)).fetchall()
        grouped = {}
        for identifier, label_id, relevant, date in rows:
            label = grouped.setdefault(label_id, {"ids": [], "relevant": bool(relevant)})
            if date:
                label["date"] = date
            label["ids"].append(identifier)
        return list(grouped.values())
