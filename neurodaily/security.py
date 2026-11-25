"""Small network/security guards shared by the web app and sources."""
from __future__ import annotations

import ipaddress
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlsplit

LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def external_url(value: str | None) -> str:
    """Return a browser-safe HTTP(S) link without embedded credentials."""
    if not isinstance(value, str):
        return ""
    url = value.strip()
    if not url or any(char.isspace() or ord(char) < 32 or ord(char) == 127 or char == "\\"
                      for char in url):
        return ""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return ""
    if (parts.scheme not in {"http", "https"} or not parts.hostname
            or parts.username is not None or parts.password is not None or port == 0):
        return ""
    return url


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
    hosts = (parts.hostname,)
    if resolve:
        public_addresses(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80), allow_private)
    elif not allow_private:
        _check_public_addresses(hosts)
    return url


def public_addresses(host: str, port: int, allow_private: bool = False) -> tuple[str, ...]:
    try:
        addresses = tuple(dict.fromkeys(info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)))
    except OSError as exc:
        raise ValueError("Source host could not be resolved") from exc
    if not addresses:
        raise ValueError("Source host could not be resolved")
    if not allow_private:
        _check_public_addresses(addresses)
    return addresses


def _check_public_addresses(hosts) -> None:
    for raw in hosts:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            if raw.casefold().rstrip(".") in {"localhost", "localhost.localdomain"}:
                raise ValueError("URL points to localhost") from None
            continue
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_reserved or ip.is_multicast or getattr(ip, "is_site_local", False):
            raise ValueError("URL resolves to a private or reserved address")


def validate_label(value: str) -> str:
    if not isinstance(value, str) or not LABEL.fullmatch(value) or ".." in value:
        raise ValueError("invalid schedule label")
    return value


def within(root: str | os.PathLike, path: str | os.PathLike) -> bool:
    root_path = Path(root).resolve()
    target = Path(path).resolve()
    return target == root_path or root_path in target.parents
