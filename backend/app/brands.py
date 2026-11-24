import re
from functools import lru_cache

from .config import BRANDS_PATH
from .contracts import Brand, BrandRegistry


@lru_cache(maxsize=1)
def load_registry() -> BrandRegistry:
    return BrandRegistry.model_validate_json(BRANDS_PATH.read_text(encoding="utf-8"))


def brand_by_id(brand_id: str | None) -> Brand | None:
    if not brand_id:
        return None
    return next((b for b in load_registry().brands if b.id == brand_id), None)


def official_brand_for_domain(host: str) -> Brand | None:
    """Brand whose official domain is `host` or a parent of it."""
    host = host.lower().rstrip(".")
    for brand in load_registry().brands:
        for domain in brand.official_domains:
            if host == domain or host.endswith("." + domain):
                return brand
    return None


def normalize_uae_phone(raw: str) -> str:
    """Digits only, without the +971 / 00971 country code or a leading 0.

    '+971 4 555 0199', '04 555 0199' and '045550199' all become '45550199'.
    """
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("00971"):
        digits = digits[5:]
    elif digits.startswith("971"):
        digits = digits[3:]
    return digits.lstrip("0")


def brand_for_helpline(phone: str) -> Brand | None:
    target = normalize_uae_phone(phone)
    if not target:
        return None
    for brand in load_registry().brands:
        if any(normalize_uae_phone(h) == target for h in brand.helplines):
            return brand
    return None
