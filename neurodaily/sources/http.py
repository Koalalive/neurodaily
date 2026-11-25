"""Shared HTTP client helpers (retries, timeouts, headers)."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import BoundedSemaphore, Lock
import os
import time
import httpx
from urllib.parse import urlsplit

from ..security import allow_fake_ip_for_host, allow_private_sources, public_addresses, validate_http_url

DEFAULT_TIMEOUT = 20.0
DEFAULT_HEADERS = {
    "User-Agent": "NeuroDaily/0.1 (personal research digest; contact: local)",
}

try:
    _SOURCE_CONCURRENCY = max(1, min(64, int(os.environ.get("NEURODAILY_SOURCE_CONCURRENCY", "8"))))
except (TypeError, ValueError):
    _SOURCE_CONCURRENCY = 8
try:
    _HOST_CONCURRENCY = max(1, min(32, int(os.environ.get("NEURODAILY_HOST_CONCURRENCY", "8"))))
except (TypeError, ValueError):
    _HOST_CONCURRENCY = 8
_SOURCE_LIMIT = BoundedSemaphore(_SOURCE_CONCURRENCY)
_host_limits: dict[str, BoundedSemaphore] = {}
_host_limits_lock = Lock()


def _host_limit(url: str):
    try:
        host = urlsplit(url).hostname or ""
    except ValueError:
        host = ""
    with _host_limits_lock:
        return _host_limits.setdefault(host, BoundedSemaphore(_HOST_CONCURRENCY))


class _SourceBudgetExceeded(httpx.RequestError):
    def __init__(self, reason, request):
        super().__init__(reason, request=request)
        self.reason = reason


_request_budget = ContextVar("source_request_budget", default=None)


@contextmanager
def source_request_budget(reserve, remaining):
    """Attach an online trial's admission callbacks to its source GET requests."""
    token = _request_budget.set((reserve, remaining))
    try:
        yield
    finally:
        _request_budget.reset(token)


def _budget_source_get(request):
    budget = _request_budget.get()
    if request.method != "GET" or budget is None:
        return
    remaining, reason = budget[0]()
    if reason:
        raise _SourceBudgetExceeded(reason, request)
    stats = _capture.get()
    if stats is not None:
        with stats._lock:
            stats.request_count += 1
    request.extensions["timeout"] = {phase: min(remaining, value) if value is not None else remaining
                                     for phase, value in request.extensions.get("timeout", {}).items()}


_source_get_events = {"request": [_budget_source_get]}

_client = httpx.Client(timeout=DEFAULT_TIMEOUT, headers=DEFAULT_HEADERS,
                        follow_redirects=True, event_hooks=_source_get_events)


class _BlockedSource(httpx.RequestError):
    pass


class _SourceTransport(httpx.HTTPTransport):
    def __init__(self, *, allow_private: bool | None = None, **kwargs):
        super().__init__(**kwargs)
        self._allow_private = allow_private

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        # Apply the same policy to the initial request and every redirect. Use
        # the validated address for the connection while preserving TLS SNI.
        try:
            allow_private = allow_private_sources() if self._allow_private is None else self._allow_private
            validate_http_url(str(request.url), allow_private=allow_private, resolve=False)
            host = request.url.raw_host.decode("ascii")
            port = request.url.port or (443 if request.url.scheme == "https" else 80)
            addresses = public_addresses(host, port, allow_private,
                                         allow_fake_ip=allow_fake_ip_for_host(host, request.url.scheme))
        except ValueError as exc:
            raise _BlockedSource("Source destination blocked or unresolved", request=request) from exc
        for index, address in enumerate(addresses):
            outbound = httpx.Request(request.method, request.url.copy_with(host=address),
                                     headers=request.headers, stream=request.stream,
                                     extensions={**request.extensions, "sni_hostname": host})
            try:
                return super().handle_request(outbound)
            except (httpx.ConnectError, httpx.ConnectTimeout):
                if index == len(addresses) - 1:
                    raise
        raise _BlockedSource("No usable source destination", request=request)


# Different hosts may share one IP. Reusing a connection by IP would bypass
# hostname validation for the second host, so disable keep-alive here.
_source_client = httpx.Client(
    transport=_SourceTransport(limits=httpx.Limits(max_keepalive_connections=0)),
    timeout=DEFAULT_TIMEOUT, headers=DEFAULT_HEADERS, follow_redirects=True,
    max_redirects=10, trust_env=False, event_hooks=_source_get_events,
)


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
        accepted_statuses: tuple[int, ...] = (),
        headers: dict | None = None, *, untrusted_url: bool = False) -> httpx.Response | None:
    """Perform a GET with retry/backoff. Return None on final failure (never raises).

    ``connect_close=True`` forces a fresh one-shot connection (no connection pool)
    per request. Some APIs (ClinicalTrials.gov v2) return 403 on reused keep-alive
    connections, so sources hitting those should pass this.
    """
    stats = _capture.get()
    budget = _request_budget.get()
    if stats is not None and budget is None:
        with stats._lock:
            stats.request_count += 1
    request_headers = dict(headers or {})
    if user_agent:
        request_headers["User-Agent"] = user_agent
    kind, message = "failed", "HTTP request failed"
    for attempt in range(retries + 1):
        try:
            with _SOURCE_LIMIT, _host_limit(url):
                if untrusted_url:
                    resp = _source_client.get(url, params=params, timeout=timeout, headers=request_headers)
                elif connect_close:
                    fresh_headers = {**DEFAULT_HEADERS, **request_headers, "Connection": "close"}
                    with httpx.Client(timeout=timeout, headers=fresh_headers,
                                      follow_redirects=True, event_hooks=_source_get_events) as fresh:
                        resp = fresh.get(url, params=params, timeout=timeout)
                elif request_headers:
                    resp = _client.get(url, params=params, timeout=timeout,
                                       headers=request_headers)
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
        except _SourceBudgetExceeded as exc:
            record_failure(exc.reason, "budget")
            return None
        except httpx.TimeoutException:
            kind, message = "timeout", "HTTP request timed out"
            delay = backoff * (attempt + 1)
        except (_BlockedSource, httpx.InvalidURL, httpx.TooManyRedirects):
            record_failure("Source URL blocked, unresolved or invalid")
            return None
        except httpx.TransportError:
            kind, message = "failed", "HTTP transport failure"
            delay = backoff * (attempt + 1)
        if attempt < retries:
            if budget is not None and budget[1]() <= delay:
                record_failure("online_time_budget_exhausted", "budget")
                return None
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
