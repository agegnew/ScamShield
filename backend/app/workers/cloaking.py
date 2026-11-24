"""Cloaking check (Simon): open the link again as a foreign desktop browser and compare with what a
UAE phone saw.

Scam kits often show the real page only to local mobile visitors and a harmless page (or nothing)
to everyone else, so crawlers and reviewers miss them. A difference is a signal, not proof: sites
also localise.
"""

from urllib.parse import urlsplit

from ..contracts import CloakingCheck, DesktopVisit, Evidence
from . import fetcher
from .enrich import icann_domain
from .fingerprint import hamming

# dHash distance above which two screenshots show clearly different pages.
DIFFERENT_PAGE_DISTANCE = 24


def _domain(url: str | None) -> str | None:
    host = urlsplit(url or "").hostname
    return icann_domain(host) if host else None


def compare(mobile: Evidence, desktop: Evidence) -> list[str]:
    signals = []
    if mobile.fetch_error is None and desktop.fetch_error is not None:
        signals.append("desktop_blocked")
    if mobile.fetch_error or desktop.fetch_error:
        return signals
    if _domain(mobile.final_url) != _domain(desktop.final_url):
        signals.append("different_destination")
    mobile_sensitive = {k for f in mobile.forms for k in f.sensitive}
    desktop_sensitive = {k for f in desktop.forms for k in f.sensitive}
    if mobile_sensitive - desktop_sensitive:
        signals.append("forms_hidden_from_desktop")
    m_hash = mobile.fingerprints.screenshot_dhash if mobile.fingerprints else None
    d_hash = desktop.fingerprints.screenshot_dhash if desktop.fingerprints else None
    if m_hash and d_hash and hamming(m_hash, d_hash) > DIFFERENT_PAGE_DISTANCE and mobile.title != desktop.title:
        signals.append("different_page")
    return signals


def check(url: str, mobile: Evidence) -> CloakingCheck:
    desktop = fetcher.fetch(url, profile="desktop_us")
    return CloakingCheck(
        signals=compare(mobile, desktop),
        desktop=DesktopVisit(
            final_url=desktop.final_url,
            http_status=desktop.http_status,
            title=desktop.title,
            screenshot_path=desktop.screenshot_path,
            fetch_error=desktop.fetch_error,
        ),
    )
