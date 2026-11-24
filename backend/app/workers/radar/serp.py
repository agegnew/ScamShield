"""SerpApi helpers shared by the Search and Maps radars (Simon).

Every SerpApi answer is saved; without SERPAPI_KEY the radars replay the saved answers and
mark their results replayed=true, so the UI can label them.
"""

import hashlib
import json
import logging
import os
import re

import phonenumbers
import requests

from ...config import CACHE_DIR

log = logging.getLogger("scamshield.radar.serp")

SERPAPI_URL = "https://serpapi.com/search.json"
GOV_SUFFIXES = (".gov.ae", ".abudhabi", ".dubai")
# Results on these hosts are news, social or directories, not impersonation.
NEUTRAL_HOSTS = {"wikipedia.org", "youtube.com", "facebook.com", "instagram.com", "x.com", "twitter.com",
                 "linkedin.com", "tiktok.com", "gulfnews.com", "khaleejtimes.com", "thenationalnews.com",
                 "apps.apple.com", "play.google.com", "google.com", "reddit.com", "wam.ae", "u.ae"}


def _cache_path(params: dict):
    key = json.dumps({k: v for k, v in sorted(params.items()) if k != "api_key"}, ensure_ascii=False)
    return CACHE_DIR / "serp" / f"{params['engine']}_{hashlib.sha256(key.encode()).hexdigest()[:16]}.json"


def serpapi(params: dict) -> dict:
    cache = _cache_path(params)
    key = os.environ.get("SERPAPI_KEY")
    if key:
        try:
            resp = requests.get(SERPAPI_URL, params={**params, "api_key": key}, timeout=60)
            if resp.status_code == 200:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(resp.text, encoding="utf-8")
                return resp.json()
            log.warning("SerpApi %s: HTTP %s", params.get("q"), resp.status_code)
        except requests.RequestException as exc:
            log.warning("SerpApi %s: %s", params.get("q"), type(exc).__name__)
    if cache.exists():
        return {**json.loads(cache.read_text(encoding="utf-8")), "_replayed": True}
    return {}


def e164(raw: str) -> str | None:
    digits = re.sub(r"[^\d+]", "", raw or "")
    if len(digits) <= 4:
        return digits or None
    try:
        number = phonenumbers.parse(raw, "AE")
    except phonenumbers.NumberParseException:
        return None
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def is_neutral(host: str) -> bool:
    return any(host == h or host.endswith("." + h) for h in NEUTRAL_HOSTS) or host.endswith(GOV_SUFFIXES)
