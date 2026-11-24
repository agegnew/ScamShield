"""Known-phishing feeds (PhishTank, OpenPhish), kept in FEEDS_DIR.

The worker refreshes them every hour (refresh()); load() re-reads the files
whenever they change on disk, so the API sees new entries without a restart.

Exact URL match is strong evidence. Host match counts only for hosts that are
not shared platforms (one bad page on vercel.app says nothing about the rest).
"""

import csv
import logging
from dataclasses import dataclass, field
from functools import lru_cache

import httpx

from ..config import FEEDS_DIR
from ..urls import hostname

log = logging.getLogger("scamshield.feeds")

FEED_URLS = {
    "phishtank.csv": "http://data.phishtank.com/data/online-valid.csv",
    "openphish.txt": "https://openphish.com/feed.txt",
}
REFRESH_MINUTES = 60


@dataclass
class FeedIndex:
    urls: dict[str, str] = field(default_factory=dict)  # url -> feed name
    hosts: dict[str, str] = field(default_factory=dict)  # host -> feed name


def _norm(url: str) -> str:
    return url.strip().rstrip("/").lower()


def _mtimes() -> tuple[float, ...]:
    return tuple(
        (FEEDS_DIR / name).stat().st_mtime if (FEEDS_DIR / name).exists() else 0.0
        for name in FEED_URLS
    )


@lru_cache(maxsize=1)
def _load(_mtimes_key: tuple[float, ...]) -> FeedIndex:
    index = FeedIndex()

    def add(url: str, feed: str) -> None:
        index.urls.setdefault(_norm(url), feed)
        host = hostname(url if "://" in url else "http://" + url)
        if host:
            index.hosts.setdefault(host, feed)

    phishtank = FEEDS_DIR / "phishtank.csv"
    if phishtank.exists():
        with phishtank.open(encoding="utf-8", errors="ignore") as f:
            for row in csv.DictReader(f):
                if row.get("url"):
                    add(row["url"], "PhishTank")
    openphish = FEEDS_DIR / "openphish.txt"
    if openphish.exists():
        for line in openphish.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip():
                add(line, "OpenPhish")
    return index


def load() -> FeedIndex:
    return _load(_mtimes())


def refresh() -> None:
    """Download fresh copies; keep the old file if a download fails."""
    FEEDS_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        for name, url in FEED_URLS.items():
            try:
                body = client.get(url).raise_for_status().content
            except httpx.HTTPError as exc:
                log.warning("feed %s not refreshed: %s", name, exc)
                continue
            if body.strip():
                tmp = FEEDS_DIR / f"{name}.tmp"
                tmp.write_bytes(body)
                tmp.replace(FEEDS_DIR / name)
                log.info("feed %s refreshed (%d bytes)", name, len(body))


def lookup(url: str, host: str, shared_platform: bool) -> tuple[str, str] | None:
    """('url' | 'host', feed name) when the URL or its host is listed."""
    index = load()
    feed = index.urls.get(_norm(url))
    if feed:
        return "url", feed
    if not shared_platform and host in index.hosts:
        return "host", index.hosts[host]
    return None
