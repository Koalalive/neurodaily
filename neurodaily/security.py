"""Small network/security guards shared by the web app and sources."""
from __future__ import annotations

import ipaddress
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlsplit

LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def allow_private_sources() -> bool:
    """Local feeds/tests can opt in; production should keep this off."""
    return os.environ.get("NEURODAILY_ALLOW_PRIVATE_SOURCES") == "1"


def validate_http_url(value: str, *, allow_private: bool | None = None,
                     resolve: bool = True) -> str:
    """Validate an HTTP(S) URL and reject private/reserved destinations.

    DNS is resolved before the check, so a hostname such as
    ``internal.example`` pointing at 10.0.0.1 is rejected as well.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("URL is empty")
    url = value.strip()
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("URL must use http(s) with a host")
    if parts.username is not None or parts.password is not None:
        raise ValueError("URL must not contain embedded credentials")
    if allow_private is None:
        allow_private = allow_private_sources()
    hosts = {parts.hostname}
    if resolve:
        try:
            hosts = {info[4][0] for info in socket.getaddrinfo(parts.hostname, parts.port or 0,
                                                               type=socket.SOCK_STREAM)}
        except OSError as exc:
            raise ValueError(f"URL host cannot be resolved: {parts.hostname}") from exc
    for raw in hosts:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            if str(raw).casefold() in {"localhost", "localhost.localdomain"} and not allow_private:
                raise ValueError("URL points to localhost") from None
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            if not allow_private:
                raise ValueError("URL resolves to a private or reserved address")
    return url


def validate_label(value: str) -> str:
    if not isinstance(value, str) or not LABEL.fullmatch(value) or ".." in value:
        raise ValueError("invalid schedule label")
    return value


def within(root: str | os.PathLike, path: str | os.PathLike) -> bool:
    root_path = Path(root).resolve()
    target = Path(path).resolve()
    return target == root_path or root_path in target.parents
