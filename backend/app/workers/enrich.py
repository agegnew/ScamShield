"""Who owns and hosts a domain (Simon): RDAP/WHOIS registration, DNS, IP, ASN and hosting provider.

Runs even when the page is offline, so dead scam links still carry domain evidence.
Every lookup has a short timeout; a failed lookup leaves its field empty.

Usage: python -m app.workers.enrich https://example.com/path
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

import dns.exception
import dns.resolver
import requests
import tldextract

from ..contracts import Evidence, Rdap

RDAP_URL = "https://rdap.org/domain/{}"
RDAP_IP_URL = "https://rdap.org/ip/{}"
TIMEOUT = 10
# .ae and a few other ccTLDs have no RDAP; their registry WHOIS is queried directly.
WHOIS_SERVERS = {"ae": "whois.aeda.net.ae"}

_extract = tldextract.TLDExtract(suffix_list_urls=(), include_psl_private_domains=True)


def registrable_domain(url_or_host: str) -> str:
    """The domain a registrant controls. For tenant hosts (foo.pages.dev) this is the tenant."""
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
    return {"created": events.get("registration"), "registrar": registrar, "abuse_email": abuse_email}


def _whois(domain: str, server: str) -> dict | None:
    out = subprocess.run(
        ["whois", "-h", server, domain], capture_output=True, text=True, timeout=TIMEOUT
    ).stdout
    if not out or re.search(r"no match|not found|no data", out, re.I):
        return None

    def field(name: str) -> str | None:
        m = re.search(rf"^{name}:\s*(.+)$", out, re.I | re.M)
        return m.group(1).strip() if m else None

    return {
        "created": field("Creation Date") or field("Created"),
        "registrar": field("Registrar Name") or field("Registrar"),
        "abuse_email": field("Registrar Abuse Contact Email"),
    }


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def registration(domain: str) -> Rdap | None:
    tld = domain.rsplit(".", 1)[-1]
    try:
        info = _whois(domain, WHOIS_SERVERS[tld]) if tld in WHOIS_SERVERS else _rdap(domain)
    except (requests.RequestException, subprocess.TimeoutExpired, OSError, ValueError):
        info = None
    if not info:
        return None
    return Rdap(
        created=_parse_date(info.get("created")),
        registrar=info.get("registrar"),
        abuse_email=info.get("abuse_email"),
    )


def _find_abuse_email(entities: list[dict]) -> str | None:
    for entity in entities:
        if "abuse" in entity.get("roles", []) and (email := _vcard(entity, "email")):
            return email
        if found := _find_abuse_email(entity.get("entities", [])):
            return found
    return None


def hosting_abuse_email(ip: str) -> str | None:
    """Abuse contact of the network that hosts the IP, for takedown requests."""
    try:
        resp = requests.get(RDAP_IP_URL.format(ip), timeout=TIMEOUT, headers={"Accept": "application/rdap+json"})
        return _find_abuse_email(resp.json().get("entities", [])) if resp.status_code == 200 else None
    except (requests.RequestException, ValueError):
        return None


def _records(name: str, rtype: str) -> list[str]:
    try:
        return sorted(r.to_text().strip('"') for r in dns.resolver.resolve(name, rtype, lifetime=TIMEOUT))
    except (dns.exception.DNSException, ValueError):
        return []


def asn(ip: str) -> tuple[int | None, str | None]:
    """IPv4 to ASN and owner through Team Cymru's free DNS service."""
    if ":" in ip:
        return None, None
    origin = _records(".".join(reversed(ip.split("."))) + ".origin.asn.cymru.com", "TXT")
    if not origin:
        return None, None
    number = origin[0].split("|")[0].strip().split()[0]
    desc = _records(f"AS{number}.asn.cymru.com", "TXT")
    return int(number), (desc[0].split("|")[-1].strip() if desc else None)


def lookup(url: str) -> dict:
    """Ownership and hosting facts for the URL's host."""
    host = urlsplit(url).hostname or url
    domain = registrable_domain(host)
    registered = icann_domain(host)
    ips = _records(host, "A")
    number, org = asn(ips[0]) if ips else (None, None)
    return {
        # On shared platforms the registration describes the platform, so its age says nothing about the site.
        "shared_hosting": domain != registered,
        "rdap": registration(registered),
        "ip": ips[0] if ips else None,
        "asn": number,
        "hosting_org": org,
        "hosting_abuse_email": hosting_abuse_email(ips[0]) if ips else None,
    }


# Destinations that are not the site being judged: a parked lookalike that redirects to a marketplace
# would otherwise get the marketplace's WHOIS (godaddy.com, 28 years old).
PLACEHOLDER_KINDS = {"parked", "for_sale", "expired", "blocked", "error", "coming_soon", "default_host_page"}


def enrich(evidence: Evidence) -> Evidence:
    """Fill rdap / ip / asn / hosting / shared_hosting for the final URL, or for the scanned URL
    when the final page is only a placeholder."""
    if evidence.fetch_error and evidence.fetch_error.startswith("Blocked"):
        return evidence  # private or forbidden address: nothing public to look up
    target = evidence.final_url or evidence.url
    if evidence.page_kind in PLACEHOLDER_KINDS:
        target = evidence.url
    return evidence.model_copy(update=lookup(target))


if __name__ == "__main__":
    for target in sys.argv[1:]:
        found = lookup(target)
        found["rdap"] = found["rdap"].model_dump(mode="json") if found["rdap"] else None
        print(json.dumps(found, ensure_ascii=False, indent=2, default=str))
