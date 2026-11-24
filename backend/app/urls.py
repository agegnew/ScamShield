from functools import lru_cache
from urllib.parse import urlsplit

import tldextract

# Bundled public-suffix snapshot: offline and the same result on every machine.
_extract = tldextract.TLDExtract(suffix_list_urls=())


class InvalidURL(ValueError):
    pass


def normalize_url(raw: str) -> str:
    """Return an http(s) URL, adding http:// when the scheme is missing."""
    value = raw.strip()
    if not value:
        raise InvalidURL("empty URL")
    if "://" not in value:
        value = "http://" + value
    parts = urlsplit(value)
    if parts.scheme.lower() not in ("http", "https"):
        raise InvalidURL(f"unsupported scheme: {parts.scheme}")
    if not parts.hostname:
        raise InvalidURL("URL has no host")
    return value


def hostname(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


@lru_cache(maxsize=65536)
def registrable_domain(host: str) -> str:
    """'login.tamm-pay.co.uk' -> 'tamm-pay.co.uk'. Falls back to the host itself (IPs)."""
    parts = _extract(host)
    if parts.domain and parts.suffix:
        return f"{parts.domain}.{parts.suffix}"
    return host


def domain_label(host: str) -> str:
    """The name part of the registrable domain: 'tamm-pay.co.uk' -> 'tamm-pay'."""
    return _extract(host).domain or host
