"""Search locally saved reports, or an explicitly configured OpenSearch index."""

from __future__ import annotations

import base64
from contextlib import closing
from dataclasses import replace
from html.parser import HTMLParser
from http.client import HTTPException
import ipaddress
import json
import os
from pathlib import Path
import re
import sqlite3
import unicodedata
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .config import DEFAULT_DIRS
from .digest import DigestResult, _SECTION_BY_KIND
from .records import record_ids

ARCHIVE_KINDS = tuple(_SECTION_BY_KIND)
_RETURN_FIELDS = ("title", "url", "kind", "source", "date", "summary", "run_id", "stage", "record_id")
_CJK = re.compile(r"([\u2e80-\u2eff\u3040-\u30ff\u31f0-\u31ff\u3400-\u9fff\uac00-\ud7af\uf900-\ufaff"
                  r"\U00020000-\U000323af]+)")
_WORDS = re.compile(r"[^\W_]+")
_PHRASES = re.compile(r'"([^"]+)"|([^\"]+)')
_SECRET_QUERY_KEYS = {"access_token", "api_key", "apikey", "authorization", "client_secret", "password",
                      "refresh_token", "signature", "token", "x_amz_credential", "x_amz_security_token",
                      "x_amz_signature", "x_goog_credential", "x_goog_signature"}


class ArchiveSearchError(RuntimeError):
    """A selected search backend is unavailable or returned unusable results."""


