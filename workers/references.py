"""Visual references of the real brand sites, and matching a suspicious page against them.

A page that reuses an official favicon, or looks almost the same as an official page, while sitting on a
non-official domain is imitating that brand.

Usage: python -m workers.references        # capture missing references into data/references.json
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from workers import brands
from workers.fingerprint import hamming

log = logging.getLogger("references")

REFERENCES_PATH = Path(__file__).resolve().parent.parent / "data" / "references.json"
# dHash bits that may differ (of 64) for two screenshots to count as the same look. Tuned on official pages.
LOOKALIKE_MAX_DISTANCE = 10


def _capture_one(brand_id: str, domain: str) -> dict | None:
    from workers.fetcher import fetch

    for url in (f"https://{domain}/", f"https://www.{domain}/"):
        page = fetch(url)
        if page["status"] == "ok" and page["fingerprints"]:
            return {"brand": brand_id, "domain": domain, "final_url": page["final_url"], "title": page["title"],
                    "screenshot_path": page["screenshot_path"], **{k: page["fingerprints"][k] for k in (
                        "favicon_mmh3", "favicon_sha256", "dom_hash", "screenshot_dhash")}}
        log.warning("%s %s: %s", brand_id, url, page["fetch_error"])
    return None


def capture(existing: list[dict]) -> list[dict]:
    """Capture every official domain not already in `existing`; returns the merged list."""
    done = {r["domain"] for r in existing}
    targets = [(b["id"], d) for b in brands.load() for d in b["official_domains"] if d not in done]
    with ThreadPoolExecutor(4) as pool:
        new = [r for r in pool.map(lambda t: _capture_one(*t), targets) if r]
    return existing + new


@lru_cache(maxsize=1)
def load() -> list[dict]:
    return json.loads(REFERENCES_PATH.read_text()) if REFERENCES_PATH.exists() else []


def visual_match(final_url: str | None, fingerprints: dict | None) -> dict | None:
    """Closest official look-alike for a page on a non-official host, or None."""
    host = urlsplit(final_url or "").hostname or ""
    if not fingerprints or not host or brands.is_official(host):
        return None
    best = None
    for ref in load():
        if fingerprints.get("favicon_sha256") and fingerprints["favicon_sha256"] == ref["favicon_sha256"]:
            return {"brand": ref["brand"], "kind": "same_favicon", "reference_url": ref["final_url"],
                    "reference_screenshot": ref["screenshot_path"]}
        if fingerprints.get("dom_hash") and fingerprints["dom_hash"] == ref["dom_hash"]:
            return {"brand": ref["brand"], "kind": "same_template", "reference_url": ref["final_url"],
                    "reference_screenshot": ref["screenshot_path"]}
        if fingerprints.get("screenshot_dhash") and ref["screenshot_dhash"]:
            distance = hamming(fingerprints["screenshot_dhash"], ref["screenshot_dhash"])
            if distance <= LOOKALIKE_MAX_DISTANCE and (not best or distance < best["distance"]):
                best = {"brand": ref["brand"], "kind": "similar_screenshot", "distance": distance,
                        "reference_url": ref["final_url"], "reference_screenshot": ref["screenshot_path"]}
    return best


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    references = capture([r for r in load() if "domain" in r])
    REFERENCES_PATH.write_text(json.dumps(references, ensure_ascii=False, indent=2))
    print(f"{len(references)} references saved to {REFERENCES_PATH}")
