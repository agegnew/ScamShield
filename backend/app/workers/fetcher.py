"""Page fetcher — SIMON OWNS THIS FILE.

Implement fetch() with Playwright (Chromium, headless) and return an Evidence.
The pipeline has already checked the first URL with assert_public_url().

Must do:
- New browser context per URL; no cookies; downloads, camera, mic, geolocation off.
- Check EVERY request host with safety.assert_public_url() inside page.route();
  abort anything that fails (a redirect can point at 127.0.0.1 or 169.254.169.254).
- Follow redirects (HTTP and JS) and record each hop in redirect_chain.
- Expand URL shorteners: the redirect chain does this if you follow it to the end.
- Screenshot to ARTIFACTS_DIR / "shots" / f"{sha1(url)}.png" and set
  screenshot_path to the path RELATIVE to ARTIFACTS_DIR ("shots/<hash>.png").
- title, text_excerpt (first ~2000 chars of visible text), http_status, final_url.
- forms: action, input types, field hints from name/id/placeholder/label/
  autocomplete (lower-cased). NEVER type into or submit a form.
- Time budget: ~20 s per URL. On timeout or error, return Evidence with
  fetch_error set — never raise for a dead site; the engine still scores the URL.

P1: fetch twice (desktop and mobile user agent) and flag differences (cloaking).
"""

from datetime import datetime, timezone

from ..contracts import Evidence


def fetch(url: str) -> Evidence:
    return Evidence(
        url=url,
        fetched_at=datetime.now(timezone.utc),
        fetch_error="fetcher not implemented yet",
    )
