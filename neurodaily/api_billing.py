"""Local, token-based estimates for actual model requests."""

from __future__ import annotations

from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, localcontext
import ipaddress
import json
from pathlib import Path
import re
import sqlite3
from threading import Lock
from urllib.parse import urlsplit, urlunsplit

from .config import DEFAULT_DIRS

PURPOSES = ("summary", "connection_test", "geolocation", "search_optimization", "other")
GEO_CONCURRENCY_DEFAULT = 4
_WRITE_LOCK = Lock()
_TOKEN_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "total_tokens")
_RATE_FIELDS = ("currency", "input", "output", "cached_input")
_RESPONSE_ID = re.compile(r"[A-Za-z0-9_.:-]{1,200}\Z")
_OPTIMIZATION_ID = re.compile(r"[0-9a-f]{32}\Z")
_PROFILE_REVISION = re.compile(r"[0-9a-f]{64}\Z")
_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY,
    called_at TEXT NOT NULL,
    purpose TEXT NOT NULL,
    run_id INTEGER,
    profile TEXT,
    base_url TEXT,
    model TEXT,
    status TEXT NOT NULL,
    http_status INTEGER,
    response_id TEXT,
    input_tokens INTEGER,
    cached_input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    currency TEXT,
    estimated_cost TEXT,
    rate TEXT
);
CREATE INDEX IF NOT EXISTS calls_date_idx ON calls(called_at DESC, id DESC);
CREATE TABLE IF NOT EXISTS optimization_calls (
    call_id INTEGER PRIMARY KEY REFERENCES calls(id),
    optimization_run_id TEXT NOT NULL, optimization_round INTEGER NOT NULL, profile_revision TEXT
);
CREATE INDEX IF NOT EXISTS optimization_calls_by_run ON optimization_calls(optimization_run_id, optimization_round);
"""


def _db_path() -> Path:
    return Path(DEFAULT_DIRS["output"]) / "api_billing.db"


@contextmanager
def _connection():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.row_factory = sqlite3.Row
        conn.executescript(_SCHEMA)
        yield conn


def _settings(conn=None) -> dict:
    row = conn.execute("SELECT data FROM settings WHERE id = 1").fetchone() if conn else None
    return json.loads(row["data"]) if row else {"rates": [], "geo_enabled": False}


def load_settings() -> dict:
    if not _db_path().is_file():
        return _settings()
    with _connection() as conn:
        return _settings(conn)


def _endpoint(value: str) -> tuple[str, str]:
    if not isinstance(value, str) or any(c.isspace() for c in value.strip()) or len(value) > 2048:
        raise ValueError("Invalid API base URL")
    parts = urlsplit(value.strip())
    host = parts.hostname
    if not host or parts.username is not None or parts.query or parts.fragment:
        raise ValueError("The API base URL must exclude credentials, queries, and fragments")
    if parts.scheme not in ("http", "https"):
        raise ValueError("The API base URL must use HTTPS or local HTTP")
    if parts.scheme == "http" and host != "localhost":
        try:
            is_loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            is_loopback = False
        if not is_loopback:
            raise ValueError("The API base URL must use HTTPS or local HTTP")
    default_port = 443 if parts.scheme == "https" else 80
    port = parts.port
    authority = f"[{host}]" if ":" in host else host
    if port is not None and port != default_port:
        authority += f":{port}"
    path = parts.path.rstrip("/").removesuffix("/chat/completions").rstrip("/")
    base_url = urlunsplit((parts.scheme, authority, path, "", ""))
    return base_url, f"{parts.scheme}://{authority}"


def _decimal_text(value: Decimal) -> str:
    if not value:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _rate_text(raw) -> str:
    if type(raw) not in (str, int, float) or len(str(raw)) > 64:
        raise ValueError("Prices must be finite, non-negative decimal values")
    try:
        value = Decimal(str(raw))
    except InvalidOperation:
        raise ValueError("Prices must be finite, non-negative decimal values") from None
    if not value.is_finite() or value < 0:
        raise ValueError("Prices must be finite, non-negative decimal values")
    if value and (value.adjusted() > 24 or value.as_tuple().exponent < -24):
        raise ValueError("Prices support up to 24 decimal places")
    return _decimal_text(value)


def _label(value, maximum=200) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        if value and len(value) <= maximum and value.isprintable():
            return value
    return None


def _validate_rates(rates) -> list[dict]:
    if not isinstance(rates, list) or len(rates) > 500:
        raise ValueError("Rates must be a list of up to 500 entries")
    result = []
    seen = set()
    for rate in rates:
        if not isinstance(rate, dict) or set(rate) - {"base_url", "model", *_RATE_FIELDS}:
            raise ValueError("Invalid model price entry")
        base_url, _ = _endpoint(rate.get("base_url"))
        model = _label(rate.get("model"))
        currency = rate.get("currency")
        if not model or not isinstance(currency, str) or not re.fullmatch(r"[A-Za-z]{3}", currency):
            raise ValueError("Specify a model and a three-letter currency code")
        key = base_url, model
        if key in seen:
            raise ValueError("This API base URL and model already have a price")
        seen.add(key)
        cached = rate.get("cached_input")
        result.append({"base_url": base_url, "model": model, "currency": currency.upper(),
                       "input": _rate_text(rate.get("input")), "output": _rate_text(rate.get("output")),
                       "cached_input": None if cached in (None, "") else _rate_text(cached)})
    return result


def save_settings(payload: dict) -> dict:
    """Apply a settings patch atomically. Prices are per million tokens."""
    if not isinstance(payload, dict) or set(payload) - {"rates", "geo_enabled", "geo_concurrency"}:
        raise ValueError("Invalid billing settings")
    patch = dict(payload)
    if "geo_enabled" in patch and not isinstance(patch["geo_enabled"], bool):
        raise ValueError("geo_enabled must be a boolean")
    if "geo_concurrency" in patch:
        value = patch["geo_concurrency"]
        if type(value) is not int or not 1 <= value <= 16:
            raise ValueError("geo_concurrency must be an integer from 1 to 16")
    if "rates" in patch:
        patch["rates"] = _validate_rates(patch["rates"])
    with _connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        settings = _settings(conn) | patch
        conn.execute("INSERT OR REPLACE INTO settings (id, data) VALUES (1, ?)",
                     (json.dumps(settings, ensure_ascii=False),))
        return settings


def price_for(base_url: str, model: str) -> dict | None:
    try:
        endpoint, _ = _endpoint(base_url)
    except ValueError:
        return None
    for rate in load_settings()["rates"]:
        if rate["base_url"] == endpoint and rate["model"] == model:
            return {key: rate[key] for key in _RATE_FIELDS}
    return None


def _integer(value, upper=10**15) -> int | None:
    return value if type(value) is int and 0 <= value <= upper else None


def _token_usage(raw) -> tuple[int | None, int | None, int | None, int | None]:
    usage = raw if isinstance(raw, dict) else {}

    def first(*values):
        return next((number for value in values if (number := _integer(value)) is not None), None)

    input_tokens = first(usage.get("prompt_tokens"), usage.get("input_tokens"))
    output_tokens = first(usage.get("completion_tokens"), usage.get("output_tokens"))
    hit = _integer(usage.get("prompt_cache_hit_tokens"))
    miss = _integer(usage.get("prompt_cache_miss_tokens"))
    if input_tokens is None and hit is not None and miss is not None:
        input_tokens = hit + miss
    details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details")
    cached_tokens = first(details.get("cached_tokens") if isinstance(details, dict) else None, hit)
    if input_tokens is not None:
        if cached_tokens is None and miss is not None and miss <= input_tokens:
            cached_tokens = input_tokens - miss
        if cached_tokens is not None and cached_tokens > input_tokens:
            cached_tokens = None
    total_tokens = first(usage.get("total_tokens"))
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    return input_tokens, cached_tokens, output_tokens, total_tokens


def _estimate(rate, input_tokens, cached_tokens, output_tokens) -> str | None:
    if rate is None or input_tokens is None or output_tokens is None:
        return None
    regular = Decimal(rate["input"])
    cached = regular if rate["cached_input"] is None else Decimal(rate["cached_input"])
    if cached_tokens is None and input_tokens and cached != regular:
        return None
    cached_tokens = cached_tokens or 0
    with localcontext() as ctx:
        ctx.prec = 96
        fee = ((input_tokens - cached_tokens) * regular + cached_tokens * cached +
               output_tokens * Decimal(rate["output"])) / 1_000_000
    return _decimal_text(fee)


def record_call(*, purpose, base_url, model, status, http_status=None, response_id=None, usage=None,
                run_id=None, profile=None, rate=None, called_at=None, optimization_context=None) -> None:
    try:
        _, origin = _endpoint(base_url)
    except ValueError:
        origin = None
    tokens = _token_usage(usage)
    cost = _estimate(rate, *tokens[:3])
    response_id = response_id if isinstance(response_id, str) and _RESPONSE_ID.fullmatch(response_id) else None
    now = called_at or datetime.now(timezone.utc)
    with _WRITE_LOCK, _connection() as conn:
        cursor = conn.execute("""INSERT INTO calls (called_at, purpose, run_id, profile, base_url, model,
                     status, http_status, response_id, input_tokens, cached_input_tokens, output_tokens,
                     total_tokens, currency, estimated_cost, rate)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                     (now.astimezone(timezone.utc).isoformat(), purpose if purpose in PURPOSES else "other",
                      _integer(run_id, 2**63 - 1), _label(profile), origin, _label(model), status,
                      _integer(http_status, 599), response_id, *tokens, rate["currency"] if rate else None,
                      cost, json.dumps(rate) if rate else None))
        if purpose == "search_optimization" and isinstance(optimization_context, dict):
            optimizer = optimization_context.get("run_id")
            round_number = optimization_context.get("round")
            revision = optimization_context.get("profile_revision")
            if isinstance(optimizer, str) and _OPTIMIZATION_ID.fullmatch(optimizer) and type(round_number) is int and 1 <= round_number <= 1000:
                if not isinstance(revision, str) or not _PROFILE_REVISION.fullmatch(revision):
                    revision = None
                conn.execute("INSERT INTO optimization_calls VALUES (?,?,?,?)", (cursor.lastrowid, optimizer, round_number, revision))


