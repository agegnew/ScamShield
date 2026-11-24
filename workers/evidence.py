"""Build one Evidence record per URL: what the page showed (fetcher) plus who owns and hosts it (enrichment).

Enrichment runs even when the page is offline, so dead scam links still carry domain evidence.
"""
from urllib.parse import urlsplit

from workers.enrich import enrich
from workers.fetcher import fetch


def collect(url: str) -> dict:
    page = fetch(url)
    if page["status"] == "blocked":
        return {**page, "rdap": None, "ip": None, "asn": None, "hosting_org": None}

    target = page["final_url"] or url
    infra = enrich(target)
    evidence = {
        **page,
        "domain": infra["domain"],
        "registered_domain": infra["registered_domain"],
        "shared_hosting": infra["shared_hosting"],
        "rdap": infra["rdap"],
        "dns": infra["dns"],
        "ip": infra["ip"],
        "asn": infra["asn"],
        "hosting_org": infra["hosting_org"],
        "hosting_country": infra["hosting_country"],
    }
    if urlsplit(target).hostname != urlsplit(url).hostname:
        origin = enrich(url)
        evidence["origin"] = {k: origin[k] for k in ("domain", "registered_domain", "shared_hosting", "rdap", "ip",
                                                   "hosting_org")}
    return evidence
