"""Load the UAE brand registry (brands.json) and answer: is this host official, and which brand does it name?"""
import json
import re
from functools import lru_cache
from pathlib import Path

BRANDS_PATH = Path(__file__).resolve().parent.parent / "data" / "brands.json"


@lru_cache(maxsize=1)
def load() -> list[dict]:
    return json.loads(BRANDS_PATH.read_text(encoding="utf-8"))["brands"]


def official_domains() -> set[str]:
    return {d for brand in load() for d in brand["official_domains"]}


def is_official(host: str) -> bool:
    host = host.lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in official_domains())


def brand_tokens() -> dict[str, str]:
    """Lowercase token -> brand id, used to spot brand names inside unrelated domains."""
    return {token: brand["id"] for brand in load() for token in brand["domain_tokens"]}


DISTINCTIVE_LENGTH = 7
# Words that turn a short, ambiguous brand name into a likely impersonation: tamm-pay, uae-dewa, icp-online.
CONTEXT_WORDS = {
    "pay", "payment", "fine", "fines", "login", "secure", "verify", "update", "portal", "online", "service",
    "services", "uae", "ae", "gov", "refund", "renew", "track", "delivery", "rewards", "points", "dubai",
    "abudhabi", "emirates", "bank", "police", "visa", "id", "toll", "bill", "parcel", "post", "card", "pass",
    "official", "help", "support", "customer", "care", "my", "e", "app", "smart", "recharge", "account",
}


def _only_context(rest: str) -> bool:
    words = [w for w in re.split(r"[^a-z0-9]+", rest) if w]
    return any(w in CONTEXT_WORDS for w in words) and all(w in CONTEXT_WORDS or w.isdigit() for w in words)


def match_brand(host: str) -> str | None:
    """Brand id if the host's registrable label names a brand; short names need a context word next to them."""
    label = host.lower().rstrip(".").rsplit(".", 1)[0]
    if is_official(host):
        return None
    for token, brand_id in brand_tokens().items():
        core = token.strip("-")
        if core not in label:
            continue
        if len(core) >= DISTINCTIVE_LENGTH:
            return brand_id
        rest = label.replace(core, " ", 1)
        if _only_context(rest.replace(".", " ")):
            return brand_id
    return None
