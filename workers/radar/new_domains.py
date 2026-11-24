"""Radar 2: domains registered in the last days that name a UAE brand.

Source: the free daily newly-registered-domains list from whoisds.com (about 70k domains a day).
Lists are cached in data/nrd/ so a re-run or an offline demo uses the last good download.

Usage: python -m workers.radar.new_domains [--days 3] [--dry-run]
"""
import argparse
import base64
import io
import logging
import zipfile
from datetime import date, timedelta
from pathlib import Path

import requests

from workers import brands, store

log = logging.getLogger("new_domains")

NRD_URL = "https://www.whoisds.com/whois-database/newly-registered-domains/{}/nrd"
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "nrd"


def download(day: date) -> list[str]:
    cached = CACHE_DIR / f"{day.isoformat()}.txt"
    if cached.exists():
        return cached.read_text().split()
    token = base64.b64encode(f"{day.isoformat()}.zip".encode()).decode()
    resp = requests.get(NRD_URL.format(token), timeout=60)
    if resp.status_code != 200 or not resp.content.startswith(b"PK"):
        log.warning("no list for %s (HTTP %s)", day, resp.status_code)
        return []
    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        text = archive.read(archive.namelist()[0]).decode("utf-8", "ignore")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached.write_text(text)
    return text.split()


def scan(days: int) -> list[dict]:
    hits = []
    for back in range(1, days + 1):
        day = date.today() - timedelta(days=back)
        domains = download(day)
        found = [{"domain": d, "brand": b, "registered_on": day.isoformat()}
                 for d in domains if (b := brands.match_brand(d))]
        log.info("%s: %d new domains, %d name a brand", day, len(domains), len(found))
        hits += found
    return hits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    hits = scan(args.days)
    if args.dry_run:
        for hit in hits:
            print(hit["registered_on"], hit["brand"], hit["domain"])
        return
    conn = store.connect()
    new = sum(store.add_candidate(conn, f"http://{h['domain']}/", "nrd", query=h["brand"],
                                  extra={"brand": h["brand"], "registered_on": h["registered_on"]}) is not None
              for h in hits)
    print(f"{len(hits)} brand-named new domains, {new} new queued")


if __name__ == "__main__":
    main()
