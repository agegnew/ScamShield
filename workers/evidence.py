"""Build one Evidence record per URL (backend/app/contracts.py Evidence plus extra fields the engine may use):
what the page showed (fetcher) and who owns and hosts it (enrichment).

Enrichment runs even when the page is offline, so dead scam links still carry domain evidence.
The cloaking check (a second, desktop visit) runs only for live pages on non-official hosts.
"""
import os
from urllib.parse import urlsplit

from workers import brands
from workers.cloaking import check as cloaking_check
from workers.enrich import enrich
from workers.fetcher import fetch
from workers.references import visual_match


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
        "hosting_abuse_email": infra["hosting_abuse_email"],
        "visual_match": visual_match(page["final_url"], page["fingerprints"]),
        "cloaking": None,
    }
    if page["status"] == "ok" and os.environ.get("SCAMSHIELD_CLOAK_CHECK", "1") == "1" \
            and not brands.is_official(urlsplit(target).hostname or ""):
        evidence["cloaking"] = cloaking_check(url, page)
    if urlsplit(target).hostname != urlsplit(url).hostname:
        origin = enrich(url)
        evidence["origin"] = {k: origin[k] for k in ("domain", "registered_domain", "shared_hosting", "rdap", "ip",
                                                   "hosting_org")}
    return evidence
