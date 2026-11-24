"""Which UAE brand does a host name? (Simon's matcher, shared by the radar and the engine.)

Long tokens ("emiratesnbd") match anywhere in the name. Short or ambiguous ones
("tamm", "dewa", "icp-") only count when everything else in the name is a
context word: tamm-fines-pay matches, tammy-shop does not.
"""

import re

from .brands import load_registry, official_brand_for_domain

DISTINCTIVE_LENGTH = 7
# Words that turn a short brand name into a likely impersonation: tamm-pay, uae-dewa, icp-online.
CONTEXT_WORDS = {
    "pay", "payment", "fine", "fines", "login", "secure", "verify", "update", "portal", "online", "service",
    "services", "uae", "ae", "gov", "refund", "renew", "track", "delivery", "rewards", "points", "dubai",
    "abudhabi", "emirates", "bank", "police", "visa", "id", "toll", "bill", "parcel", "post", "card", "pass",
    "official", "help", "support", "customer", "care", "my", "e", "app", "smart", "recharge", "account",
}


def is_official(host: str) -> bool:
    return official_brand_for_domain(host) is not None


def brand_tokens() -> dict[str, str]:
    """Lowercase token -> brand id."""
    return {
        token.lower(): brand.id for brand in load_registry().brands for token in brand.domain_tokens
    }


def _only_context(rest: str) -> bool:
    words = [w for w in re.split(r"[^a-z0-9]+", rest) if w]
    return any(w in CONTEXT_WORDS for w in words) and all(w in CONTEXT_WORDS or w.isdigit() for w in words)


def match_token(host: str) -> tuple[str, str] | None:
    """(brand id, token) if the host's name (minus its TLD) names a brand and isn't official."""
    host = host.lower().rstrip(".")
    if not host or is_official(host):
        return None
    label = host.rsplit(".", 1)[0]
    # Longest token first: "dubaicustoms-uae" is Dubai Customs, not the shorter "customs-uae".
    for token, brand_id in sorted(brand_tokens().items(), key=lambda item: -len(item[0].strip("-"))):
        core = token.strip("-")
        if core not in label:
            continue
        if len(core) >= DISTINCTIVE_LENGTH:
            return brand_id, core
        rest = label.replace(core, " ", 1)
        if _only_context(rest.replace(".", " ")):
            return brand_id, core
    return None


def match_brand(host: str) -> str | None:
    hit = match_token(host)
    return hit[0] if hit else None