class _PlainText(HTMLParser):
    _IGNORED = {"script", "style", "template"}
    _BREAKS = {"br", "div", "li", "p", "td", "tr", "section"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = []

    def handle_starttag(self, tag, _attrs):
        if tag in self._IGNORED:
            self.ignored.append(tag)
        elif tag in self._BREAKS and not self.ignored:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if self.ignored and tag == self.ignored[-1]:
            self.ignored.pop()
        elif tag in self._BREAKS and not self.ignored:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def _text(value, limit) -> str:
    if not isinstance(value, str):
        return ""
    parser = _PlainText()
    try:
        parser.feed(value[:limit * 4])
        parser.close()
    except (AssertionError, ValueError):
        return ""
    return " ".join("".join(parser.parts).replace("\x00", " ").split())[:limit]


def _url(value) -> str:
    if not isinstance(value, str) or len(value) > 4096 or any(c.isspace() or not c.isprintable() for c in value):
        return ""
    try:
        parsed = urlsplit(value)
        _ = parsed.port
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username is not None:
            return ""
        if any(key.casefold().replace("-", "_") in _SECRET_QUERY_KEYS for key, _ in parse_qsl(parsed.query)):
            return ""
    except ValueError:
        return ""
    return value


def _fold(value):
    return unicodedata.normalize("NFKC", value).casefold()


def _pieces(value):
    for index, part in enumerate(_CJK.split(_fold(value))):
        if index % 2:
            yield tuple(part)
        else:
            yield from ((word,) for word in _WORDS.findall(part))


def _tokens(value):
    return " ".join(word for group in _pieces(value) for word in group)


def _query_terms(query):
    groups = []
    for quoted, plain in _PHRASES.findall(query):
        if quoted:
            phrase = tuple(_tokens(quoted).split())
            if phrase:
                groups.append(phrase)
        else:
            groups.extend(_pieces(plain))
    return tuple(dict.fromkeys(groups))


def _profile(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 200 or not value.isprintable():
        raise ValueError("Invalid archive profile")
    return value


def _run_id(value):
    return value if type(value) is int and 0 < value < 2**63 else None


def _identifier(value):
    if isinstance(value, str) and value.startswith("url:"):
        return f"url:{url}" if (url := _url(value[4:])) else ""
    return _text(value, 600)


def _result_row(value):
    if not isinstance(value, dict) or value.get("kind") not in ARCHIVE_KINDS:
        return None
    title = _text(value.get("title"), 700)
    if not title:
        return None
    return {"title": title, "url": _url(value.get("url")), "kind": value["kind"],
            "source": _text(value.get("source"), 160), "date": _text(value.get("date"), 80),
            "summary": _text(value.get("summary"), 16000), "run_id": _run_id(value.get("run_id")),
            "stage": _text(value.get("stage"), 240), "record_id": _identifier(value.get("record_id"))}


def _stage(extra):
    parts = []
    for key in ("phase", "stage", "overall_status", "status"):
        value = extra.get(key)
        for entry in value if isinstance(value, (tuple, list)) else (value,):
            if text := _text(entry, 80):
                parts.append(text)
    return " · ".join(dict.fromkeys(parts))[:240]


def _archive_item(item, run_id):
    extra = item.extra if isinstance(item.extra, dict) else {}
    row = _result_row({"title": item.title, "url": item.url, "kind": item.kind, "source": item.source,
                       "date": item.date, "summary": item.summary, "run_id": run_id, "stage": _stage(extra)})
    if row is None:
        return None
    safe_item = replace(item, url=row["url"], title=row["title"], source=row["source"],
                        doi=_text(item.doi, 600), extra=extra)
    aliases = record_ids(safe_item)
    row["record_id"] = aliases[0]
    metadata = [row["source"], row["kind"], row["stage"], *aliases]
    extra_ids = extra.get("record_ids")
    if isinstance(extra_ids, (list, tuple)):
        metadata.extend(_identifier(value) for value in extra_ids[:30])
    for field in (item.authors, item.tags):
        if isinstance(field, (tuple, list)):
            metadata.extend(_text(value, 200) for value in field[:100])
    return row, _tokens(row["title"]), _tokens(row["summary"]), _tokens(" ".join(metadata))


_SCHEMA = """
CREATE TABLE IF NOT EXISTS archive_records (
    id INTEGER PRIMARY KEY,
    profile TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    kind TEXT NOT NULL,
    source TEXT NOT NULL,
    date TEXT NOT NULL,
    summary TEXT NOT NULL,
    run_id INTEGER,
    stage TEXT NOT NULL,
    record_id TEXT NOT NULL,
    title_terms TEXT NOT NULL,
    summary_terms TEXT NOT NULL,
    metadata_terms TEXT NOT NULL,
    fts_synced INTEGER NOT NULL DEFAULT 0,
    UNIQUE (profile, kind, record_id)
);
CREATE INDEX IF NOT EXISTS archive_profile_kind ON archive_records(profile, kind);
CREATE INDEX IF NOT EXISTS archive_pending ON archive_records(fts_synced) WHERE fts_synced = 0;
"""


def _db_path():
    return Path(DEFAULT_DIRS["output"]) / "archive.db"


def _connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _sync_fts(conn):
    existed = conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'archive_fts'").fetchone()
    try:
        conn.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS archive_fts USING fts5(
                        title_terms, summary_terms, metadata_terms,
                        tokenize='unicode61 remove_diacritics 2')""")
        conn.execute("SELECT rowid FROM archive_fts LIMIT 0")
    except sqlite3.OperationalError as error:
        if "no such module: fts5" not in str(error).lower():
            raise
        return False
    if not existed:
        conn.execute("UPDATE archive_records SET fts_synced = 0")
    if conn.execute("SELECT 1 FROM archive_records WHERE fts_synced = 0 LIMIT 1").fetchone():
        conn.execute("DELETE FROM archive_fts WHERE rowid IN (SELECT id FROM archive_records WHERE fts_synced = 0)")
        conn.execute("""INSERT INTO archive_fts (rowid, title_terms, summary_terms, metadata_terms)
                     SELECT id, title_terms, summary_terms, metadata_terms FROM archive_records WHERE fts_synced = 0""")
        conn.execute("UPDATE archive_records SET fts_synced = 1 WHERE fts_synced = 0")
    return True


def index_report(result: DigestResult) -> None:
    """Upsert the records in one saved report without any remote requests."""
    if result.skipped:
        return
    profile = _profile(result.config_profile)
    values = []
    for item in result.items:
        indexed = _archive_item(item, result.history_id)
        if indexed is not None:
            row, *terms = indexed
            values.append((profile, *(row[key] for key in _RETURN_FIELDS), *terms))
    if not values:
        return
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(_connect(path)) as conn, conn:
        conn.executescript(_SCHEMA)
        conn.execute("BEGIN IMMEDIATE")
        conn.executemany("""INSERT INTO archive_records (profile, title, url, kind, source, date, summary,
                         run_id, stage, record_id, title_terms, summary_terms, metadata_terms)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                         ON CONFLICT(profile, kind, record_id) DO UPDATE SET
                           title = excluded.title, url = COALESCE(NULLIF(excluded.url, ''), archive_records.url),
                           source = excluded.source,
                           date = COALESCE(NULLIF(excluded.date, ''), archive_records.date),
                           summary = COALESCE(NULLIF(excluded.summary, ''), archive_records.summary),
                           run_id = COALESCE(excluded.run_id, archive_records.run_id),
                           stage = COALESCE(NULLIF(excluded.stage, ''), archive_records.stage),
                           title_terms = excluded.title_terms,
                           summary_terms = COALESCE(NULLIF(excluded.summary_terms, ''), archive_records.summary_terms),
                           metadata_terms = excluded.metadata_terms, fts_synced = 0
                         WHERE archive_records.run_id IS NULL OR excluded.run_id >= archive_records.run_id""",
                         values)
        _sync_fts(conn)


def _fallback_text(value):
    return " " + "".join(c for c in unicodedata.normalize("NFD", value) if not unicodedata.combining(c)) + " "


def _fallback_search(conn, where, parameters, groups, exact, limit):
    phrases = [_fallback_text(" ".join(group)) for group in groups]
    matches = []
    for row in conn.execute(f"SELECT * FROM archive_records AS r {where}", parameters):
        title, summary, metadata = (_fallback_text(row[field])
                                    for field in ("title_terms", "summary_terms", "metadata_terms"))
        if all(phrase in title or phrase in summary or phrase in metadata for phrase in phrases):
            score = sum(5 * (phrase in title) + 2 * (phrase in metadata) + (phrase in summary) for phrase in phrases)
            matches.append(((row["title_terms"] == exact, score, row["date"], row["id"]), row))
    matches.sort(key=lambda match: match[0], reverse=True)
    return [row for _, row in matches[:limit]]


def _local_search(query, profile, kind, limit):
    path = _db_path()
    groups = _query_terms(query)
    if not groups or not path.is_file():
        return []
    where = "WHERE r.profile = ?"
    parameters = (profile,)
    if kind is not None:
        where += " AND r.kind = ?"
        parameters += (kind,)
    exact = _tokens(query)
    try:
        with closing(_connect(path)) as conn, conn:
            if not _sync_fts(conn):
                rows = _fallback_search(conn, where, parameters, groups, exact, limit)
            else:
                expression = " AND ".join('"' + " ".join(group) + '"' for group in groups)
                rows = conn.execute(f"""SELECT r.* FROM archive_fts
                                    JOIN archive_records r ON r.id = archive_fts.rowid
                                    {where} AND archive_fts MATCH ?
                                    ORDER BY r.title_terms = ? DESC, bm25(archive_fts, 5.0, 1.0, 2.0),
                                             r.date DESC, r.id DESC LIMIT ?""",
                                    (*parameters, expression, exact, limit)).fetchall()
            return [{field: row[field] for field in _RETURN_FIELDS} for row in rows]
    except sqlite3.Error as error:
        raise ArchiveSearchError("Could not read the local archive") from error


_OS_PREFIX = "NEURODAILY_OPENSEARCH_"
_IDENTIFIER = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9._-]{0,199}\Z")
_INDEX = re.compile(r"[a-z0-9][a-z0-9._-]{0,199}\Z")
_MAX_RESPONSE = 8 * 1024 * 1024


def _opensearch_config():
    base, index, pipeline, model = (os.environ.get(_OS_PREFIX + key, "").strip()
                                    for key in ("URL", "INDEX", "PIPELINE", "MODEL_ID"))
    if not all((base, index, pipeline, model)):
        raise ArchiveSearchError("OpenSearch requires URL, INDEX, PIPELINE, and MODEL_ID settings")
    user = os.environ.get(_OS_PREFIX + "USERNAME", "")
    password = os.environ.get(_OS_PREFIX + "PASSWORD", "")
    try:
        endpoint = urlsplit(base)
        host = endpoint.hostname
        _ = endpoint.port
        loopback = host == "localhost"
        if host and not loopback and endpoint.scheme == "http":
            loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        raise ArchiveSearchError("Invalid OpenSearch endpoint") from None
    if (not host or endpoint.username is not None or endpoint.query or endpoint.fragment
            or endpoint.scheme not in ("http", "https") or endpoint.scheme == "http" and not loopback
            or any(c.isspace() or not c.isprintable() for c in base)):
        raise ArchiveSearchError("Use an HTTPS or local HTTP OpenSearch URL without embedded credentials")
    if not _INDEX.fullmatch(index) or not _IDENTIFIER.fullmatch(pipeline) or not _IDENTIFIER.fullmatch(model):
        raise ArchiveSearchError("Invalid OpenSearch index, pipeline, or model identifier")
    if bool(user) != bool(password) or ":" in user:
        raise ArchiveSearchError("Supply both OpenSearch USERNAME and PASSWORD for basic authentication")
    return base.rstrip("/"), index, pipeline, model, user, password


def opensearch_configured() -> bool:
    try:
        _opensearch_config()
    except ArchiveSearchError:
        return False
    return True


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, _request, _fp, _code, _message, _headers, _new_url):
        return None


def _opensearch(query, profile, kind, limit):
    base, index, pipeline, model, user, password = _opensearch_config()
    filters = [{"term": {"profile": profile}}]
    if kind is not None:
        filters.append({"term": {"kind": kind}})
    body = {"size": limit, "_source": [*_RETURN_FIELDS, "profile"], "query": {"hybrid": {
        "filter": {"bool": {"filter": filters}},
        "queries": [
            {"multi_match": {"query": query, "fields": ["title^3", "summary"]}},
            {"neural": {"embedding": {"query_text": query, "model_id": model, "k": limit}}},
        ],
    }}}
    parameters = urlencode({"search_pipeline": pipeline, "allow_partial_search_results": "false"})
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if user:
        credentials = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
        headers["Authorization"] = f"Basic {credentials}"
    request = Request(f"{base}/{index}/_search?{parameters}", data=json.dumps(body).encode(),
                      headers=headers, method="POST")
    try:
        with build_opener(_NoRedirect()).open(request, timeout=8) as response:
            payload = response.read(_MAX_RESPONSE + 1)
    except HTTPError as error:
        error.close()
        raise ArchiveSearchError(f"OpenSearch returned HTTP {error.code}") from None
    except (OSError, HTTPException):
        raise ArchiveSearchError("Could not connect to OpenSearch") from None
    if len(payload) > _MAX_RESPONSE:
        raise ArchiveSearchError("OpenSearch returned an oversized response")
    try:
        data = json.loads(payload)
        hits = data["hits"]["hits"]
        if not isinstance(hits, list):
            raise TypeError("invalid hits")
        if data.get("timed_out") or data.get("_shards", {}).get("failed"):
            raise ArchiveSearchError("OpenSearch returned an incomplete search")
    except (AttributeError, KeyError, RecursionError, TypeError, ValueError):
        raise ArchiveSearchError("OpenSearch returned an invalid result") from None
    results = []
    for hit in hits[:limit]:
        source = hit.get("_source") if isinstance(hit, dict) else None
        if not isinstance(source, dict) or source.get("profile") != profile:
            continue
        if kind is not None and source.get("kind") != kind:
            continue
        if row := _result_row(source):
            results.append(row)
    return results


def search_archive(query, *, profile: str, kind: str | None = None, limit: int = 30, backend: str = "local") -> dict:
    profile = _profile(profile)
    if not isinstance(query, str) or len(query) > 500:
        raise ValueError("Enter search text of up to 500 characters")
    if kind is not None and kind not in ARCHIVE_KINDS:
        raise ValueError("Unknown archive document kind")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Archive limit must be between 1 and 100")
    if backend not in ("local", "opensearch"):
        raise ValueError("Unknown archive search backend")
    query = query.strip()
    if not query:
        results = []
    elif backend == "local":
        results = _local_search(query, profile, kind, limit)
    else:
        results = _opensearch(query, profile, kind, limit)
    return {"backend": backend, "results": results, "total": len(results)}
