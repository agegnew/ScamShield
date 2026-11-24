"""Radar 4 — Google Maps listings. SIMON OWNS THIS FILE. Needs SERPAPI_KEY.

SerpApi engine=google_maps, query "<brand name> customer care" / "<brand> branch",
ll centred on Abu Dhabi and Dubai. For each listing with a `website`:
Candidate(url=website, source=Source.MAPS, query=<query>,
          extra=CandidateExtra(listing_name=title, phone=phone, address=address))
Keep listings WITHOUT a website too when the phone is not an official helpline:
use the listing's Google Maps link as the url so the case still exists.
The engine compares extra.phone with the brand's helplines (helpline_mismatch).
"""

from ...contracts import Brand, Candidate, Source
from .base import RadarSource


class GoogleMaps(RadarSource):
    name = "maps"
    source = Source.MAPS
    interval_minutes = 60
    required_env = ("SERPAPI_KEY",)

    def discover(self, brands: list[Brand]) -> list[Candidate]:
        return []