def _report(rows) -> dict:
    totals = dict.fromkeys(("calls", "successful_calls", "failed_calls", "usage_reported_calls",
                            "known_cost_calls", "unknown_cost_calls", *_TOKEN_FIELDS), 0)
    costs = {}
    with localcontext() as ctx:
        ctx.prec = 96
        for row in rows:
            totals["calls"] += 1
            totals["successful_calls" if row["status"] == "success" else "failed_calls"] += 1
            totals["usage_reported_calls"] += int(any(row[field] is not None for field in _TOKEN_FIELDS))
            for field in _TOKEN_FIELDS:
                totals[field] += row[field] or 0
            if row["estimated_cost"] is None:
                totals["unknown_cost_calls"] += 1
            else:
                totals["known_cost_calls"] += 1
                currency = row["currency"]
                costs[currency] = costs.get(currency, Decimal(0)) + Decimal(row["estimated_cost"])
    totals["cost_by_currency"] = {key: _decimal_text(value) for key, value in sorted(costs.items())}
    return totals


def billing_report(days=30, limit=100, offset=0, purpose=None, *, optimization_run_id=None) -> dict:
    if type(days) is not int or not 1 <= days <= 36500:
        raise ValueError("days must be between 1 and 36500")
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    if type(offset) is not int or not 0 <= offset < 2**63:
        raise ValueError("offset must be a non-negative integer")
    if purpose is not None and purpose not in PURPOSES:
        raise ValueError("Unknown request purpose")
    if optimization_run_id is not None and (not isinstance(optimization_run_id, str) or not _OPTIMIZATION_ID.fullmatch(optimization_run_id)):
        raise ValueError("Invalid optimization run ID")
    if not _db_path().is_file():
        return {"calls": [], "totals": _report(()), "total_calls": 0, "rounds": []}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    where = "WHERE called_at >= ?"
    params = (cutoff,)
    if purpose is not None:
        where += " AND purpose = ?"
        params += (purpose,)
    if optimization_run_id is not None:
        where += " AND optimization_run_id = ?"
        params += (optimization_run_id,)
    joined = f"FROM calls LEFT JOIN optimization_calls ON calls.id=optimization_calls.call_id {where}"
    with _connection() as conn:
        conn.execute("BEGIN")
        rows = conn.execute(f"SELECT * {joined} ORDER BY called_at DESC, id DESC LIMIT ? OFFSET ?",
                            (*params, limit, offset))
        calls = [{key: row[key] for key in row.keys() if key != "call_id"} | {
            "rate": json.loads(row["rate"]) if row["rate"] else None} for row in rows]
        totals = _report(conn.execute(f"SELECT * {joined}", params))
        rounds = []
        if optimization_run_id is not None:
            from itertools import groupby

            usage = conn.execute(f"SELECT * {joined} ORDER BY optimization_round", params)
            rounds = [{"round": number, **_report(records)}
                      for number, records in groupby(usage, key=lambda row: row["optimization_round"])]
    return {"calls": calls, "totals": totals, "total_calls": totals["calls"], "rounds": rounds}
