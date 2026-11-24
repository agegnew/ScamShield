"""Radar 1 — lookalike domains. SIMON OWNS THIS FILE. Free, no API key.

For each official domain in brands.json generate variants:
- typos: missing/doubled/swapped letters, adjacent keys (tamm -> tam, taam, tmam)
- homoglyphs: rn->m, l->1, o->0, Arabic/Cyrillic look-alike letters (punycode)
- hyphen and TLD swaps: uae-pass.ae, uaepass.com, uaepass-ae.com
- brand + keyword combos: tamm-fines, tamm-pay, rta-fine-check, enbd-support
  (keywords: pay, fine, fines, login, verify, update, support, refund, portal)
Keep only variants that resolve in DNS (registered). Emit
Candidate(url="https://<variant>/", source=Source.LOOKALIKE, query=<brand id>).
The `dnstwist` package can generate most typo/homoglyph variants.
"""

from ...contracts import Brand, Candidate, Source
from .base import RadarSource


class Lookalikes(RadarSource):
    name = "lookalikes"
    source = Source.LOOKALIKE
    interval_minutes = 60

    def discover(self, brands: list[Brand]) -> list[Candidate]:
        return []
