"""Radar 3: new TLS certificates whose names contain a UAE brand (Certificate Transparency via crt.sh).

crt.sh is slow and often returns 502, so each brand is queried with retries and the last good answer is cached
in data/ct/; a failed query falls back to that cache.

Usage: python -m workers.radar.certificates [--days 30] [--dry-run]
"""
import argparse
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from workers import brands, store

log = logging.getLogger("certificates")

CRT_URL = "https://crt.sh/"
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "ct"
TIMEOUT_S = 90
RETRIES = 2


def query(token: str) -> list[dict]:
    cache = CACHE_DIR / f"{token}.json"
    for attempt in range(RETRIES + 1):
        try:
            resp = requests.get(CRT_URL, params={"q": f"%{token}%", "output": "json"}, timeout=TIMEOUT_S)
            if resp.status_code == 200:
                rows = resp.json()
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(rows))
                return rows
            log.warning("crt.sh %s: HTTP %s", token, resp.status_code)
        except (requests.RequestException, ValueError) as exc:
            log.warning("crt.sh %s: %s", token, type(exc).__name__)
        time.sleep(5 * (attempt + 1))
    if cache.exists():
        log.info("crt.sh %s: using cache from %s", token,
                 datetime.fromtimestamp(cache.stat().st_mtime).isoformat(timespec="minutes"))
        return json.loads(cache.read_text())
    return []


def scan(days: int) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    tokens = sorted({t.strip("-") for t in brands.brand_tokens() if len(t.strip("-")) >= 4})
    seen: dict[str, dict] = {}
    for token in tokens:
        rows = query(token)
        for row in rows:
            if row.get("not_before", "") < since:
                continue
            for name in row.get("name_value", "").split("\n"):
                host = name.strip().lower().lstrip("*.")
                brand = brands.match_brand(host)
                if brand and host not in seen:
                    seen[host] = {"domain": host, "brand": brand, "cert_issued": row["not_before"],
                                  "issuer": row.get("issuer_name"), "crt_id": row.get("id")}
        log.info("%s: %d certificates", token, len(rows))
    return list(seen.values())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    hits = scan(args.days)
    if args.dry_run:
        for hit in sorted(hits, key=lambda h: h["cert_issued"], reverse=True):
            print(hit["cert_issued"], hit["brand"], hit["domain"])
        return
    conn = store.connect()
    new = sum(store.add_candidate(conn, f"https://{h['domain']}/", "ct", query=h["brand"], extra=h) is not None
              for h in hits)
    print(f"{len(hits)} brand-named certificates, {new} new queued")


if __name__ == "__main__":
    main()
