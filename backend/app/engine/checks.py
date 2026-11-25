"""Engine checks. Each takes the scoring context and returns Reasons (EN + AR).

Weights are points added to the 0-100 risk score (negative = lowers risk).
"""

import os
import re
import unicodedata
from dataclasses import dataclass, field

from ..brand_match import match_token
from ..brands import GENERIC_LABELS, HELPLINE_CLAIM, NO_TYPOSQUAT_LABELS, normalize_uae_phone
from ..contracts import Brand, Candidate, Evidence, Reason, ScamTheme
from ..urls import domain_label, registrable_domain
from . import feeds, model
from .lists import (
    GLOBAL_BRANDS,
    GOVERNMENT_ASNS,
    GOVERNMENT_NETWORKS,
    SUSPICIOUS_TLDS,
    URL_SHORTENERS,
    USER_CONTENT_HOSTS,
    VENDOR_TENANT_DOMAINS,
    top_domains,
)

HOMOGLYPHS = (("rn", "m"), ("vv", "w"), ("0", "o"), ("1", "l"), ("3", "e"), ("5", "s"))

# Points the URL model adds at p=1.0 is MODEL_WEIGHT / 2 (and removes at p=0).
# Tuned with scripts/evaluate.py; override with SCAMSHIELD_MODEL_WEIGHT to experiment.
MODEL_WEIGHT = int(os.getenv("SCAMSHIELD_MODEL_WEIGHT", "140"))


@dataclass
class Ctx:
    url: str
    host: str
    domain: str
    final_url: str
    final_host: str
    final_domain: str
    platform: str | None
    evidence: Evidence | None
    candidate: Candidate | None
    brands: list[Brand]
    themes: list[ScamTheme]
    use_feeds: bool
    kind: str | None = None  # page kind with today's patterns (page_kinds.effective_kind)
    brand_target: str | None = None
    notes: dict = field(default_factory=dict)

    @property
    def live_page(self) -> bool:
        """The fetcher saw a real page (not an error, a placeholder or nothing at all)."""
        ev = self.evidence
        if ev is None or ev.fetch_error or self.kind not in (None, "content"):
            return False
        return bool(ev.title or ev.text_excerpt or ev.forms)


def _r(code: str, weight: int, en: str, ar: str, ref: str | None = None) -> Reason:
    return Reason(code=code, weight=weight, text_en=en, text_ar=ar, evidence_ref=ref)


def _levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _brand_tokens(brand: Brand) -> set[str]:
    tokens = {t.lower() for t in brand.domain_tokens}
    tokens |= {domain_label(d).lower() for d in brand.official_domains}
    return {t for t in tokens if len(t) >= 3}


def is_maps_listing_link(url: str, host: str, candidate: Candidate | None) -> bool:
    """A Maps candidate whose URL is just the Google Maps page of the listing (no website)."""
    return (
        candidate is not None
        and candidate.source.value == "maps"
        and host.endswith("google.com")
        and "/maps" in url
    )


def _token_in(token: str, text: str) -> bool:
    if len(token) >= 5:
        return token in text
    return re.search(rf"(^|[.\-_/]){re.escape(token)}([.\-_/]|$)", text) is not None


def _without_own_address(text: str, ctx: "Ctx") -> str:
    """Error, for-sale and parking pages print the site's own address ("emiratespost-track.com | 522:
    Connection timed out"); the address is not the page claiming to be the brand."""
    for name in sorted({ctx.host, ctx.final_host, ctx.domain, ctx.final_domain} - {""}, key=len, reverse=True):
        text = re.sub(re.escape(name), " ", text, flags=re.I)
    return text


def _is_official(brand: Brand, host: str) -> bool:
    return any(host == d or host.endswith("." + d) for d in brand.official_domains)


COUNTRY_SUFFIX = re.compile(r"(?:com|co|net|org|gov)\.[a-z]{2}|[a-z]{2}")
# Endings used as typos of .com (netflix.co, paypal.cm) or handed out free: never a brand's country site.
TYPO_OR_FREE_SUFFIXES = {"co", "cm", "om", "cc", "ws", "tk", "ml", "ga", "cf", "gq"}


def _global_brand_in(ctx: Ctx) -> tuple[str, str] | None:
    """A worldwide brand name inside a domain that isn't the brand's or a popular site."""
    popular = top_domains()
    for host, domain in dict.fromkeys(((ctx.host, ctx.domain), (ctx.final_host, ctx.final_domain))):
        if not domain or (domain in popular and not ctx.platform):
            continue
        label, _, suffix = domain.partition(".")
        for token, officials in GLOBAL_BRANDS.items():
            if domain in officials:
                continue
            # The brand's own country site: exactly its name on a country ending (citibank.ae,
            # microsoft.ae, hsbc.com.eg). A scam needs more words (citibank-ae.com, paypal-verify.ae).
            if label == token and COUNTRY_SUFFIX.fullmatch(suffix) and suffix not in TYPO_OR_FREE_SUFFIXES:
                continue
            bounded = re.search(rf"(^|[^a-z]){token}([^a-z]|$)", host)
            if bounded or (len(token) >= 7 and token in host):
                return token, officials[0]
    return None


