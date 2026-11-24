"""Who owns and hosts a domain: RDAP/WHOIS registration, DNS, IP, ASN and hosting provider.

Usage: python -m workers.enrich https://example.com/path
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

import dns.resolver
import requests
import tldextract

RDAP_URL = "https://rdap.org/domain/{}"
TIMEOUT = 10
# .ae and a few other ccTLDs have no RDAP; their registry WHOIS is queried directly.
WHOIS_SERVERS = {"ae": "whois.aeda.net.ae"}

_extract = tldextract.TLDExtract(suffix_list_urls=(), include_psl_private_domains=True)


def registrable_domain(url_or_host: str) -> str:
    """The domain a registrant controls. For tenant hosts (foo.pages.dev) this is the tenant, not the platform."""
    host = urlsplit(url_or_host).hostname if "://" in url_or_host else url_or_host
    return _extract(host).top_domain_under_public_suffix or host


def icann_domain(host: str) -> str:
    """The domain registered with a registrar (pages.dev for foo.pages.dev)."""
    return _extract(host, include_psl_private_domains=False).top_domain_under_public_suffix or host


def _vcard(entity: dict, field: str) -> str | None:
    for entry in (entity.get("vcardArray") or [None, []])[1]:
        if entry[0] == field and entry[3]:
            return entry[3]
    return None


def _rdap(domain: str) -> dict | None:
    resp = requests.get(RDAP_URL.format(domain), timeout=TIMEOUT, headers={"Accept": "application/rdap+json"})
    if resp.status_code != 200:
        return None
    data = resp.json()
    events = {e["eventAction"]: e["eventDate"] for e in data.get("events", [])}
    registrar, abuse_email = None, None
    for entity in data.get("entities", []):
        if "registrar" in entity.get("roles", []):
            registrar = _vcard(entity, "fn")
            for sub in entity.get("entities", []):
                if "abuse" in sub.get("roles", []):
                    abuse_email = _vcard(sub, "email")
    return {
        "source": "rdap",
        "created": events.get("registration"),
        "expires": events.get("expiration"),
        "registrar": registrar,
        "abuse_email": abuse_email,
        "status": data.get("status", []),
    }


def _whois(domain: str, server: str) -> dict | None:
    out = subprocess.run(["whois", "-h", server, domain], capture_output=True, text=True, timeout=TIMEOUT).stdout
    if not out or re.search(r"no match|not found|no data", out, re.I):
        return None
    field = lambda name: (m.group(1).strip() if (m := re.search(rf"^{name}:\s*(.+)$", out, re.I | re.M)) else None)
    return {
        "source": f"whois:{server}",
        "created": field("Creation Date") or field("Created"),
        "expires": field("Expiry Date") or field("Registry Expiry Date"),
        "registrar": field("Registrar Name") or field("Registrar"),
        "abuse_email": field("Registrar Abuse Contact Email"),
        "status": [s for s in [field("Status")] if s],
    }


def registration(domain: str) -> dict:
    tld = domain.rsplit(".", 1)[-1]
    try:
        info = _whois(domain, WHOIS_SERVERS[tld]) if tld in WHOIS_SERVERS else _rdap(domain)
    except (requests.RequestException, subprocess.TimeoutExpired, ValueError):
        info = None
    if not info:
        return {"source": None, "registered": False, "created": None, "age_days": None,
                "registrar": None, "abuse_email": None}
    created = info.get("created")
    age_days = None
    if created:
        try:
            age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(created.replace("Z", "+00:00"))).days
        except ValueError:
            pass
    return {**info, "registered": True, "age_days": age_days}


def _records(name: str, rtype: str) -> list[str]:
    try:
        return sorted(r.to_text().strip('"') for r in dns.resolver.resolve(name, rtype, lifetime=TIMEOUT))
    except (dns.exception.DNSException, ValueError):
        return []


def asn(ip: str) -> dict:
    """IPv4 to ASN and owner through Team Cymru's free DNS service."""
    if ":" in ip:
        return {"asn": None, "asn_org": None, "country": None}
    origin = _records(".".join(reversed(ip.split("."))) + ".origin.asn.cymru.com", "TXT")
    if not origin:
        return {"asn": None, "asn_org": None, "country": None}
    number, _, country, *_ = [p.strip() for p in origin[0].split("|")]
    number = number.split()[0]
    desc = _records(f"AS{number}.asn.cymru.com", "TXT")
    org = desc[0].split("|")[-1].strip() if desc else None
    return {"asn": int(number), "asn_org": org, "country": country}


def enrich(url: str) -> dict:
    host = urlsplit(url).hostname or url
    domain = registrable_domain(host)
    registered_domain = icann_domain(host)
    # On shared platforms the registration describes the platform, so its age says nothing about the site.
    shared_hosting = domain != registered_domain
    ips = _records(host, "A")
    hosting = asn(ips[0]) if ips else {"asn": None, "asn_org": None, "country": None}
    return {
        "host": host,
        "domain": domain,
        "registered_domain": registered_domain,
        "shared_hosting": shared_hosting,
        "rdap": registration(registered_domain),
        "dns": {"a": ips, "aaaa": _records(host, "AAAA"), "ns": _records(domain, "NS"), "mx": _records(domain, "MX")},
        "ip": ips[0] if ips else None,
        "asn": hosting["asn"],
        "hosting_org": hosting["asn_org"],
        "hosting_country": hosting["country"],
        "enriched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


if __name__ == "__main__":
    for target in sys.argv[1:]:
        print(json.dumps(enrich(target), ensure_ascii=False, indent=2))
