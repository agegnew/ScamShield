"""Radar 3 — Google Search results and ads. SIMON OWNS THIS FILE. Needs SERPAPI_KEY.

SerpApi engine=google, gl=ae, hl=en and hl=ar. Queries come from
data/scam_themes.json (app.themes.load_themes(): search_queries_en / _ar per
theme) plus "<brand name> customer care" for each brand.
From each response take `organic_results[].link` (Source.SEARCH) and
`ads[].link` (Source.SEARCH_AD). Skip official domains of any brand.
Emit Candidate(url=link, source=..., query=<the query>).
Budget: keep the query list short — every query costs one SerpApi credit.
"""

from ...contracts import Brand, Candidate, Source
from .base import RadarSource


class GoogleSearch(RadarSource):
    name = "search"
    source = Source.SEARCH
    interval_minutes = 60
    required_env = ("SERPAPI_KEY",)

    def discover(self, brands: list[Brand]) -> list[Candidate]:
        return []
