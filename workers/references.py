"""Visual references of the real brand sites, and matching a suspicious page against them.

A page that reuses an official favicon or page template while sitting on a non-official domain is imitating
that brand. Screenshot hashes are not used for matching: mobile screenshots of different official sites (mostly
white, cookie banners) differ by only 1-2 of 64 bits, so they cannot tell brands apart.

Usage: python -m workers.references        # capture missing references into data/references.json
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from workers import brands

log = logging.getLogger("references")

REFERENCES_PATH = Path(__file__).resolve().parent.parent / "data" / "references.json"


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
    """Official brand whose favicon or page template a page on a non-official host reuses, or None."""
    host = urlsplit(final_url or "").hostname or ""
    if not fingerprints or not host or brands.is_official(host):
        return None
    for ref in load():
        for kind, key in (("same_favicon", "favicon_sha256"), ("same_template", "dom_hash")):
            if fingerprints.get(key) and fingerprints[key] == ref[key]:
                return {"brand": ref["brand"], "kind": kind, "reference_url": ref["final_url"],
                        "reference_screenshot": ref["screenshot_path"]}
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    references = capture([r for r in load() if "domain" in r])
    REFERENCES_PATH.write_text(json.dumps(references, ensure_ascii=False, indent=2))
    print(f"{len(references)} references saved to {REFERENCES_PATH}")
