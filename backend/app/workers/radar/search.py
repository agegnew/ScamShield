"""Radar 4 (Simon): Google Search results and ads for UAE brand and service queries, via SerpApi.

Any result or ad for a brand query, or for a generic service phrase victims search for
("pay traffic fine abu dhabi"), that points outside official domains becomes a candidate.

Try it: python -m app.workers.radar.search
"""

import logging
from datetime import datetime, timezone
from urllib.parse import urlsplit

from ...brand_match import is_official, match_brand
from ...contracts import Brand, Candidate, CandidateExtra, Source
from .base import RadarSource
from .serp import is_neutral, serpapi

log = logging.getLogger("scamshield.radar.search")

# What victims type when they look for a service; fake sites and ads target these, not only brand names.
GENERIC_QUERIES = [
    ("pay traffic fine abu dhabi", "en"), ("دفع المخالفات المرورية أبوظبي", "ar"),
    ("traffic fine discount uae", "en"), ("خصم المخالفات المرورية", "ar"),
    ("consumer protection complaint uae", "en"), ("شكوى حماية المستهلك", "ar"),
    ("darb toll fine payment", "en"), ("دفع مخالفات درب", "ar"),
    ("parcel delivery fee uae", "en"), ("رسوم توصيل الطرد الإمارات", "ar"),
    ("uae visa status check", "en"), ("الاستعلام عن التأشيرة الإمارات", "ar"),
    ("domestic worker visa uae", "en"), ("تأشيرة عاملة منزلية", "ar"),
]


def google(query: str, lang: str, brand_id: str | None) -> list[Candidate]:
    data = serpapi({"engine": "google", "q": query, "google_domain": "google.ae", "gl": "ae", "hl": lang,
                    "location": "United Arab Emirates", "num": 20})
    now = datetime.now(timezone.utc)
    found = []
    results = [(Source.SEARCH_AD, r) for r in data.get("ads", [])] + \
              [(Source.SEARCH, r) for r in data.get("organic_results", [])]
    for source, result in results:
        link = result.get("link")
        host = (urlsplit(link).hostname or "") if link else ""
        if not host or is_official(host) or is_neutral(host):
            continue
        target = brand_id or match_brand(host)
        found.append(Candidate(
            url=link, source=source, query=query, discovered_at=now,
            extra=CandidateExtra(brand=target, details={
                "title": result.get("title"), "lang": lang, "position": result.get("position"),
                "replayed": data.get("_replayed", False)}),
        ))
    return found


class GoogleSearch(RadarSource):
    name = "search"
    source = Source.SEARCH
    interval_minutes = 2 * 60  # every query costs one SerpApi credit

    def discover(self, brands: list[Brand]) -> list[Candidate]:
        found = [c for query, lang in GENERIC_QUERIES for c in google(query, lang, None)]
        for brand in brands:
            queries = [(q, "en") for q in brand.keywords_en] + [(q, "ar") for q in brand.keywords_ar]
            found += [c for query, lang in queries for c in google(query, lang, brand.id)]
        return found


if __name__ == "__main__":
    from ...brands import load_registry

    logging.basicConfig(level=logging.INFO)
    for c in GoogleSearch().discover(load_registry().brands):
        print(c.source.value, c.extra.brand, c.url, "(replayed)" if c.extra.details["replayed"] else "")