# ---- URL-only checks (work for dead sites too) -----------------------------


def top_site(ctx: Ctx) -> list[Reason]:
    if ctx.platform or ctx.final_domain not in top_domains():
        return []
    return [
        _r(
            "top_site",
            -45,
            f"Well-known website: {ctx.final_domain} is among the most visited sites",
            f"موقع معروف: {ctx.final_domain} من أكثر المواقع زيارة",
            "url",
        )
    ]


def threat_feed(ctx: Ctx) -> list[Reason]:
    if not ctx.use_feeds:
        return []
    for url, host in {(ctx.url, ctx.host), (ctx.final_url, ctx.final_host)}:
        # A host entry only counts for a site of its own: one reported Google Form, Dropbox file or
        # bit.ly link puts docs.google.com, dropbox.com or bit.ly in the feed's host list.
        shared = bool(ctx.platform) or host in USER_CONTENT_HOSTS or registrable_domain(host) in top_domains()
        hit = feeds.lookup(url, host, shared)
        if hit:
            kind, feed = hit
            ctx.notes["feed_kind"] = kind
            return [
                _r(
                    "threat_feed",
                    70 if kind == "url" else 50,
                    f"Listed as phishing by {feed}",
                    f"مُدرج كموقع تصيّد لدى {feed}",
                    "threat_feed",
                )
            ]
    return []


# Links that open a chat (wa.me/message/RJ2UYB55M77RP1): the random code says nothing about phishing.
CHAT_LINK_HOSTS = {"wa.me", "api.whatsapp.com", "chat.whatsapp.com", "t.me", "telegram.me"}


# Added by Google, ad networks and mailers (srsltid on every Google Shopping result): they say
# nothing about the site, and their random values read as phishing tokens to the URL model.
TRACKING_PARAM = re.compile(r"^(utm_\w+|srsltid|gclid|gbraid|wbraid|fbclid|msclkid|yclid|_gl|mc_cid|mc_eid|igshid)$", re.I)


def without_tracking(url: str) -> str:
    """The URL minus tracking parameters; everything else stays byte for byte as it was."""
    base, sep, rest = url.partition("?")
    if not sep:
        return url
    query, hash_, fragment = rest.partition("#")
    pieces = query.split("&")
    kept = [p for p in pieces if not TRACKING_PARAM.match(p.split("=", 1)[0])]
    if len(kept) == len(pieces):
        return url
    return base + ("?" + "&".join(kept) if kept else "") + hash_ + fragment


def url_model(ctx: Ctx) -> list[Reason]:
    if ctx.host.removeprefix("www.") in CHAT_LINK_HOSTS:
        return []
    p = model.phishing_probability(without_tracking(ctx.url))
    if p is None:
        return []
    ctx.notes["url_model_p"] = p
    pct = round(p * 100)
    weight = round(MODEL_WEIGHT * (p - 0.5))
    if weight >= 0:
        en = f"URL pattern looks like phishing ({pct}% by our URL model)"
        ar = f"نمط الرابط يشبه روابط التصيّد ({pct}٪ حسب نموذج الروابط)"
    else:
        en = f"URL pattern looks normal (phishing likelihood {pct}%)"
        ar = f"نمط الرابط يبدو طبيعيًا (احتمال التصيّد {pct}٪)"
    return [_r("url_model", weight, en, ar, "url")]


# Government domains (portal.moi.gov.qa, any .gov.ae) cannot be registered by a scammer: Qatar's
# Ministry of Interior is not imitating the UAE's.
GOVERNMENT_HOST = re.compile(r"\.(gov|mil)(\.[a-z]{2})?$")


def _own_name_space(host: str) -> bool:
    """A host whose name a scammer cannot pick: a government domain or a recruitment platform tenant."""
    from ..urls import registrable_domain as _reg

    return bool(GOVERNMENT_HOST.search(host)) or _reg(host) in VENDOR_TENANT_DOMAINS


