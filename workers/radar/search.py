"""Radars 4 and 5: Google Search (organic results and ads) and Google Maps listings for UAE brand queries, via SerpApi.

Search: any result or ad for a brand query that points outside the brand's official domains is queued.
Maps: a listing that names a brand is queued when its website is not official, or when it presents itself as a
helpline / customer service and its phone is not an official helpline.

Every SerpApi answer is saved in data/serp/; without SERPAPI_KEY the radar replays those saved answers.

Usage: python -m workers.radar.search [--maps-only | --search-only] [--brand tamm] [--dry-run]
"""
import argparse
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

import phonenumbers
import requests

from workers import brands, store

log = logging.getLogger("search")

SERPAPI_URL = "https://serpapi.com/search.json"
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "serp"
UAE_CENTER = "@24.4539,54.3773,9z"
HELPLINE_CLAIM = re.compile(
    r"customer\s*(service|care|support)|help\s*line|hotline|call\s*cent|contact|complain|refund|"
    r"خدمة العملاء|خط المساعدة|الدعم|مركز الاتصال", re.I)
# Search results on these hosts are news, social or directories, not impersonation.
NEUTRAL_HOSTS = {"wikipedia.org", "youtube.com", "facebook.com", "instagram.com", "x.com", "twitter.com",
                 "linkedin.com", "tiktok.com", "gulfnews.com", "khaleejtimes.com", "thenationalnews.com",
                 "apps.apple.com", "play.google.com", "google.com", "reddit.com", "wam.ae", "u.ae"}


def _cache_path(params: dict) -> Path:
    key = json.dumps({k: v for k, v in sorted(params.items()) if k != "api_key"}, ensure_ascii=False)
    return CACHE_DIR / f"{params['engine']}_{hashlib.sha256(key.encode()).hexdigest()[:16]}.json"


def serpapi(params: dict) -> dict:
    cache = _cache_path(params)
    key = os.environ.get("SERPAPI_KEY")
    if key:
        resp = requests.get(SERPAPI_URL, params={**params, "api_key": key}, timeout=60)
        if resp.status_code == 200:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache.write_text(resp.text)
            return resp.json()
        log.warning("SerpApi %s: HTTP %s", params.get("q"), resp.status_code)
    if cache.exists():
        return {**json.loads(cache.read_text()), "_replayed": True}
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
    return any(host == h or host.endswith("." + h) for h in NEUTRAL_HOSTS)


def search_queries(brand: dict) -> list[tuple[str, str]]:
    return [(q, "en") for q in brand["keywords_en"]] + [(q, "ar") for q in brand["keywords_ar"]]


def search_brand(brand: dict) -> list[dict]:
    hits = []
    for query, lang in search_queries(brand):
        data = serpapi({"engine": "google", "q": query, "google_domain": "google.ae", "gl": "ae", "hl": lang,
                        "location": "United Arab Emirates", "num": 20})
        results = [("search_ad", r) for r in data.get("ads", [])] + \
                  [("search", r) for r in data.get("organic_results", [])]
        for source, result in results:
            link = result.get("link")
            host = (urlsplit(link).hostname or "") if link else ""
            if not host or brands.is_official(host) or is_neutral(host):
                continue
            hits.append({"url": link, "source": source, "query": query, "brand": brand["id"],
                         "extra": {"brand": brand["id"], "title": result.get("title"), "lang": lang,
                                   "position": result.get("position"), "replayed": data.get("_replayed", False)}})
    return hits


def maps_brand(brand: dict) -> list[dict]:
    hits = []
    official_phones = {e164(p) for p in brand["helplines"]}
    names = [brand["name_en"].split(" (")[0], brand["name_ar"]]
    for query in [f"{names[0]} customer service", f"{names[0]} UAE", f"{names[1]} خدمة العملاء"]:
        data = serpapi({"engine": "google_maps", "q": query, "ll": UAE_CENTER, "type": "search", "hl": "en"})
        for place in data.get("local_results", []):
            title = place.get("title") or ""
            if brands.match_brand(title.replace(" ", "")) != brand["id"] and \
                    not any(n.lower() in title.lower() for n in names):
                continue
            website = place.get("website")
            host = (urlsplit(website).hostname or "") if website else ""
            phone = e164(place.get("phone", ""))
            flags = []
            if host and not brands.is_official(host) and not is_neutral(host):
                flags.append("website_not_official")
            if phone and official_phones and phone not in official_phones and HELPLINE_CLAIM.search(title):
                flags.append("helpline_not_official")
            if not flags:
                continue
            place_url = f"https://www.google.com/maps/place/?q=place_id:{place.get('place_id')}"
            hits.append({"url": website if "website_not_official" in flags else place_url, "source": "maps",
                         "query": query, "brand": brand["id"],
                         "extra": {"brand": brand["id"], "listing_name": title, "phone": phone,
                                   "official_helplines": sorted(p for p in official_phones if p),
                                   "address": place.get("address"), "website": website, "maps_url": place_url,
                                   "flags": flags, "rating": place.get("rating"), "reviews": place.get("reviews"),
                                   "replayed": data.get("_replayed", False)}})
    return hits


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--maps-only", action="store_true")
    group.add_argument("--search-only", action="store_true")
    parser.add_argument("--brand", action="append")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    if not os.environ.get("SERPAPI_KEY"):
        log.warning("SERPAPI_KEY not set: replaying saved results from %s", CACHE_DIR)

    hits = []
    for brand in brands.load():
        if args.brand and brand["id"] not in args.brand:
            continue
        if not args.maps_only:
            hits += search_brand(brand)
        if not args.search_only:
            hits += maps_brand(brand)
    if args.dry_run:
        for hit in hits:
            print(hit["source"], hit["brand"], hit["url"], json.dumps(hit["extra"].get("flags", ""), ensure_ascii=False))
        return
    conn = store.connect()
    new = sum(store.add_candidate(conn, h["url"], h["source"], query=h["query"], extra=h["extra"]) is not None
              for h in hits)
    print(f"{len(hits)} search/maps hits, {new} new queued")


if __name__ == "__main__":
    main()
