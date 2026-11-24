"""SSRF guard: never let the worker open internal or private addresses.

Call assert_public_url() before every request the worker makes to a scanned
site, including every redirect hop (in Playwright: inside page.route()).
"""

import ipaddress
import socket
from urllib.parse import urlsplit

ALLOWED_PORTS = {80, 443, 8080, 8443}

_resolve = socket.getaddrinfo  # replaced in tests


class UnsafeURL(ValueError):
    pass


def assert_public_url(url: str) -> list[str]:
    """Return the host's public IPs, or raise UnsafeURL."""
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        raise UnsafeURL(f"scheme not allowed: {scheme or 'none'}")
    if parts.username or parts.password:
        raise UnsafeURL("credentials in URL")
    host = parts.hostname
    if not host:
        raise UnsafeURL("no host")
    try:
        port = parts.port or (443 if scheme == "https" else 80)
    except ValueError as exc:
        raise UnsafeURL("invalid port") from exc
    if port not in ALLOWED_PORTS:
        raise UnsafeURL(f"port not allowed: {port}")

    try:
        infos = _resolve(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as exc:
        raise UnsafeURL(f"cannot resolve {host}") from exc

    ips = sorted({info[4][0] for info in infos})
    if not ips:
        raise UnsafeURL(f"cannot resolve {host}")
    for ip in ips:
        addr = ipaddress.ip_address(ip.split("%")[0])
        if addr.version == 6 and addr.ipv4_mapped:
            addr = addr.ipv4_mapped
        if not addr.is_global or addr.is_multicast:
            raise UnsafeURL(f"{host} resolves to a non-public address {addr}")
    return ips
