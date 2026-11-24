"""Domain and hosting enrichment — SIMON OWNS THIS FILE.

Fill in, on a copy of the Evidence (evidence.model_copy(update={...})):
- rdap: created date, registrar, registrar abuse email.
  RDAP bootstrap: https://rdap.org/domain/<registrable domain>
- ip: first public IP of the final host (DNS A/AAAA).
- asn, hosting_org, hosting_abuse_email: IP -> ASN/org lookup
  (e.g. RDAP for the IP: https://rdap.org/ip/<ip>).

Works even when fetch failed (a dead site still has WHOIS/DNS).
Use httpx with a short timeout; on any lookup error leave the field None.
"""

from ..contracts import Evidence


def enrich(evidence: Evidence) -> Evidence:
    return evidence
