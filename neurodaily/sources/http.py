"""Shared HTTP client helpers (retries, timeouts, headers)."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Lock
import time
import httpx

DEFAULT_TIMEOUT = 20.0
DEFAULT_HEADERS = {
    "User-Agent": "NeuroDaily/0.1 (personal research digest; contact: local)",
}

_client = httpx.Client(timeout=DEFAULT_TIMEOUT, headers=DEFAULT_HEADERS,
                        follow_redirects=True)


@dataclass
class FetchDiagnostics:
    """Track transport and candidate coverage for one source execution."""

    request_count: int = 0
    candidate_count: int | None = None
    queries: list[str] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)
    batches: int = 0
    sampled: bool = False
    truncated: bool = False
    _lock: Lock = field(default_factory=Lock, repr=False)

    def as_dict(self, count: int) -> dict:
        kinds = {kind for kind, _ in self.errors}
        if self.errors:
            if count or self.batches:
                status = "partial"
            else:
                status = next((kind for kind in ("limited", "timeout") if kind in kinds), "failed")
        else:
            status = "ok" if count else "empty"
        return {
            "status": status,
            "ok": status in ("ok", "empty") or (status == "partial" and count > 0),
            "request_count": self.request_count,
            "request_errors": list(dict.fromkeys(message for _, message in self.errors)),
            "query": self.queries[0] if self.queries else "",
            "queries": self.queries.copy(),
            "candidate_count": self.candidate_count,
            "coverage": "partial" if self.errors else "sampled" if self.sampled else "full",
            "truncated": self.truncated,
        }


_capture: ContextVar[FetchDiagnostics | None] = ContextVar("source_fetch_diagnostics", default=None)


@contextmanager
def capture_requests():
    stats = FetchDiagnostics()
    token = _capture.set(stats)
    try:
        yield stats
    finally:
        _capture.reset(token)


def record_query(query: str) -> None:
    stats = _capture.get()
    if stats is not None and query:
        with stats._lock:
            if query not in stats.queries:
                stats.queries.append(query)


def record_candidates(count: int) -> None:
    stats = _capture.get()
    if stats is not None:
        with stats._lock:
            stats.batches += 1
            stats.candidate_count = (stats.candidate_count or 0) + count


def record_failure(message: str, kind: str = "failed") -> None:
    stats = _capture.get()
    if stats is not None:
        with stats._lock:
            stats.errors.append((kind, message))


def mark_sampled(*, truncated: bool = False) -> None:
    stats = _capture.get()
    if stats is not None:
        with stats._lock:
            stats.sampled = True
            stats.truncated |= truncated


def get(url: str, params: dict | None = None, timeout: float = DEFAULT_TIMEOUT,
        retries: int = 2, backoff: float = 1.2, connect_close: bool = False,
        user_agent: str | None = None,
        accepted_statuses: tuple[int, ...] = ()) -> httpx.Response | None:
    """Perform a GET with retry/backoff. Return None on final failure (never raises).

    ``connect_close=True`` forces a fresh one-shot connection (no connection pool)
    per request. Some APIs (ClinicalTrials.gov v2) return 403 on reused keep-alive
    connections, so sources hitting those should pass this.
    """
    stats = _capture.get()
    if stats is not None:
        with stats._lock:
            stats.request_count += 1
    kind, message = "failed", "HTTP request failed"
    for attempt in range(retries + 1):
        try:
            if connect_close:
                # one-shot client: avoid pooled keep-alive connections entirely
                headers = dict(DEFAULT_HEADERS)
                headers["Connection"] = "close"
                if user_agent:
                    headers["User-Agent"] = user_agent
                with httpx.Client(timeout=timeout, headers=headers,
                                  follow_redirects=True) as fresh:
                    resp = fresh.get(url, params=params, timeout=timeout)
            elif user_agent:
                resp = _client.get(url, params=params, timeout=timeout,
                                   headers={"User-Agent": user_agent})
            else:
                resp = _client.get(url, params=params, timeout=timeout)
            if resp.status_code < 400 or resp.status_code in accepted_statuses:
                return resp
            kind = "limited" if resp.status_code == 429 else "failed"
            message = f"HTTP {resp.status_code}"
            if resp.status_code < 500 and kind != "limited":
                break
            delay = backoff * (attempt + 1)
            retry_after = resp.headers.get("Retry-After", "")
            if retry_after.isdigit():
                delay = max(delay, int(retry_after))
                if delay > 5:
                    break
        except httpx.TimeoutException:
            kind, message = "timeout", "HTTP request timed out"
            delay = backoff * (attempt + 1)
        except httpx.TransportError:
            kind, message = "failed", "HTTP transport failure"
            delay = backoff * (attempt + 1)
        if attempt < retries:
            time.sleep(delay)
    record_failure(message, kind)
    return None


def parse_date_any(value: str | None) -> str:
    if not value:
        return ""
    v = value.strip()
    if not v:
        return ""
    # RFC 822 / RFC 2822 (e.g. "Mon, 10 Nov 2026 00:00:00 GMT")
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(v).strftime("%Y-%m-%d")
    except Exception:
        pass
    # handle common prefixes
    v = v.split("T")[0].split(" ")[0].replace(".000Z", "").replace("Z", "")
    if len(v) >= 10 and v[4] == "-":
        # YYYY-MM-DD likely
        pass
    # If it looks like DD Mon YYYY -> convert
    months = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05",
              "Jun": "06", "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10",
              "Nov": "11", "Dec": "12"}
    parts = v.split()
    if len(parts) == 3 and parts[1] in months:
        return f"{parts[2]}-{months[parts[1]]}-{parts[0]:0>2}"
    return v


def strip_html(value: str, keep_breaks: bool = False) -> str:
    """Strip HTML tags/entities from a blob into readable plain text.

    Used for RSS/news summaries and any source that returns markup, so the
    report shows clean content rather than raw ``<p>...``/``&amp;`` noise.
    """
    import html as _html
    import re as _re
    if not value:
        return ""
    # Decode entities first (e.g. &lt;span&gt; -> <span>) so tag-stripping catches
    # markup that was HTML-encoded by the feed. Unescape twice because some feeds
    # double-encode (e.g. &amp;#039;). Then strip tags.
    value = _html.unescape(_html.unescape(value))
    if keep_breaks:
        value = _re.sub(r"<br\s*/?>", "\n", value, flags=_re.I)
    value = _re.sub(r"<\/?[^>]+>", " ", value)
    value = _re.sub(r"\s+", " ", value).strip()
    return value
