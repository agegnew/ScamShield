"""Radar 2 (Simon): new TLS certificates whose names contain a UAE brand (Certificate Transparency, crt.sh).

crt.sh is slow and often returns 502, so each token is queried with retries and the last good
answer is cached; a failed query falls back to that cache.

Try it: python -m app.workers.radar.ct
"""

import json
import logging
import time
from datetime import datetime, timedelta, timezone

import requests

from ...brand_match import brand_tokens, match_brand
from ...config import CACHE_DIR
from ...contracts import Brand, Candidate, CandidateExtra, Source
from .base import RadarSource

log = logging.getLogger("scamshield.radar.ct")

CRT_URL = "https://crt.sh/"
TIMEOUT_S = 90
RETRIES = 2
LOOKBACK_DAYS = 30


def query(token: str) -> list[dict]:
    cache = CACHE_DIR / "ct" / f"{token}.json"
    for attempt in range(RETRIES + 1):
        try:
            resp = requests.get(CRT_URL, params={"q": f"%{token}%", "output": "json"}, timeout=TIMEOUT_S)
            if resp.status_code == 200:
                rows = resp.json()
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(rows), encoding="utf-8")
                return rows
            log.warning("crt.sh %s: HTTP %s", token, resp.status_code)
        except (requests.RequestException, ValueError) as exc:
            log.warning("crt.sh %s: %s", token, type(exc).__name__)
        time.sleep(5 * (attempt + 1))
    if cache.exists():
        log.info("crt.sh %s: using cache from %s", token,
                 datetime.fromtimestamp(cache.stat().st_mtime).isoformat(timespec="minutes"))
        return json.loads(cache.read_text(encoding="utf-8"))
    return []


def hosts_from(rows: list[dict], since: str) -> dict[str, dict]:
    """Brand-naming hosts in certificates issued after `since`, with certificate details."""
    seen: dict[str, dict] = {}
    for row in rows:
        if row.get("not_before", "") < since:
            continue
        for name in row.get("name_value", "").split("\n"):
            host = name.strip().lower().lstrip("*.")
            brand = match_brand(host)
            if brand and host not in seen:
                seen[host] = {"brand": brand, "cert_issued": row["not_before"],
                              "issuer": row.get("issuer_name"), "crt_id": row.get("id")}
    return seen


class CertTransparency(RadarSource):
    name = "ct"
    source = Source.CT
    interval_minutes = 60

    def discover(self, brands: list[Brand]) -> list[Candidate]:
        since = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%dT%H:%M:%S")
        wanted = {b.id for b in brands}
        tokens = sorted({t.strip("-") for t, b in brand_tokens().items() if b in wanted and len(t.strip("-")) >= 4})
        seen: dict[str, dict] = {}
        self.report(0, len(tokens))
        for i, token in enumerate(tokens, 1):
            rows = query(token)
            for host, info in hosts_from(rows, since).items():
                seen.setdefault(host, info)
            log.info("%s: %d certificates", token, len(rows))
            self.report(i, len(tokens))
        now = datetime.now(timezone.utc)
        return [
            Candidate(url=f"https://{host}/", source=Source.CT, query=info["brand"], discovered_at=now,
                      extra=CandidateExtra(brand=info["brand"], details=info))
            for host, info in seen.items()
        ]


if __name__ == "__main__":
    from ...brands import load_registry

    logging.basicConfig(level=logging.INFO)
    for c in CertTransparency().discover(load_registry().brands):
        print(c.extra.details["cert_issued"], c.extra.brand, c.url)