def brand_lookalike(ctx: Ctx) -> list[Reason]:
    if any(_own_name_space(h) for h in (ctx.host, ctx.final_host) if h):
        return []
    by_id = {b.id: b for b in ctx.brands}
    for host in dict.fromkeys((ctx.host, ctx.final_host)):
        hit = match_token(host)
        if hit and hit[0] in by_id:
            brand, token = by_id[hit[0]], hit[1]
            official = brand.official_domains[0]
            ctx.brand_target = ctx.notes["domain_brand"] = brand.id
            return [
                _r(
                    "lookalike_domain",
                    35,
                    f"Domain uses '{token}' ({brand.name_en}) but is not the official {official}",
                    f"النطاق يستخدم «{token}» ({brand.name_ar}) لكنه ليس النطاق الرسمي {official}",
                    "url",
                )
            ]
        # One brand's official site is never a misspelling of another's (rakpolice.gov.ae vs adpolice).
        if any(_is_official(brand, host) for brand in ctx.brands):
            continue
        label = domain_label(host).lower()
        for brand in ctx.brands:
            for off in brand.official_domains:
                off_label = domain_label(off).lower()
                if (
                    len(off_label) < 5
                    or label == off_label
                    or off_label in GENERIC_LABELS
                    or off_label in NO_TYPOSQUAT_LABELS
                ):
                    continue
                folded = label
                for a, b in HOMOGLYPHS:
                    folded = folded.replace(a, b)
                dist = _levenshtein(label, off_label)
                # Two edits on a name of 7-8 letters already reach ordinary words and other companies'
                # names (akbank, aramix, talaat), so short names allow one edit only.
                if folded == off_label or 0 < dist <= (1 if len(off_label) < 9 else 2):
                    ctx.brand_target = ctx.notes["domain_brand"] = brand.id
                    return [
                        _r(
                            "typosquat",
                            40,
                            f"Domain '{label}' is a misspelling of {off}",
                            f"النطاق «{label}» تحريف لاسم {off}",
                            "url",
                        )
                    ]
    hit = _global_brand_in(ctx)
    if hit:
        token, official = hit
        ctx.notes["global_brand"] = token
        return [
            _r(
                "lookalike_domain",
                35,
                f"Domain uses the brand name '{token}' but is not {official}",
                f"النطاق يستخدم اسم العلامة «{token}» لكنه ليس {official}",
                "url",
            )
        ]
    if ctx.platform:
        text = ctx.url.lower()
        for brand in ctx.brands:
            for token in _brand_tokens(brand):
                if len(token) >= 4 and token in text:
                    ctx.brand_target = ctx.notes["domain_brand"] = brand.id
                    return [
                        _r(
                            "brand_on_free_platform",
                            35,
                            f"Uses the {brand.name_en} name on a free website platform "
                            f"({ctx.platform})",
                            f"يستخدم اسم {brand.name_ar} على منصة مواقع مجانية ({ctx.platform})",
                            "url",
                        )
                    ]
    return []


def _lookalike_letters(host: str) -> bool:
    """Punycode used to fake a Latin name (pаypal with a Cyrillic а), as opposed to a name written in
    its own script (الداخلية.امارات, the Ministry of Interior's Arabic domain)."""
    for label in host.split("."):
        if not label.startswith("xn--"):
            continue
        try:
            text = label.encode("ascii").decode("idna")
        except (UnicodeError, ValueError):
            return True
        scripts = set()
        for ch in text:
            if ch.isalpha():
                name = unicodedata.name(ch, "")
                scripts.add(name.split(" ")[0])
        if {"CYRILLIC", "GREEK"} & scripts or ("LATIN" in scripts and len(scripts) > 1):
            return True
    return False


def url_shape(ctx: Ctx) -> list[Reason]:
    reasons = []
    host = ctx.host
    if "xn--" in host and _lookalike_letters(host):
        reasons.append(
            _r(
                "punycode",
                15,
                "Domain uses look-alike international characters (punycode)",
                "النطاق يستخدم أحرفًا دولية مشابهة (Punycode)",
                "url",
            )
        )
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
        reasons.append(
            _r(
                "ip_host",
                25,
                "Link points to a bare IP address instead of a domain",
                "الرابط يشير إلى عنوان IP مباشرة بدلًا من اسم نطاق",
                "url",
            )
        )
    if host in URL_SHORTENERS:
        reasons.append(
            _r(
                "shortener",
                5,
                "Short link hides the real destination",
                "الرابط المختصر يخفي الوجهة الحقيقية",
                "url",
            )
        )
    tld = ctx.final_domain.rsplit(".", 1)[-1] if "." in ctx.final_domain else ""
    if tld in SUSPICIOUS_TLDS:
        reasons.append(
            _r(
                "suspicious_tld",
                8,
                f"Cheap domain ending often used in scams (.{tld})",
                f"امتداد نطاق رخيص يكثر استخدامه في الاحتيال (.{tld})",
                "url",
            )
        )
    if ctx.platform:
        reasons.append(
            _r(
                "free_platform",
                18,
                f"Hosted on a free website platform ({ctx.platform})",
                f"مستضاف على منصة مواقع مجانية ({ctx.platform})",
                "url",
            )
        )
    return reasons


# Form-field words are scored by the credential_form check; counting them as a scam theme too
# would double-count every ordinary checkout or login page.
FORM_FIELD_WORDS = {
    "otp", "cvv", "card number", "verification code", "one-time password", "enter your pin",
    "رمز التحقق", "رقم البطاقة", "الرقم السري", "كلمة المرور لمرة واحدة",
}
# Themes whose single words are already specific enough (anydesk, teamviewer, .apk).
DISTINCTIVE_THEMES = {"remote_access"}
# ...except these: every article about the Salik or RTA app says "download the app".
GENERIC_APP_PHRASES = {
    "download the app", "install the app", "security app", "screen share",
    "حمّل التطبيق", "تحميل التطبيق", "ثبّت التطبيق", "مشاركة الشاشة", "تطبيق الحماية",
}


