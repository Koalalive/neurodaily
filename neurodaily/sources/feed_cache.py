"""Conditional HTTP cache for RSS/Atom feeds.

The feed body is small enough to keep locally. Sending ETag/Last-Modified
headers avoids re-downloading unchanged journal and policy feeds.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from ..config import DEFAULT_DIRS
from .http import get


def _cache_dir() -> Path:
    return Path(DEFAULT_DIRS["output"]) / "rss_cache"


def _cache_path(url: str) -> Path:
    return _cache_dir() / (hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json")


def _read(url: str) -> dict | None:
    try:
        data = json.loads(_cache_path(url).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("url") != url:
            return None
        body = data.get("body")
        if not isinstance(body, str):
            return None
        data["content"] = base64.b64decode(body)
        return data
    except (OSError, ValueError, TypeError):
        return None


def _write(url: str, response) -> None:
    try:
        headers = getattr(response, "headers", {}) or {}
        etag = headers.get("ETag", "")
        modified = headers.get("Last-Modified", "")
        if not etag and not modified:
            return
        path = _cache_path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "url": url,
            "etag": etag,
            "last_modified": modified,
            "body": base64.b64encode(response.content).decode("ascii"),
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
    except (OSError, ValueError, TypeError):
        pass


def fetch_feed(url: str, *, timeout: float, retries: int = 1,
               user_agent: str | None = None, untrusted_url: bool = True,
               getter=None) -> bytes | None:
    """Fetch a feed conditionally and return its bytes.

    A 304 response returns the cached body. Non-2xx responses return None and
    are recorded by the shared HTTP client.
    """
    cached = _read(url)
    headers = {}
    if cached:
        if cached.get("etag"):
            headers["If-None-Match"] = cached["etag"]
        if cached.get("last_modified"):
            headers["If-Modified-Since"] = cached["last_modified"]
    response = (getter or get)(url, timeout=timeout, retries=retries, user_agent=user_agent,
                               headers=headers or None, untrusted_url=untrusted_url)
    if response is None:
        return None
    status = getattr(response, "status_code", 200)
    if status == 304:
        return cached.get("content") if cached else None
    if status >= 400:
        return None
    _write(url, response)
    return response.content
