"""Scam domains the browser extension blocks before the page loads (GET /api/blocklist).

A block replaces the whole site with a warning, so it needs more than a high score. A domain is
listed when an analyst confirmed its case, or when the engine rated it FRAUD on firm evidence nobody
dismissed: a phishing feed lists it, a security service already warns about it, the page itself
poses as the brand or copies its look, it pushes a remote-access app or APK, or the AI review is
confident it is a scam. A FRAUD rating from the address alone (a lookalike name the fetcher could
not open) or from an unusual URL with a login form is not enough: on 25 Nov 2026 that blocked the
hackathon's own submission site.

Never listed: official brand domains, government suffixes, popular sites and the shared hosts where
anyone can publish (sites.google.com, pages.dev itself): blocking those would block every honest
page on them. A scam *on* a platform (tamm-pay.pages.dev) is still listed.
"""

from .brands import official_brand_for_domain
from .engine.lists import USER_CONTENT_HOSTS, platform_of, top_domains
from .urls import registrable_domain

# Chrome allows an extension at most 1,000 regex blocking rules.
MAX_DOMAINS = 1000
GOV_SUFFIXES = (".gov.ae", ".abudhabi", ".dubai")
# Reason codes that back a block (engine/checks.py HARD_EVIDENCE plus a confirmed impersonation).
FIRM = {
    "threat_feed", "platform_warning", "brand_on_wrong_domain", "visual_match", "impersonation_confirmed",
    "remote_access", "app_download",
}
AI_SURE = 30  # ai_flagged weight when Claude was at least 85% sure


def firm_evidence(reasons: list[dict]) -> bool:
    """reasons: the verdict's reasons as stored (dicts with code and weight)."""
    for r in reasons:
        if r.get("code") in FIRM or (r.get("code") == "ai_flagged" and (r.get("weight") or 0) >= AI_SURE):
            return True
    return False


def blockable(host: str) -> bool:
    host = (host or "").lower().rstrip(".").removeprefix("www.")
    if not host or "." not in host or host.endswith(GOV_SUFFIXES):
        return False
    if official_brand_for_domain(host) is not None or host in USER_CONTENT_HOSTS:
        return False
    registrable = registrable_domain(host)
    platform = platform_of(host, registrable)
    if platform:
        return host != platform and host.endswith("." + platform)
    return registrable not in top_domains()