def _theme_hits(text: str, theme: ScamTheme, url_mode: bool) -> str | None:
    """The matched wording if the theme applies, else None.

    A theme applies on a multi-word scam phrase ("pay dh3", "remove black points") or on two
    different keywords of the same theme. One generic word ("tickets", "refund", "الإقامة")
    appears on plenty of legitimate pages and is not enough on its own.
    """
    hits: list[str] = []
    for kw in theme.keywords_en:
        if kw in FORM_FIELD_WORDS:
            continue
        if url_mode:
            if " " not in kw.strip():
                continue  # single words in a URL path (/tickets, /refund) say nothing
            if any(v in text for v in (kw.replace(" ", ""), kw.replace(" ", "-"), kw.replace(" ", "_"))):
                hits.append(kw)
        elif re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", text):
            hits.append(kw)
    if not url_mode:
        hits += [kw for kw in theme.keywords_ar if kw not in FORM_FIELD_WORDS and kw in text]
    hits = list(dict.fromkeys(hits))
    if not hits:
        return None
    if theme.id in DISTINCTIVE_THEMES:
        # A named tool (AnyDesk, an .apk) is enough; generic app wording needs a second hit.
        specific = next((h for h in hits if h not in GENERIC_APP_PHRASES), None)
        if specific:
            return specific
        return f"{hits[0]} / {hits[1]}" if len(hits) >= 2 else None
    phrase = next((h for h in hits if " " in h.strip()), None)
    if phrase:
        return phrase
    if len(hits) >= 2:
        return f"{hits[0]} / {hits[1]}"
    return None


def scam_themes_in_url(ctx: Ctx) -> list[Reason]:
    text = ctx.url.lower()
    reasons = []
    for theme in ctx.themes:
        kw = _theme_hits(text, theme, url_mode=True)
        if kw:
            reasons.append(
                _r(
                    "scam_theme_url",
                    10,
                    f"Link wording matches a known scam type: {theme.name_en} ('{kw}')",
                    f"صياغة الرابط تطابق نوع احتيال معروف: {theme.name_ar} («{kw}»)",
                    "url",
                )
            )
    return reasons[:2]


# ---- Page checks (need Evidence from the fetcher) ---------------------------


def _page_names(brand: Brand) -> list[str]:
    """Brand names to look for in page text. Short ones ('du', Arabic 'تم' = 'was') are too common."""
    names = [brand.name_en.split(" (")[0].lower(), brand.name_ar]
    names += [domain_label(d).lower() for d in brand.official_domains]
    return [n for n in dict.fromkeys(names) if len(n.replace(" ", "")) >= 4 and n not in GENERIC_LABELS]


def _name_in_page(name: str, text: str, raw_text: str) -> bool:
    if name.isascii():
        return re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", text) is not None
    return re.search(rf"(?<!\w){re.escape(name)}(?!\w)", raw_text) is not None


