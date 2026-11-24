"""Load the UAE brand registry (brands.json) and answer: is this host official, and which brand does it name?"""
import json
from functools import lru_cache
from pathlib import Path

BRANDS_PATH = Path(__file__).resolve().parent.parent / "brands.json"


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


def match_brand(host: str) -> str | None:
    host = host.lower()
    for token, brand_id in brand_tokens().items():
        if token in host:
            return brand_id
    return None
