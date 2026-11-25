"""Small network/security guards shared by the web app and sources."""
from __future__ import annotations

import ipaddress
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlsplit

LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
# Mihomo/Clash fake-IP pools use this benchmark range. It is not a private
# network, but it is intentionally not globally routable. Permit it only for
# an explicit list of official public feed hosts.
_FAKE_IP_NETWORK = ipaddress.ip_network("198.18.0.0/15")
_TRUSTED_FEED_SUFFIXES = (
    "nature.com", "science.org", "cell.com", "thelancet.com",
    "psychiatryonline.org", "fda.gov", "jamanetwork.com",
    "elifesciences.org", "sciencedirect.com", "neurology.org",
    "pnas.org", "sciencedaily.com", "sciencenews.org", "chinanews.com.cn",
)


def trusted_fake_ip_host(host: str | None) -> bool:
    """Whether a host is one of the known official public feed hosts."""
    normalized = (host or "").strip().casefold().rstrip(".")
    return any(normalized == suffix or normalized.endswith("." + suffix)
               for suffix in _TRUSTED_FEED_SUFFIXES)


def allow_fake_ip_for_host(host: str | None, scheme: str = "https") -> bool:
    """Allow proxy fake-IP for public HTTPS hostnames.

    A fake-IP is not a real destination address: TLS still verifies the
    original hostname and the proxy remains the only route. Never allow it for
    localhost, private suffixes, IP literals, or plain HTTP.
    """
    if os.environ.get("NEURODAILY_ALLOW_FAKE_IP", "1") == "0":
        return False
    normalized = (host or "").strip().casefold().rstrip(".")
    if not normalized or "." not in normalized or scheme not in {"https", "http"}:
        return False
    if scheme == "http" and not trusted_fake_ip_host(normalized):
        return False
    if normalized in {"localhost", "localhost.localdomain"} or normalized.endswith((".local", ".lan", ".internal", ".arpa")):
        return False
    try:
        ipaddress.ip_address(normalized)
        return False
    except ValueError:
        pass
    return True


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
                     resolve: bool = True, allow_fake_ip: bool = False) -> str:
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
        public_addresses(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80),
                         allow_private, allow_fake_ip=allow_fake_ip)
    elif not allow_private:
        _check_public_addresses(hosts)
    return url


def public_addresses(host: str, port: int, allow_private: bool = False,
                     *, allow_fake_ip: bool = False) -> tuple[str, ...]:
    allow_fake_ip = allow_fake_ip and allow_fake_ip_for_host(host)
    try:
        addresses = tuple(dict.fromkeys(info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)))
    except OSError as exc:
        raise ValueError("Source host could not be resolved") from exc
    if not addresses:
        raise ValueError("Source host could not be resolved")
    if not allow_private:
        _check_public_addresses(addresses, allow_fake_ip=allow_fake_ip)
    return addresses


def _check_public_addresses(hosts, *, allow_fake_ip: bool = False) -> None:
    for raw in hosts:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            if raw.casefold().rstrip(".") in {"localhost", "localhost.localdomain"}:
                raise ValueError("URL points to localhost") from None
            continue
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if allow_fake_ip and ip in _FAKE_IP_NETWORK:
            continue
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