def page_signals(ctx: Ctx) -> list[Reason]:
    ev = ctx.evidence
    if ev is None or ev.fetch_error:
        return []
    reasons: list[Reason] = []
    raw_text = f"{ev.title or ''} {ev.text_excerpt or ''}"
    text = raw_text.lower()

    remote = next((s for s in ev.download_signals if s.kind.startswith("remote_access")), None)
    if remote:
        what = remote.text or remote.href or "remote access"
        reasons.append(
            _r(
                "remote_access",
                30,
                f"Page pushes a remote-access app ('{what}')",
                f"الصفحة تدفع لتثبيت تطبيق تحكم عن بعد («{what}»)",
                "download_signals",
            )
        )
    apk = next((s for s in ev.download_signals if s.kind == "app_download_link"), None)
    if apk:
        reasons.append(
            _r(
                "app_download",
                20,
                f"Page asks you to install an app outside the app store ('{apk.text or apk.href}')",
                f"الصفحة تطلب تثبيت تطبيق من خارج متجر التطبيقات («{apk.text or apk.href}»)",
                "download_signals",
            )
        )

    theme_reasons = []
    for theme in ctx.themes:
        kw = _theme_hits(text, theme, url_mode=False)
        if not kw:
            continue
        if theme.id == "remote_access":
            if not remote:
                reasons.append(
                    _r(
                        "remote_access",
                        30,
                        f"Page asks you to install a remote-access app or APK ('{kw}')",
                        f"الصفحة تطلب تثبيت تطبيق تحكم عن بعد أو ملف APK («{kw}»)",
                        "text_excerpt",
                    )
                )
        else:
            theme_reasons.append(
                _r(
                    "scam_theme_page",
                    12,
                    f"Page text matches a known scam type: {theme.name_en} ('{kw}')",
                    f"نص الصفحة يطابق نوع احتيال معروف: {theme.name_ar} («{kw}»)",
                    "text_excerpt",
                )
            )
    reasons += theme_reasons[:2]

    asks_en, asks_ar = [], []
    for form in ev.forms:
        hints = " ".join(form.field_hints).lower()
        kinds = set(form.sensitive)
        if "password" in form.input_types or "password" in hints or "password" in kinds:
            asks_en.append("a password"), asks_ar.append("كلمة المرور")
        if "card" in kinds or re.search(r"card|cvv|cvc|expiry|credit", hints):
            asks_en.append("card details"), asks_ar.append("بيانات البطاقة")
        if "otp" in kinds or re.search(r"otp|one.time|verification code|sms code", hints):
            asks_en.append("a one-time code"), asks_ar.append("رمز التحقق")
        if "emirates_id" in kinds:
            asks_en.append("your Emirates ID"), asks_ar.append("رقم الهوية الإماراتية")
    # Card, one-time code or Emirates ID: what scams are after. A password alone is every login page.
    ctx.notes["asks_payment"] = any(a != "a password" for a in asks_en)
    if asks_en:
        en = ", ".join(dict.fromkeys(asks_en))
        ar = " و".join(dict.fromkeys(asks_ar))
        reasons.append(
            _r("credential_form", 20, f"Page asks for {en}", f"الصفحة تطلب {ar}", "forms")
        )

    # "Presents itself as" = the brand is in the page title, or the page names the brand AND asks
    # for sensitive data. A blog or news page that only mentions TAMM is not impersonating it.
    title_raw = _without_own_address(ev.title or "", ctx)
    page_raw = _without_own_address(raw_text, ctx)
    asks_sensitive = bool(asks_en)
    ctx.notes["asks_sensitive"] = asks_sensitive
    ctx.notes["official_claim"] = bool(OFFICIAL_CLAIM.search(raw_text[:1500]))
    # A parked or for-sale page names the domain it sits on ("emiratespost.com is for sale");
    # that is not the page presenting itself as the brand.
    claims_allowed = (ctx.kind or "") not in HOLDING_PAGES
    for brand in ctx.brands:
        if not claims_allowed or _is_official(brand, ctx.final_host) or _own_name_space(ctx.final_host):
            continue
        names = _page_names(brand)
        hit = next((n for n in names if _name_in_page(n, title_raw.lower(), title_raw)), None)
        if hit is None and asks_sensitive:
            hit = next((n for n in names if _name_in_page(n, page_raw.lower(), page_raw)), None)
        if hit:
            ctx.brand_target = ctx.brand_target or brand.id
            ctx.notes.setdefault("page_brands", set()).add(brand.id)
            reasons.append(
                _r(
                    "brand_on_wrong_domain",
                    20,
                    f"Page presents itself as {brand.name_en} on a non-official domain",
                    f"الصفحة تقدّم نفسها على أنها {brand.name_ar} على نطاق غير رسمي",
                    "screenshot",
                )
            )
            break

    if ev.visual_match:
        brand = next((b for b in ctx.brands if b.id == ev.visual_match.brand), None)
        if brand:
            ctx.brand_target = ctx.brand_target or brand.id
            ctx.notes.setdefault("page_brands", set()).add(brand.id)
            what_en ="favicon" if ev.visual_match.kind == "same_favicon" else "page template"
            what_ar = "أيقونة" if ev.visual_match.kind == "same_favicon" else "قالب صفحة"
            reasons.append(
                _r(
                    "visual_match",
                    35,
                    f"Page reuses the official {brand.name_en} {what_en} on a non-official domain",
                    f"الصفحة تعيد استخدام {what_ar} {brand.name_ar} الرسمي على نطاق غير رسمي",
                    "fingerprints",
                )
            )

    warned_by = _platform_warning(ev.title or "", ev.text_excerpt or "")
    if warned_by:
        reasons.append(
            _r(
                "platform_warning",
                50,
                f"{warned_by} already shows visitors a phishing warning for this link",
                f"تعرض {warned_by} بالفعل تحذيرًا من التصيّد لزوار هذا الرابط",
                "screenshot",
            )
        )

    if ev.cloaking and ev.cloaking.signals:
        strong = {"different_destination", "forms_hidden_from_desktop", "different_page"}
        weight = 25 if strong & set(ev.cloaking.signals) else 10
        listed = ", ".join(s.replace("_", " ") for s in ev.cloaking.signals)
        reasons.append(
            _r(
                "cloaking",
                weight,
                f"Shows different content to a foreign desktop visitor than to a UAE phone ({listed})",
                f"يعرض محتوى مختلفًا لزائر من حاسوب خارج الدولة عن هاتف داخل الإمارات ({listed})",
                "cloaking",
            )
        )

    if ctx.final_domain and ctx.final_domain != ctx.domain:
        reasons.append(
            _r(
                "cross_domain_redirect",
                10,
                f"Link redirects to a different site ({ctx.final_host})",
                f"الرابط يحوّل إلى موقع مختلف ({ctx.final_host})",
                "redirect_chain",
            )
        )
    return reasons


def _platform_warning(title: str, text: str) -> str | None:
    """The interstitial a security service shows instead of a reported page."""
    t, x = title.lower(), text[:400].lower()
    if ("phishing" in t and "cloudflare" in t) or "suspected phishing site ahead" in x:
        return "Cloudflare"
    if re.search(r"the account that created this link has been|there might be a problem with the requested link|"
                 r"this link has been (flagged|disabled|blocked)", f"{t} {x}"):
        return "Bitly"
    if "deceptive site ahead" in f"{t} {x}":
        return "Google Safe Browsing"
    return None


