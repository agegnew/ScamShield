from urllib.parse import urlsplit


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
    return (urlsplit(url).hostname or "").lower().rstrip(".")
