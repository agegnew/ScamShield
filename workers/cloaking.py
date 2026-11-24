"""Cloaking check: open the link again as a foreign desktop browser and compare with what a UAE phone saw.

Scam kits often show the real page only to local mobile visitors and a harmless page (or nothing) to everyone
else, so that crawlers and reviewers miss them. A difference is a signal, not proof: sites also localise.
"""
from urllib.parse import urlsplit

from workers.enrich import icann_domain
from workers.fetcher import fetch
from workers.fingerprint import hamming

# dHash distance above which two screenshots show clearly different pages.
DIFFERENT_PAGE_DISTANCE = 24


def _domain(url: str | None) -> str | None:
    host = urlsplit(url or "").hostname
    return icann_domain(host) if host else None


def compare(mobile: dict, desktop: dict) -> list[str]:
    signals = []
    if mobile["status"] == "ok" and desktop["status"] != "ok":
        signals.append("desktop_blocked")
    if mobile["status"] != "ok" or desktop["status"] != "ok":
        return signals
    if _domain(mobile["final_url"]) != _domain(desktop["final_url"]):
        signals.append("different_destination")
    mobile_sensitive = {k for f in mobile["forms"] for k in f["sensitive"]}
    desktop_sensitive = {k for f in desktop["forms"] for k in f["sensitive"]}
    if mobile_sensitive - desktop_sensitive:
        signals.append("forms_hidden_from_desktop")
    m_hash = (mobile["fingerprints"] or {}).get("screenshot_dhash")
    d_hash = (desktop["fingerprints"] or {}).get("screenshot_dhash")
    if m_hash and d_hash and hamming(m_hash, d_hash) > DIFFERENT_PAGE_DISTANCE and mobile["title"] != desktop["title"]:
        signals.append("different_page")
    return signals


def check(url: str, mobile: dict) -> dict:
    desktop = fetch(url, profile="desktop_us")
    return {
        "signals": compare(mobile, desktop),
        "desktop": {k: desktop[k] for k in ("status", "final_url", "http_status", "title", "screenshot_path",
                                            "fetch_error")},
    }
