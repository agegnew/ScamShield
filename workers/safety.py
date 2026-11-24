"""Refuse URLs that would make the fetcher reach private or internal hosts (SSRF guard)."""
import ipaddress
import socket
from urllib.parse import urlsplit

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {None, 80, 443, 8080, 8443}


class UnsafeURL(ValueError):
    pass


class Unresolvable(UnsafeURL):
    """The host has no DNS record: often a scam domain already taken down."""


def _is_public(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return addr.is_global and not addr.is_multicast


def resolve_public(host: str) -> list[str]:
    """Return the host's IPs; raise UnsafeURL if it does not resolve or any IP is non-public."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise Unresolvable(f"cannot resolve {host}") from exc
    ips = sorted({info[4][0] for info in infos})
    blocked = [ip for ip in ips if not _is_public(ip)]
    if blocked:
        raise UnsafeURL(f"{host} resolves to non-public address {blocked[0]}")
    return ips


def check_url(url: str) -> list[str]:
    """Validate scheme, credentials, port and destination. Returns the resolved IPs."""
    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURL(f"scheme {parts.scheme!r} not allowed")
    if parts.username or parts.password:
        raise UnsafeURL("credentials in URL")
    if parts.port not in ALLOWED_PORTS:
        raise UnsafeURL(f"port {parts.port} not allowed")
    if not parts.hostname:
        raise UnsafeURL("no host")
    return resolve_public(parts.hostname)
