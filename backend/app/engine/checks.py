"""Engine checks. Each takes the scoring context and returns Reasons (EN + AR).

Weights are points added to the 0-100 risk score (negative = lowers risk).
"""

import os
import re
from dataclasses import dataclass, field

from ..brand_match import match_token
from ..brands import normalize_uae_phone
from ..contracts import Brand, Candidate, Evidence, Reason, ScamTheme
from ..urls import domain_label
from . import feeds, model
from .lists import GLOBAL_BRANDS, SUSPICIOUS_TLDS, URL_SHORTENERS, top_domains

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
    brand_target: str | None = None
    notes: dict = field(default_factory=dict)


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


def _is_official(brand: Brand, host: str) -> bool:
    return any(host == d or host.endswith("." + d) for d in brand.official_domains)


def _global_brand_in(ctx: Ctx) -> tuple[str, str] | None:
    """A worldwide brand name inside a domain that isn't the brand's or a popular site."""
    popular = top_domains()
    for host, domain in dict.fromkeys(((ctx.host, ctx.domain), (ctx.final_host, ctx.final_domain))):
        if not domain or (domain in popular and not ctx.platform):
            continue
        for token, officials in GLOBAL_BRANDS.items():
            if domain in officials:
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
        hit = feeds.lookup(url, host, bool(ctx.platform))
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


def url_model(ctx: Ctx) -> list[Reason]:
    p = model.phishing_probability(ctx.url)
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


def brand_lookalike(ctx: Ctx) -> list[Reason]:
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
        label = domain_label(host).lower()
        for brand in ctx.brands:
            if _is_official(brand, host):
                continue
            for off in brand.official_domains:
                off_label = domain_label(off).lower()
                if len(off_label) < 5 or label == off_label:
                    continue
                folded = label
                for a, b in HOMOGLYPHS:
                    folded = folded.replace(a, b)
                dist = _levenshtein(label, off_label)
                if folded == off_label or 0 < dist <= (1 if len(off_label) < 7 else 2):
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


def url_shape(ctx: Ctx) -> list[Reason]:
    reasons = []
    host = ctx.host
    if "xn--" in host:
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
    phrase = next((h for h in hits if " " in h.strip()), None)
    if phrase:
        return phrase
    if len(hits) >= 2:
        return f"{hits[0]} / {hits[1]}"
    return hits[0] if theme.id in DISTINCTIVE_THEMES else None


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
    return [n for n in dict.fromkeys(names) if len(n.replace(" ", "")) >= 4]


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
    if asks_en:
        en = ", ".join(dict.fromkeys(asks_en))
        ar = " و".join(dict.fromkeys(asks_ar))
        reasons.append(
            _r("credential_form", 20, f"Page asks for {en}", f"الصفحة تطلب {ar}", "forms")
        )

    # "Presents itself as" = the brand is in the page title, or the page names the brand AND asks
    # for sensitive data. A blog or news page that only mentions TAMM is not impersonating it.
    title_raw = ev.title or ""
    asks_sensitive = bool(asks_en)
    for brand in ctx.brands:
        if _is_official(brand, ctx.final_host):
            continue
        names = _page_names(brand)
        hit = next((n for n in names if _name_in_page(n, title_raw.lower(), title_raw)), None)
        if hit is None and asks_sensitive:
            hit = next((n for n in names if _name_in_page(n, text, raw_text)), None)
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


CHECKS = (
    top_site,
    threat_feed,
    url_model,
    brand_lookalike,
    url_shape,
    scam_themes_in_url,
    page_signals,
    domain_age,
    helpline,
)


# ---- Combination rules (run once, after every check) -----------------------

PAGE_IMPERSONATION = {"brand_on_wrong_domain", "visual_match"}
# Reasons that lower risk because a site looks ordinary or established.
TRUST_DISCOUNTS = {"url_model", "old_domain"}
# Signs of an active scam: a page showing them is not a mere placeholder, whatever it says.
ACTIVE_SCAM = PAGE_IMPERSONATION | {"credential_form", "remote_access", "app_download", "cloaking"}
# The domain is held but shows no site of its own. There is nothing to take down yet, so it is
# watched (SUSPICIOUS) instead of reported, unless a phishing feed already lists it.
HOLDING_PAGES = {
    "parked": ("parked-domain", "صفحة نطاق محجوز"),
    "for_sale": ("domain-for-sale", "صفحة بيع النطاق"),
    "expired": ("expired-domain", "صفحة نطاق منتهي الصلاحية"),
    "coming_soon": ("coming-soon", "صفحة «قريبًا»"),
    "default_host_page": ("default hosting", "صفحة الاستضافة الافتراضية"),
}
HOLDING_PAGE_CAP = 60


def combine(ctx: Ctx, reasons: list[Reason]) -> list[Reason]:
    """Rules that read several checks at once. Weights stay additive: the score is their sum."""
    codes = {r.code for r in reasons}

    if codes & PAGE_IMPERSONATION or ctx.notes.get("feed_kind") == "url":
        # The page itself pretends to be the brand, or this exact URL is a reported phishing page.
        # A normal-looking URL and an old domain are how such pages hide (phishing kits are often
        # planted on hacked, years-old business sites), so they no longer count in the site's favour.
        reasons = [r for r in reasons if r.code not in TRUST_DISCOUNTS or r.weight >= 0]
    if codes & PAGE_IMPERSONATION:
        domain_brand = ctx.notes.get("domain_brand")
        brand = next((b for b in ctx.brands if b.id == domain_brand), None)
        if brand and domain_brand in ctx.notes.get("page_brands", set()):
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
    holding = HOLDING_PAGES.get(ev.page_kind or "") if ev and not ev.fetch_error else None
    if holding and "threat_feed" not in codes and not codes & ACTIVE_SCAM:
        total = sum(r.weight for r in reasons)
        if total > HOLDING_PAGE_CAP:
            kind_en, kind_ar = holding
            reasons.append(
                _r(
                    "holding_page",
                    HOLDING_PAGE_CAP - total,
                    f"Shows only a {kind_en} page: the domain is registered but not used yet, "
                    "so it is watched rather than reported",
                    f"تعرض {kind_ar} فقط: النطاق مسجّل لكنه غير مستخدم بعد، "
                    "لذا يبقى تحت المراقبة بدل الإبلاغ عنه",
                    "screenshot",
                )
            )
    return reasons
