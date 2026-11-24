"""Radar 4 (Simon): Google Search results and ads for UAE brand and service queries, via SerpApi.

Any result or ad for a brand query, or for a generic service phrase victims search for
("pay traffic fine abu dhabi"), that points outside official domains becomes a candidate.
Each run spends its SerpApi budget on the queries that matter most (serp.plan()).

Try it: python -m app.workers.radar.search
"""

import logging
from datetime import datetime, timezone
from urllib.parse import urlsplit

from ...brand_match import is_official, match_brand
from ...contracts import Brand, Candidate, CandidateExtra, Source
from .base import RadarSource
from .serp import Query, is_neutral, plan_into_budget, serpapi

log = logging.getLogger("scamshield.radar.search")

# What victims type when they look for a service or an offer; fake sites and ads target these,
# not only brand names. Worth the most: one search covers every brand that sells the service.
GENERIC_QUERIES = [
    ("pay traffic fine abu dhabi", "en"), ("دفع المخالفات المرورية أبوظبي", "ar"),
    ("traffic fine discount uae", "en"), ("خصم المخالفات المرورية", "ar"),
    ("parking fine payment dubai", "en"), ("دفع مخالفة المواقف دبي", "ar"),
    ("consumer protection complaint uae", "en"), ("شكوى حماية المستهلك", "ar"),
    ("darb toll fine payment", "en"), ("دفع مخالفات درب", "ar"),
    ("parcel delivery fee uae", "en"), ("رسوم توصيل الطرد الإمارات", "ar"),
    ("uae visa status check", "en"), ("الاستعلام عن التأشيرة الإمارات", "ar"),
    ("domestic worker visa uae", "en"), ("تأشيرة عاملة منزلية", "ar"),
    ("free flight tickets uae", "en"), ("تذاكر طيران مجانية الإمارات", "ar"),
    ("supermarket gift voucher uae", "en"), ("قسيمة هدية مجانية الإمارات", "ar"),
]
GENERIC_WEIGHT = 3.0

# Per sector: what a victim searches next to the brand name, and how often the sector is copied.
SECTOR_QUERIES: dict[str, tuple[str, str, float]] = {
    "police": ("traffic fine payment", "دفع المخالفات المرورية", 2.0),
    "transport": ("fine payment", "دفع المخالفات", 2.0),
    "government": ("online services", "الخدمات الإلكترونية", 2.0),
    "bank": ("online banking login", "تسجيل الدخول للخدمات المصرفية", 2.0),
    "delivery": ("parcel delivery fee", "رسوم توصيل الطرد", 1.5),
    "shopping": ("gift voucher offer", "قسيمة هدية عرض", 1.5),
    "travel": ("free tickets offer", "تذاكر مجانية عرض", 1.5),
    "telecom": ("recharge offer", "عرض شحن الرصيد", 1.0),
    "utility": ("bill payment", "دفع الفاتورة", 1.0),
}


def _params(query: str, lang: str) -> dict:
    return {"engine": "google", "q": query, "google_domain": "google.ae", "gl": "ae", "hl": lang,
            "location": "United Arab Emirates", "num": 20}


def google(query: str, lang: str, brand_id: str | None) -> list[Candidate]:
    data = serpapi(_params(query, lang))
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


def brand_queries(brand: Brand) -> list[tuple[str, str]]:
    action_en, action_ar, _ = SECTOR_QUERIES.get(brand.category, ("", "", 1.0))
    name = brand.name_en.split(" (")[0]
    return [(f"{name} {action_en}".strip(), "en"), (f"{brand.name_ar} {action_ar}".strip(), "ar")]


def all_queries(brands: list[Brand]) -> list[tuple[Query, str, str | None]]:
    """(query, lang, brand id) for every search this radar could make, most valuable first."""
    out = [(Query(_params(q, lang), GENERIC_WEIGHT, q), lang, None) for q, lang in GENERIC_QUERIES]
    for brand in brands:
        weight = SECTOR_QUERIES.get(brand.category, ("", "", 1.0))[2]
        out += [(Query(_params(q, lang), weight, q), lang, brand.id) for q, lang in brand_queries(brand)]
    return out


class GoogleSearch(RadarSource):
    name = "search"
    source = Source.SEARCH
    interval_minutes = 2 * 60
    needs_key = "SERPAPI_KEY"

    def discover(self, brands: list[Brand]) -> list[Candidate]:
        queries = all_queries(brands)
        # About two thirds of the run's searches; the Maps radar gets the rest.
        plan_into_budget([q for q, _, _ in queries], share=2 / 3)
        found: list[Candidate] = []
        self.report(0, len(queries))
        for i, (query, lang, brand_id) in enumerate(queries, 1):
            found += google(query.label, lang, brand_id)
            self.report(i, len(queries))
        return found


if __name__ == "__main__":
    from ...brands import load_registry

    logging.basicConfig(level=logging.INFO)
    for c in GoogleSearch().discover(load_registry().brands):
        print(c.source.value, c.extra.brand, c.url, "(replayed)" if c.extra.details["replayed"] else "")
