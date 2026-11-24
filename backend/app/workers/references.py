"""Visual references of the real brand sites, and matching a suspicious page against them (Simon).

A page that reuses an official favicon or page template while sitting on a non-official domain is
imitating that brand. Screenshot hashes are not used for matching: mobile screenshots of different
official sites (mostly white, cookie banners) differ by only 1-2 of 64 bits.

Capture references (visits every official domain once):  python -m app.workers.references
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from urllib.parse import urlsplit

from ..brand_match import is_official
from ..brands import load_registry
from ..config import BRANDS_PATH
from ..contracts import Fingerprints, VisualMatch

log = logging.getLogger("scamshield.references")

REFERENCES_PATH = BRANDS_PATH.parent / "references.json"


def _capture_one(brand_id: str, domain: str) -> dict | None:
    from .fetcher import fetch

    for url in (f"https://{domain}/", f"https://www.{domain}/"):
        page = fetch(url)
        # A block or challenge page would match every other block page, so it is not a reference.
        if page.fetch_error is None and page.fingerprints and page.page_kind == "content":
            fp = page.fingerprints
            return {"brand": brand_id, "domain": domain, "final_url": page.final_url, "title": page.title,
                    "screenshot_path": page.screenshot_path, "favicon_mmh3": fp.favicon_mmh3,
                    "favicon_sha256": fp.favicon_sha256, "dom_hash": fp.dom_hash,
                    "screenshot_dhash": fp.screenshot_dhash}
        log.warning("%s %s: %s %s", brand_id, url, page.page_kind, page.fetch_error)
    return None


def capture(existing: list[dict]) -> list[dict]:
    """Capture every official domain not already in `existing`; returns the merged list."""
    done = {r["domain"] for r in existing}
    targets = [(b.id, d) for b in load_registry().brands for d in b.official_domains if d not in done]
    with ThreadPoolExecutor(4) as pool:
        new = [r for r in pool.map(lambda t: _capture_one(*t), targets) if r]
    return existing + new


@lru_cache(maxsize=1)
def load() -> list[dict]:
    return json.loads(REFERENCES_PATH.read_text(encoding="utf-8")) if REFERENCES_PATH.exists() else []


def visual_match(final_url: str | None, fingerprints: Fingerprints | None) -> VisualMatch | None:
    """Official brand whose favicon or page template a page on a non-official host reuses."""
    host = urlsplit(final_url or "").hostname or ""
    if not fingerprints or not host or is_official(host):
        return None
    for ref in load():
        for kind, key in (("same_favicon", "favicon_sha256"), ("same_template", "dom_hash")):
            value = getattr(fingerprints, key)
            if value and value == ref.get(key):
                return VisualMatch(brand=ref["brand"], kind=kind, reference_url=ref.get("final_url"),
                                   reference_screenshot=ref.get("screenshot_path"))
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    references = capture([r for r in load() if "domain" in r])
    REFERENCES_PATH.write_text(json.dumps(references, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(references)} references saved to {REFERENCES_PATH}")