def search_rank(ctx: Ctx) -> list[Reason]:
    """An organic Google result for the brand's own search. Scam pages buy ads (search_ad) far more
    often than they rank on the first page, so this counts a little in the site's favour, unless
    there is hard evidence (combine() then drops it)."""
    cand = ctx.candidate
    if cand is None or cand.source.value != "search":
        return []
    position = cand.extra.details.get("position")
    if not isinstance(position, int) or position > 10:
        return []
    query = cand.query or ""
    return [
        _r(
            "organic_search",
            -20,
            f"Ranks #{position} in Google's organic results for '{query}' (scam pages usually buy ads instead)",
            f"يظهر في المرتبة {position} من نتائج Google العادية للبحث «{query}» (صفحات الاحتيال تشتري الإعلانات عادةً)",
            "candidate.extra.details",
        )
    ]


def government_network(ctx: Ctx) -> list[Reason]:
    """Hosted on a UAE government network, where scammers cannot put a site (e.g. adpolice.ae,
    an Abu Dhabi Police alias on the Abu Dhabi Digital Authority network)."""
    ev = ctx.evidence
    if ev is None or ev.shared_hosting:
        return []
    org = (ev.hosting_org or "").lower()
    if ev.asn not in GOVERNMENT_ASNS and not any(name in org for name in GOVERNMENT_NETWORKS):
        return []
    return [
        _r(
            "government_network",
            -60,
            f"Hosted on a UAE government network ({ev.hosting_org or f'AS{ev.asn}'})",
            f"مستضاف على شبكة حكومية إماراتية ({ev.hosting_org or f'AS{ev.asn}'})",
            "asn",
        )
    ]


def domain_age(ctx: Ctx) -> list[Reason]:
    from .core import domain_age_days  # local import avoids a cycle

    days = domain_age_days(ctx.evidence)
    if days is None:
        return []
    if days <= 30:
        return [
            _r(
                "new_domain",
                25 if days <= 7 else 18,
                f"Domain registered {days} days ago",
                f"تم تسجيل النطاق منذ {days} يوم",
                "rdap.created",
            )
        ]
    if days >= 730:
        years = days // 365
        return [
            _r(
                "old_domain",
                -10,
                f"Domain registered {years} years ago",
                f"تم تسجيل النطاق منذ {years} سنوات",
                "rdap.created",
            )
        ]
    return []


def helpline(ctx: Ctx) -> list[Reason]:
    cand = ctx.candidate
    if cand is None or not cand.extra.phone:
        return []
    listing = (cand.extra.listing_name or "").lower()
    # A shop or branch ("ETISALAT STORE, E& DMCC MARINA") has its own number; only a listing that
    # presents itself as customer service is claiming to be the brand's helpline.
    flagged = "helpline_not_official" in (cand.extra.details.get("flags") or [])
    if not flagged and not HELPLINE_CLAIM.search(listing):
        return []
    phone = normalize_uae_phone(cand.extra.phone)
    for brand in ctx.brands:
        if not brand.helplines:
            continue
        if cand.extra.brand:
            if brand.id != cand.extra.brand:  # the radar already knows which brand it named
                continue
        else:
            names = [brand.name_en.split(" (")[0].lower()] + list(_brand_tokens(brand))
            if not any(n and len(n.strip("-")) >= 3 and _token_in(n.strip("-"), listing) for n in names):
                continue
        if phone in {normalize_uae_phone(h) for h in brand.helplines}:
            return []
        ctx.brand_target = ctx.brand_target or brand.id
        official = ", ".join(brand.helplines)
        return [
            _r(
                "helpline_mismatch",
                35,
                f"Listing phone {cand.extra.phone} is not an official {brand.name_en} helpline "
                f"({official})",
                f"رقم الهاتف {cand.extra.phone} ليس رقم خدمة رسميًا لـ{brand.name_ar} ({official})",
                "candidate.extra.phone",
            )
        ]
    return []


AI_STRONG = 0.85  # confidence for the full weight
AI_SOME = 0.6  # below this the answer is ignored


def ai_review(ctx: Ctx) -> list[Reason]:
    """Claude's second look at a borderline page, when the worker asked for one (workers/ai_review.py).
    Only a confident answer counts; combine() lets hard evidence overrule a clearing answer."""
    ai = ctx.evidence.ai_review if ctx.evidence else None
    if ai is None or ai.verdict == "unsure" or ai.confidence < AI_SOME:
        return []
    strong = ai.confidence >= AI_STRONG
    if ai.verdict == "scam":
        if ai.impersonates and not ctx.brand_target and any(b.id == ai.impersonates for b in ctx.brands):
            ctx.brand_target = ai.impersonates
        return [
            _r(
                "ai_flagged",
                30 if strong else 15,
                f"AI review ({round(ai.confidence * 100)}% sure): {ai.explanation_en}",
                f"مراجعة الذكاء الاصطناعي (بثقة {round(ai.confidence * 100)}٪): {ai.explanation_ar}",
                "screenshot",
            )
        ]
    return [
        _r(
            "ai_cleared",
            -30 if strong else -15,
            f"AI review ({round(ai.confidence * 100)}% sure it is legitimate): {ai.explanation_en}",
            f"مراجعة الذكاء الاصطناعي (بثقة {round(ai.confidence * 100)}٪ أنه سليم): {ai.explanation_ar}",
            "screenshot",
        )
    ]


