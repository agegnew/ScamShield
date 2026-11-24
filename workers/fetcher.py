"""Open a URL the way a UAE phone user would and record what it shows.

Follows shorteners, HTTP, meta-refresh and JavaScript redirects, takes a screenshot and lists form fields
(types only, never values). Output matches the Evidence contract in README.md, minus enrichment.

Usage: python -m workers.fetcher https://bit.ly/xyz
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from workers.safety import UnsafeURL, check_url

SCREENSHOT_DIR = Path(__file__).resolve().parent.parent / "data" / "screenshots"
NAV_TIMEOUT_MS = 20_000
SETTLE_MS = 2_500
TEXT_LIMIT = 4_000

# Scam pages often show their real content only to phones with a local setup.
PROFILE = {
    "device": "iPhone 13",
    "locale": "ar-AE",
    "timezone_id": "Asia/Dubai",
    "extra_http_headers": {"Accept-Language": "ar-AE,ar;q=0.9,en-AE;q=0.8,en;q=0.7"},
}

FORM_FIELDS_JS = """
() => [...document.querySelectorAll('form, body')].map(root => {
  const inputs = [...root.querySelectorAll('input, select, textarea')]
    .filter(el => root.tagName === 'FORM' || !el.closest('form'))
    .filter(el => !['hidden', 'submit', 'button', 'image', 'reset'].includes(el.type))
    .map(el => [el.type, el.name, el.id, el.autocomplete, el.placeholder,
                el.getAttribute('aria-label'), el.inputMode, el.maxLength].join(' ').toLowerCase());
  return {action: root.tagName === 'FORM' ? (root.getAttribute('action') || '') : '', inputs};
}).filter(f => f.inputs.length)
"""

FIELD_KINDS = [
    ("password", ("password", "كلمة المرور", "كلمة السر")),
    ("card", ("cc-number", "card", "cardnumber", "cvv", "cvc", "cc-exp", "expiry", "البطاقة")),
    ("otp", ("otp", "one-time-code", "verification code", "رمز التحقق", "sms code")),
    ("emirates_id", ("emirates id", "emiratesid", "eid", "784-", "الهوية")),
    ("phone", ("tel", "phone", "mobile", "الهاتف", "الجوال")),
    ("email", ("email", "البريد")),
]


def classify_field(descriptor: str) -> str:
    for kind, hints in FIELD_KINDS:
        if any(hint in descriptor for hint in hints):
            return kind
    return "text"


def summarize_forms(raw_forms: list[dict], page_url: str) -> list[dict]:
    forms = []
    for form in raw_forms:
        kinds = sorted({classify_field(d) for d in form["inputs"]} - {"text"}) or ["text"]
        action = urljoin(page_url, form["action"]) if form["action"] else page_url
        forms.append({"type": kinds[0] if len(kinds) == 1 else "+".join(kinds), "fields": kinds, "action": action})
    return forms


def _screenshot_path(url: str) -> Path:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return SCREENSHOT_DIR / f"{stamp}_{hashlib.sha256(url.encode()).hexdigest()[:12]}.png"


def fetch(url: str) -> dict:
    result = {
        "url": url,
        "final_url": None,
        "redirect_chain": [],
        "http_status": None,
        "screenshot_path": None,
        "screenshot_sha256": None,
        "title": None,
        "text_excerpt": None,
        "forms": [],
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "ok",
        "error": None,
    }
    try:
        check_url(url)
    except UnsafeURL as exc:
        return {**result, "status": "blocked", "error": str(exc)}

    chain: list[dict] = []

    def guard(route):
        try:
            check_url(route.request.url)
        except UnsafeURL:
            return route.abort("blockedbyclient")
        route.continue_()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            **p.devices[PROFILE["device"]],
            locale=PROFILE["locale"],
            timezone_id=PROFILE["timezone_id"],
            extra_http_headers=PROFILE["extra_http_headers"],
            accept_downloads=False,
            permissions=[],
        )
        context.route("**/*", guard)
        page = context.new_page()

        def on_response(response):
            if response.request.is_navigation_request() and response.frame == page.main_frame:
                chain.append({"url": response.url, "status": response.status})

        page.on("response", on_response)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            page.wait_for_timeout(SETTLE_MS)
            try:
                page.wait_for_load_state("networkidle", timeout=5_000)
            except PlaywrightError:
                pass
            shot = _screenshot_path(url)
            page.screenshot(path=str(shot))
            text = page.evaluate("() => document.body ? document.body.innerText : ''") or ""
            result.update(
                final_url=page.url,
                http_status=chain[-1]["status"] if chain else (response.status if response else None),
                screenshot_path=str(shot),
                screenshot_sha256=hashlib.sha256(shot.read_bytes()).hexdigest(),
                title=page.title(),
                text_excerpt=" ".join(text.split())[:TEXT_LIMIT],
                forms=summarize_forms(page.evaluate(FORM_FIELDS_JS), page.url),
            )
        except PlaywrightError as exc:
            result.update(status="error", error=str(exc).splitlines()[0], final_url=page.url if page.url != "about:blank" else None)
        finally:
            browser.close()

    result["redirect_chain"] = chain
    if result["final_url"] and urlsplit(result["final_url"]).hostname != urlsplit(url).hostname:
        result["cross_domain_redirect"] = True
    return result


if __name__ == "__main__":
    for target in sys.argv[1:]:
        print(json.dumps(fetch(target), ensure_ascii=False, indent=2))
