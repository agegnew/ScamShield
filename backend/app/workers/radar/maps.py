"""Radar 5 (Simon): Google Maps listings that impersonate UAE brands, via SerpApi.

A listing that names a brand becomes a candidate when its website is not official, or when it
presents itself as a helpline / customer service and its phone is not an official helpline.
The engine then raises helpline_mismatch from extra.phone.

Try it: python -m app.workers.radar.maps
"""

import logging
from datetime import datetime, timezone
from urllib.parse import urlsplit

from ...brand_match import is_official, match_brand
from ...brands import HELPLINE_CLAIM
from ...contracts import Brand, Candidate, CandidateExtra, Source
from .base import RadarSource
from .serp import Query, e164, is_neutral, plan_into_budget, serpapi

log = logging.getLogger("scamshield.radar.maps")

UAE_CENTER = "@24.4539,54.3773,9z"


def _params(query: str) -> dict:
    return {"engine": "google_maps", "q": query, "ll": UAE_CENTER, "type": "search", "hl": "en"}


def brand_queries(brand: Brand) -> list[Query]:
    """Fake helplines hide behind "customer service" listings. A brand with official helplines to
    compare against is worth more; the Arabic and plain-name searches are the fallbacks."""
    name = brand.name_en.split(" (")[0]
    main = 1.5 if brand.helplines else 0.75
    return [
        Query(_params(f"{name} customer service"), main, f"{name} customer service"),
        Query(_params(f"{brand.name_ar} خدمة العملاء"), main * 2 / 3, f"{brand.name_ar} خدمة العملاء"),
        Query(_params(f"{name} UAE"), 0.5, f"{name} UAE"),
    ]


def listings(brand: Brand) -> list[Candidate]:
    official_phones = {e164(p) for p in brand.helplines}
    names = [brand.name_en.split(" (")[0], brand.name_ar]
    now = datetime.now(timezone.utc)
    found = []
    for q in brand_queries(brand):
        query = q.params["q"]
        data = serpapi(q.params)
        # An exact match comes back as a single place_results object instead of a list.
        places = data.get("local_results") or ([data["place_results"]] if data.get("place_results") else [])
        for place in places:
            title = place.get("title") or ""
            if match_brand(title.replace(" ", "")) != brand.id and \
                    not any(n.lower() in title.lower() for n in names):
                continue
            website = place.get("website")
            host = (urlsplit(website).hostname or "") if website else ""
            phone = e164(place.get("phone", ""))
            flags = []
            if host and not is_official(host) and not is_neutral(host):
                flags.append("website_not_official")
            if phone and official_phones and phone not in official_phones and HELPLINE_CLAIM.search(title):
                flags.append("helpline_not_official")
            if not flags:
                continue
            place_url = f"https://www.google.com/maps/place/?q=place_id:{place.get('place_id')}"
            found.append(Candidate(
                url=website if "website_not_official" in flags else place_url,
                source=Source.MAPS, query=query, discovered_at=now,
                extra=CandidateExtra(
                    listing_name=title, phone=phone, address=place.get("address"), brand=brand.id,
                    details={"website": website, "maps_url": place_url, "flags": flags,
                             "official_helplines": sorted(p for p in official_phones if p),
                             "rating": place.get("rating"), "reviews": place.get("reviews"),
                             "replayed": data.get("_replayed", False)}),
            ))
    return found


class GoogleMaps(RadarSource):
    name = "maps"
    source = Source.MAPS
    interval_minutes = 2 * 60
    needs_key = "SERPAPI_KEY"

    def discover(self, brands: list[Brand]) -> list[Candidate]:
        plan_into_budget([q for brand in brands for q in brand_queries(brand)])
        found: list[Candidate] = []
        self.report(0, len(brands))
        for i, brand in enumerate(brands, 1):
            found += listings(brand)
            self.report(i, len(brands))
        return found


if __name__ == "__main__":
    from ...brands import load_registry

    logging.basicConfig(level=logging.INFO)
    for c in GoogleMaps().discover(load_registry().brands):
        print(c.extra.brand, c.extra.listing_name, c.extra.phone, c.url, c.extra.details["flags"])