CHECKS = (
    top_site,
    threat_feed,
    url_model,
    brand_lookalike,
    url_shape,
    scam_themes_in_url,
    page_signals,
    search_rank,
    government_network,
    domain_age,
    helpline,
    ai_review,
)


# ---- Combination rules (run once, after every check) -----------------------

PAGE_IMPERSONATION = {"brand_on_wrong_domain", "visual_match"}
# The domain name itself claims a brand it does not own.
DOMAIN_BRAND_CLAIM = {"lookalike_domain", "typosquat"}
# Reasons that lower risk because a site looks ordinary or established.
TRUST_DISCOUNTS = {"url_model", "old_domain"}
# The page says it is the official or government site ("Official Government Portal", "الموقع الرسمي").
OFFICIAL_CLAIM = re.compile(r"\bofficial\b|\bgovernment\b|\bministry\b|رسمي|حكوم|وزارة", re.I)
# Firm, specific evidence of a scam. An unusual URL, a cheap domain ending or a login form are not:
# plenty of honest sites have them (the hackathon's own submission site had all three).
HARD_EVIDENCE = PAGE_IMPERSONATION | {"threat_feed", "platform_warning", "remote_access", "app_download", "ai_flagged"}
# Anything that points to a scam; a live page with none of them is probably an unrelated business.
SCAM_SIGNS = HARD_EVIDENCE | {"scam_theme_page", "helpline_mismatch", "cloaking"}
# Hard evidence an AI "looks legitimate" answer may not outweigh.
AI_CANNOT_CLEAR = {"threat_feed", "platform_warning", "cloaking", "visual_match", "remote_access", "app_download"}
# The domain shows no site of its own. There is nothing to take down yet, so it is watched
# (SUSPICIOUS) instead of reported, unless there is hard evidence or the page asks for payment data.
HOLDING_PAGES = {
    "parked": ("parked-domain", "صفحة نطاق محجوز"),
    "for_sale": ("domain-for-sale", "صفحة بيع النطاق"),
    "expired": ("expired or suspended domain", "صفحة نطاق منتهي الصلاحية أو موقوف"),
    "coming_soon": ("coming-soon", "صفحة «قريبًا»"),
    "default_host_page": ("default hosting", "صفحة الاستضافة الافتراضية"),
    "error": ("server-error", "صفحة خطأ في الخادم"),
    "offline": ("", ""),  # no site answers at that name (fetch error): worded on its own below
}
HOLDING_PAGE_CAP = 60
# With the page in front of us, the page decides: the URL model's view adds at most this much.
LIVE_PAGE_MODEL_CAP = 20
# No brand named anywhere (domain, page, Maps listing, AI) and no hard evidence: watched, not reported.
NO_BRAND_CAP = 60


def _cap(reasons: list[Reason], cap: int, code: str, en: str, ar: str) -> list[Reason]:
    total = sum(r.weight for r in reasons)
    if total <= cap:
        return reasons
    return reasons + [_r(code, cap - total, en, ar, "screenshot" if code == "holding_page" else None)]


