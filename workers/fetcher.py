"""Open a URL the way a UAE phone user would and record what it shows.

Follows shorteners, HTTP, meta-refresh and JavaScript redirects, takes a screenshot and lists form fields
(types only, never values), and links that push remote-access apps or APK installs. Output follows backend/app/contracts.py Evidence, minus enrichment.
screenshot_path is relative to the artifacts dir, as the API serves it.

Usage: python -m workers.fetcher https://bit.ly/xyz
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from workers import fingerprint as fp
from workers.safety import UnsafeURL, Unresolvable, check_url

ARTIFACTS_DIR = Path(os.getenv("SCAMSHIELD_ARTIFACTS", Path(__file__).resolve().parent.parent / "backend" / "artifacts"))
SCREENSHOT_DIR = ARTIFACTS_DIR / "screenshots"
NAV_TIMEOUT_MS = 20_000
SETTLE_MS = 1_500
TEXT_LIMIT = 2_000

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
    .map(el => {
      const label = (el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`)) || el.closest('label');
      return {type: el.type || el.tagName.toLowerCase(),
              hint: [el.name, el.id, el.autocomplete, el.placeholder, el.getAttribute('aria-label'),
                     label ? label.innerText : ''].filter(Boolean).join(' ').toLowerCase().trim()};
    });
  return {action: root.tagName === 'FORM' ? (root.getAttribute('action') || '') : '', inputs};
}).filter(f => f.inputs.length)
"""

LINKS_JS = """
() => [...document.querySelectorAll('a[href], button, [onclick]')].slice(0, 500).map(el => ({
  href: el.href || el.getAttribute('onclick') || '', text: (el.innerText || '').trim().slice(0, 80)
}))
"""

# Scam scripts push victims to install remote-control apps or sideloaded APKs, then log in to their bank.
REMOTE_ACCESS = re.compile(r"anydesk|teamviewer|rustdesk|quicksupport|airdroid|supremo|ultraviewer|splashtop|"
                           r"remote\s*(support|desktop|access)", re.I)
APK = re.compile(r"\.apk(\b|$)|تحميل التطبيق|download (our |the )?app", re.I)


def download_signals(links: list[dict], text: str) -> list[dict]:
    signals = []
    for link in links:
        target = f"{link['href']} {link['text']}"
        if REMOTE_ACCESS.search(target):
            signals.append({"kind": "remote_access_link", "href": link["href"][:300], "text": link["text"]})
        elif APK.search(target):
            signals.append({"kind": "app_download_link", "href": link["href"][:300], "text": link["text"]})
    if match := REMOTE_ACCESS.search(text):
        signals.append({"kind": "remote_access_text", "href": None, "text": match.group(0)})
    return signals[:20]


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
    """FormInfo per form: HTML input types, hint words, and the sensitive kinds they ask for."""
    forms = []
    for form in raw_forms:
        descriptors = [f"{i['type']} {i['hint']}".lower() for i in form["inputs"]]
        sensitive = sorted({classify_field(d) for d in descriptors} - {"text"})
        hints = sorted({i["hint"][:60] for i in form["inputs"] if i["hint"]})
        forms.append({
            "action": urljoin(page_url, form["action"]) if form["action"] else page_url,
            "input_types": sorted({i["type"] for i in form["inputs"]}),
            "field_hints": sensitive + [h for h in hints if h not in sensitive][:20],
            "sensitive": sensitive,
        })
    return forms


def _screenshot_path(url: str) -> Path:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return SCREENSHOT_DIR / f"{stamp}_{hashlib.sha256(url.encode()).hexdigest()[:12]}.png"


def _favicon(context, page) -> bytes:
    try:
        icon_url = page.evaluate(fp.FAVICON_JS)
        check_url(icon_url)
        resp = context.request.get(icon_url, timeout=5_000, max_redirects=3)
        return resp.body() if resp.ok and len(resp.body()) < 500_000 else b""
    except (PlaywrightError, UnsafeURL):
        return b""


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
        "download_signals": [],
        "fingerprints": None,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "ok",
        "fetch_error": None,
    }
    try:
        check_url(url)
    except Unresolvable as exc:
        return {**result, "status": "offline", "fetch_error": str(exc)}
    except UnsafeURL as exc:
        return {**result, "status": "blocked", "fetch_error": str(exc)}

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
                page.wait_for_load_state("networkidle", timeout=3_000)
            except PlaywrightError:
                pass
            shot = _screenshot_path(url)
            page.screenshot(path=str(shot))
            text = page.evaluate("() => document.body ? document.body.innerText : ''") or ""
            html = page.content()
            png = shot.read_bytes()
            result.update(
                final_url=page.url,
                http_status=chain[-1]["status"] if chain else (response.status if response else None),
                screenshot_path=str(shot.relative_to(ARTIFACTS_DIR)),
                screenshot_sha256=hashlib.sha256(png).hexdigest(),
                title=page.title(),
                text_excerpt=" ".join(text.split())[:TEXT_LIMIT],
                forms=summarize_forms(page.evaluate(FORM_FIELDS_JS), page.url),
                download_signals=download_signals(page.evaluate(LINKS_JS), text),
                fingerprints={
                    **fp.favicon_hashes(_favicon(context, page)),
                    "dom_hash": fp.dom_hash(page.evaluate(fp.DOM_SHAPE_JS)),
                    "screenshot_dhash": fp.screenshot_dhash(png),
                    "tracking_ids": fp.tracking_ids(html),
                    "contacts": fp.contacts(text, html),
                },
            )
        except PlaywrightError as exc:
            result.update(status="error", fetch_error=str(exc).splitlines()[0], final_url=page.url if page.url != "about:blank" else None)
        finally:
            browser.close()

    result["redirect_chain"] = chain
    if result["final_url"] and urlsplit(result["final_url"]).hostname != urlsplit(url).hostname:
        result["cross_domain_redirect"] = True
    return result


if __name__ == "__main__":
    for target in sys.argv[1:]:
        print(json.dumps(fetch(target), ensure_ascii=False, indent=2))
