"""Scam domains the browser extension blocks before the page loads (GET /api/blocklist).

A domain is listed when an analyst confirmed its case, or the engine rated it FRAUD and nobody
dismissed it. Never listed: official brand domains, government suffixes, popular sites and the
shared hosts where anyone can publish (sites.google.com, pages.dev itself): blocking those would
block every honest page on them. A scam *on* a platform (tamm-pay.pages.dev) is still listed.
"""

from .brands import official_brand_for_domain
from .engine.lists import USER_CONTENT_HOSTS, platform_of, top_domains
from .urls import registrable_domain

# Chrome allows an extension at most 1,000 regex blocking rules.
MAX_DOMAINS = 1000
GOV_SUFFIXES = (".gov.ae", ".abudhabi", ".dubai")


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