def combine(ctx: Ctx, reasons: list[Reason]) -> list[Reason]:
    """Rules that read several checks at once. Weights stay additive: the score is their sum."""
    codes = {r.code for r in reasons}

    if codes & HARD_EVIDENCE:
        reasons = [r for r in reasons if r.code != "organic_search"]  # ranking excuses no hard evidence
        codes.discard("organic_search")
    if codes & AI_CANNOT_CLEAR:
        # A phishing-feed hit, cloaking, a copied official template or a pushed app outweighs an
        # AI answer that the page looks legitimate.
        reasons = [r for r in reasons if r.code != "ai_cleared"]
        codes.discard("ai_cleared")
    if "ai_cleared" in codes and not ctx.notes.get("domain_brand"):
        # The brand came only from the page's words (a news article about an Abu Dhabi Police
        # fine discount) and the AI found no impersonation: don't tag the site with that brand.
        ctx.brand_target = None

    if codes & PAGE_IMPERSONATION or ctx.notes.get("feed_kind") == "url":
        # The page itself pretends to be the brand, or this exact URL is a reported phishing page.
        # A normal-looking URL and an old domain are how such pages hide (phishing kits are often
        # planted on hacked, years-old business sites), so they no longer count in the site's favour.
        reasons = [r for r in reasons if r.code not in TRUST_DISCOUNTS or r.weight >= 0]
    elif codes & DOMAIN_BRAND_CLAIM and ctx.evidence is None:
        # URL only (no page to look at): the domain name claims a brand it doesn't own (roblox.ly,
        # paypal-verify.com). The URL model's "looks normal" mostly reflects a short clean URL, which
        # says nothing against that claim. With a page, the page decides (car parts on moi-portal.com).
        reasons = [r for r in reasons if r.code != "url_model" or r.weight >= 0]
    if ctx.notes.get("feed_kind") == "url":
        reasons = [r for r in reasons if r.code != "government_network"]  # reported phishing on a hacked site
    if ctx.live_page:
        # The URL model only reads the address. Once the page itself is in front of us, an unusual
        # address (podium.aevsoft.cc/HackathonMngtWebApp/...) is a hint, not the verdict.
        reasons = [
            r.model_copy(update={"weight": LIVE_PAGE_MODEL_CAP})
            if r.code == "url_model" and r.weight > LIVE_PAGE_MODEL_CAP
            else r
            for r in reasons
        ]
    if codes & PAGE_IMPERSONATION:
        domain_brand = ctx.notes.get("domain_brand")
        brand = next((b for b in ctx.brands if b.id == domain_brand), None)
        # A business that merely shares the name ("Tamm Real Estate", the ad-fraud firm AdPolice)
        # is not confirmed: the page must also claim official status or ask for sensitive data.
        claims_more = ctx.notes.get("official_claim") or ctx.notes.get("asks_sensitive")
        if brand and domain_brand in ctx.notes.get("page_brands", set()) and claims_more:
            reasons.append(
                _r(
                    "impersonation_confirmed",
                    20,
                    f"Both the domain name and the page claim to be {brand.name_en}, "
                    "on a domain it does not own",
                    f"اسم النطاق ومحتوى الصفحة ينتحلان معًا صفة {brand.name_ar} على نطاق لا تملكه",
                    "screenshot",
                )
            )

    ev = ctx.evidence
    named = next((b for b in ctx.brands if b.id == ctx.notes.get("domain_brand")), None)
    if named and ctx.live_page and not codes & SCAM_SIGNS and not ctx.notes.get("asks_payment"):
        raw = _without_own_address(f"{ev.title or ''} {ev.text_excerpt or ''}", ctx)
        if not any(_name_in_page(n, raw.lower(), raw) for n in _page_names(named)):
            # A working site that never names the brand and shows no scam sign: a business whose name
            # happens to be close to the brand's (Aramix Concreto on aramix.site, ICP株式会社 on
            # icp-online.xyz). The name match was a coincidence, so it and the URL model's view of
            # that name no longer count.
            claim = sum(r.weight for r in reasons if r.code in DOMAIN_BRAND_CLAIM)
            url_view = sum(max(0, r.weight) for r in reasons if r.code == "url_model")
            reasons.append(
                _r(
                    "unrelated_content",
                    -(claim + url_view),
                    f"The site is live but never mentions {named.name_en} and shows no sign of a "
                    "scam (no payment or ID form, no scam wording), so the name looks like a coincidence",
                    f"الموقع يعمل لكنه لا يذكر {named.name_ar} ولا يُظهر أي علامة احتيال "
                    "(لا نموذج دفع أو هوية، ولا عبارات احتيال)، لذا يبدو تشابه الاسم مصادفة",
                    "screenshot",
                )
            )
            ctx.brand_target = None
            ctx.notes["brand_refuted"] = True

    codes = {r.code for r in reasons}
    firm = bool(codes & HARD_EVIDENCE) or bool(ctx.notes.get("asks_payment"))
    holding = HOLDING_PAGES.get(ctx.kind or "") if ev else None
    if holding and not firm:
        kind_en, kind_ar = holding
        if ctx.kind == "offline":
            en = ("No web site answers at this address now, so there is nothing to take down: "
                  "it is watched rather than reported")
            ar = "لا يوجد موقع يعمل على هذا العنوان الآن، فلا شيء لإزالته: يبقى تحت المراقبة بدل الإبلاغ عنه"
        else:
            en = (f"Shows only a {kind_en} page: there is no site of its own on it now, "
                  "so it is watched rather than reported")
            ar = f"تعرض {kind_ar} فقط: لا يوجد عليه موقع فعلي الآن، لذا يبقى تحت المراقبة بدل الإبلاغ عنه"
        reasons = _cap(reasons, HOLDING_PAGE_CAP, "holding_page", en, ar)
    brand_claim = ctx.brand_target or ctx.notes.get("global_brand")
    if not brand_claim and not firm:
        reasons = _cap(
            reasons,
            NO_BRAND_CAP,
            "no_brand_claim",
            "Names no brand and shows no firm sign of a scam (no reported phishing, copied page or "
            "security warning), so it is watched rather than reported",
            "لا ينتحل أي علامة ولا يُظهر علامة احتيال مؤكدة (لا بلاغ تصيّد ولا صفحة منسوخة ولا تحذير أمني)، "
            "لذا يبقى تحت المراقبة بدل الإبلاغ عنه",
        )
    return reasons
