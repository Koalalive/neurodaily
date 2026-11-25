"""Local append-only history of research settings by configuration location."""
from __future__ import annotations

from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import sqlite3

from .config import Config, DEFAULT_DIRS, config_lock_path, research_config, revision_for
from .file_lock import file_lock

_PROVENANCE_KEYS = {"optimization_run_id", "candidate_id", "snapshot_id", "round", "restored_revision"}
LOG = logging.getLogger(__name__)
_SCHEMA = """
CREATE TABLE IF NOT EXISTS revisions (
    id INTEGER PRIMARY KEY, slot TEXT NOT NULL, revision TEXT NOT NULL, profile TEXT NOT NULL,
    created_at TEXT NOT NULL, origin TEXT NOT NULL, provenance TEXT NOT NULL, document TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS revision_slot_id ON revisions(slot, id DESC);
CREATE TABLE IF NOT EXISTS revision_writes (
    slot TEXT PRIMARY KEY, digest TEXT NOT NULL, origin TEXT NOT NULL, provenance TEXT NOT NULL
);
"""


@contextmanager
def _connection():
    path = Path(DEFAULT_DIRS["output"]) / "config_revisions.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=10)) as conn, conn:
        conn.row_factory = sqlite3.Row
        conn.executescript(_SCHEMA)
        conn.execute("BEGIN IMMEDIATE")
        yield conn


def _append(conn, slot, config, origin, provenance=None):
    revision = revision_for(config)
    previous = conn.execute("SELECT revision FROM revisions WHERE slot=? ORDER BY id DESC LIMIT 1", (slot,)).fetchone()
    if previous and previous["revision"] == revision:
        return
    document = json.dumps(research_config(config), ensure_ascii=False, allow_nan=False)
    conn.execute("INSERT INTO revisions(slot,revision,profile,created_at,origin,provenance,document) VALUES(?,?,?,?,?,?,?)",
                 (slot, revision, config.profile, datetime.now(timezone.utc).isoformat(), origin,
                  json.dumps(provenance or {}, ensure_ascii=False), document))


def _file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _reconcile(conn, slot, path):
    intent = conn.execute("SELECT digest,origin,provenance FROM revision_writes WHERE slot=?", (slot,)).fetchone()
    if intent is not None:
        if Path(path).is_file() and _file_digest(path) == intent["digest"]:
            _append(conn, slot, Config.load(path), intent["origin"], json.loads(intent["provenance"]))
        conn.execute("DELETE FROM revision_writes WHERE slot=?", (slot,))


def save_revision(path, temporary, *, origin, provenance):
    """Record a recoverable write intent before changing the authoritative JSON file."""
    slot = config_lock_path(path).name
    try:
        previous = Config.load(path) if Path(path).is_file() else None
    except (ValueError, TypeError, KeyError):
        previous = None  # An unreadable old file has no usable research revision.
    provenance = {key: value for key, value in (provenance or {}).items()
                  if key in _PROVENANCE_KEYS and (type(value) is int or isinstance(value, str) and len(value) <= 128)}
    with _connection() as conn:
        _reconcile(conn, slot, path)
        if previous is not None:
            _append(conn, slot, previous, "existing")
        conn.execute("INSERT INTO revision_writes VALUES (?,?,?,?)",
                     (slot, _file_digest(temporary), origin, json.dumps(provenance, ensure_ascii=False)))
    os.replace(temporary, path)
    try:
        with _connection() as conn:
            _reconcile(conn, slot, path)
    except (OSError, sqlite3.Error):
        # The file is already installed. The committed intent lets the next history read finish the write.
        LOG.warning("Profile revision indexing deferred after configuration save")


def _metadata(row):
    return {**{key: row[key] for key in ("id", "revision", "profile", "created_at", "origin")},
            "provenance": json.loads(row["provenance"])}


def list_revisions(path, *, limit=50, before=None):
    path = path or Config.default_path()
    lock_path = config_lock_path(path)
    with file_lock(lock_path), _connection() as conn:
        current = Config.load(path)
        _reconcile(conn, lock_path.name, path)
        _append(conn, lock_path.name, current, "existing")
        rows = conn.execute("""SELECT id, revision, profile, created_at, origin, provenance FROM revisions
                             WHERE slot=? AND (? IS NULL OR id<?) ORDER BY id DESC LIMIT ?""",
                            (lock_path.name, before, before, limit)).fetchall()
        return current, [_metadata(row) for row in rows]


def get_revision(path, revision_id):
    slot = config_lock_path(path or Config.default_path()).name
    with _connection() as conn:
        row = conn.execute("SELECT * FROM revisions WHERE slot=? AND id=?", (slot, revision_id)).fetchone()
        if row is None:
            raise LookupError("Profile revision not found")
        return _metadata(row), json.loads(row["document"])
