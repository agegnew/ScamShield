"""Radar 3 (Simon): domains registered in the last days that name a UAE brand.

Source: the free daily newly-registered-domains list from whoisds.com (about 70k domains a day).
Lists are cached so a re-run or an offline demo uses the last good download.

Try it: python -m app.workers.radar.nrd
"""

import base64
import io
import logging
import zipfile
from datetime import date, datetime, timedelta, timezone

import requests

from ...brand_match import match_brand
from ...config import CACHE_DIR
from ...contracts import Brand, Candidate, CandidateExtra, Source
from .base import RadarSource

log = logging.getLogger("scamshield.radar.nrd")

NRD_URL = "https://www.whoisds.com/whois-database/newly-registered-domains/{}/nrd"
LOOKBACK_DAYS = 3


def download(day: date) -> list[str]:
    cached = CACHE_DIR / "nrd" / f"{day.isoformat()}.txt"
    if cached.exists():
        return cached.read_text(encoding="utf-8", errors="ignore").split()
    token = base64.b64encode(f"{day.isoformat()}.zip".encode()).decode()
    try:
        resp = requests.get(NRD_URL.format(token), timeout=60)
    except requests.RequestException as exc:
        log.warning("no list for %s (%s)", day, type(exc).__name__)
        return []
    if resp.status_code != 200 or not resp.content.startswith(b"PK"):
        log.warning("no list for %s (HTTP %s)", day, resp.status_code)
        return []
    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        text = archive.read(archive.namelist()[0]).decode("utf-8", "ignore")
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(text, encoding="utf-8")
    return text.split()


class NewDomains(RadarSource):
    name = "nrd"
    source = Source.NRD
    interval_minutes = 6 * 60

    def discover(self, brands: list[Brand]) -> list[Candidate]:
        wanted = {b.id for b in brands}
        now = datetime.now(timezone.utc)
        found: list[Candidate] = []
        for back in range(1, LOOKBACK_DAYS + 1):
            day = date.today() - timedelta(days=back)
            domains = download(day)
            hits = [(d, b) for d in domains if (b := match_brand(d)) and b in wanted]
            log.info("%s: %d new domains, %d name a brand", day, len(domains), len(hits))
            found += [
                Candidate(url=f"http://{domain}/", source=Source.NRD, query=brand, discovered_at=now,
                          extra=CandidateExtra(brand=brand, details={"registered_on": day.isoformat()}))
                for domain, brand in hits
            ]
        return found


if __name__ == "__main__":
    from ...brands import load_registry

    logging.basicConfig(level=logging.INFO)
    for c in NewDomains().discover(load_registry().brands):
        print(c.extra.details["registered_on"], c.extra.brand, c.url)
