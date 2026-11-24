"""Build one Evidence per URL (Simon): what the page showed (fetcher) and who owns and hosts it
(enrichment), plus the visual match against official sites and the cloaking check.

Enrichment runs even when the page is offline, so dead scam links still carry domain evidence.
The cloaking check (a second, desktop visit) runs only for live pages on non-official hosts;
turn it off with SCAMSHIELD_CLOAK_CHECK=0 to halve fetch time.
"""

import os
from urllib.parse import urlsplit

from ..brand_match import is_official
from ..contracts import Evidence
from . import cloaking, enrich, fetcher, references


def collect(url: str) -> Evidence:
    page = fetcher.fetch(url)
    if page.fetch_error and page.fetch_error.startswith("Blocked"):
        return page
    evidence = enrich.enrich(page)
    if page.fetch_error is None:
        update = {"visual_match": references.visual_match(page.final_url, page.fingerprints)}
        host = urlsplit(page.final_url or url).hostname or ""
        if os.environ.get("SCAMSHIELD_CLOAK_CHECK", "1") == "1" and not is_official(host):
            update["cloaking"] = cloaking.check(url, page)
        evidence = evidence.model_copy(update=update)
    return evidence
