"""Shared HTTP client helpers (retries, timeouts, headers)."""
from __future__ import annotations

import time
import httpx

DEFAULT_TIMEOUT = 20.0
DEFAULT_HEADERS = {
    "User-Agent": "NeuroDaily/0.1 (personal research digest; contact: local)",
}

_client = httpx.Client(timeout=DEFAULT_TIMEOUT, headers=DEFAULT_HEADERS,
                        follow_redirects=True)


def get(url: str, params: dict | None = None, timeout: float = DEFAULT_TIMEOUT,
        retries: int = 2, backoff: float = 1.2, connect_close: bool = False,
        user_agent: str | None = None) -> httpx.Response | None:
    """Perform a GET with retry/backoff. Return None on final failure (never raises).

    ``connect_close=True`` forces a fresh one-shot connection (no connection pool)
    per request. Some APIs (ClinicalTrials.gov v2) return 403 on reused keep-alive
    connections, so sources hitting those should pass this.
    """
    last_err: Exception | None = None
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
            else:
                resp = _client.get(url, params=params, timeout=timeout)
            if resp.status_code < 400:
                return resp
            last_err = RuntimeError(f"HTTP {resp.status_code}")
            # 429 / 5xx -> backoff and retry
            if resp.status_code in (429,) or resp.status_code >= 500:
                time.sleep(backoff * (attempt + 1))
                continue
            return None  # 4xx (not transient) — don't retry
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last_err = e
            time.sleep(backoff * (attempt + 1))
    return None


def parse_date_any(value: str | None) -> str:
    if not value:
        return ""
    v = value.strip()
    if not v:
        return ""
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
