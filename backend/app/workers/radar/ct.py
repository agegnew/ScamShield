"""Radar 2 — new TLS certificates. SIMON OWNS THIS FILE. Free, no API key.

Query crt.sh for each brand keyword, e.g.
  https://crt.sh/?q=%25tamm%25&output=json
Keep certificates issued in the last ~7 days whose names are NOT under an
official domain of that brand. Emit one Candidate per distinct host:
Candidate(url="https://<host>/", source=Source.CT, query=<keyword>).
Skip wildcard prefixes ("*.") and dedupe hosts. crt.sh is slow: 30 s timeout,
and cache the last good response to disk so a crt.sh outage doesn't empty the radar.
"""

from ...contracts import Brand, Candidate, Source
from .base import RadarSource


class CertTransparency(RadarSource):
    name = "ct"
    source = Source.CT
    interval_minutes = 30

    def discover(self, brands: list[Brand]) -> list[Candidate]:
        return []
