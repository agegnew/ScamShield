"""Fake cases for building the UI before the real radar and engine exist.

Scam domains use the reserved .test TLD and documentation IP ranges
(203.0.113.0/24, 198.51.100.0/24) so they can never point at a real site.
Real official domains appear only as LEGIT examples.
"""

from datetime import datetime, timedelta, timezone

from ..api_models import Case, Decision, Metrics
from ..brands import official_brand_for_domain
from ..contracts import (
    Candidate,
    CandidateExtra,
    Evidence,
    FormInfo,
    Label,
    Rdap,
    Reason,
    RedirectHop,
    Source,
    Verdict,
)
from ..messages import official_domain_reason
from ..urls import hostname

UAE = timezone(timedelta(hours=4))
MODEL = "mock-0"
SCREENSHOT = "mock/screenshot.svg"


def _at(hour: int, minute: int, day: int = 24) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=UAE)


def _utc(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 11, day, hour, 0, tzinfo=timezone.utc)


def _r(code: str, weight: int, en: str, ar: str, ref: str | None = None) -> Reason:
    return Reason(code=code, weight=weight, text_en=en, text_ar=ar, evidence_ref=ref)


CARD_OTP = _r(
    "card_otp_form",
    20,
    "Form asks for card number, CVV and a one-time code",
    "النموذج يطلب رقم البطاقة ورمز CVV ورمز التحقق لمرة واحدة",
    "forms",
)

REGISTRAR_A = ("Example Registrar Inc.", "abuse@registrar.test")
REGISTRAR_B = ("Sample Registrar LLC", "abuse@sample-registrar.test")
HOST_A = ("203.0.113.45", 64500, "Example Hosting Ltd.", "abuse@hosting.test")
HOST_B = ("198.51.100.23", 64501, "Sample Cloud LLC", "abuse@cloud.test")


def _evidence(
    url: str,
    seen: datetime,
    *,
    title: str,
    text: str,
    forms: list[FormInfo] | None = None,
    registrar: tuple[str, str] | None = None,
    created: datetime | None = None,
    host: tuple[str, int, str, str] | None = None,
    redirects: list[RedirectHop] | None = None,
    final_url: str | None = None,
) -> Evidence:
    return Evidence(
        url=url,
        final_url=final_url or url,
        redirect_chain=redirects or [],
        http_status=200,
        screenshot_path=SCREENSHOT,
        title=title,
        text_excerpt=text,
        forms=forms or [],
        rdap=Rdap(created=created, registrar=registrar[0], abuse_email=registrar[1])
        if registrar
        else None,
        ip=host[0] if host else None,
        asn=host[1] if host else None,
        hosting_org=host[2] if host else None,
        hosting_abuse_email=host[3] if host else None,
        fetched_at=seen + timedelta(minutes=1),
    )


def _case(
    case_id: str,
    candidate: Candidate,
    evidence: Evidence | None,
    label: Label,
    score: int,
    brand: str | None,
    reasons: list[Reason],
    status: str = "new",
    decisions: list[Decision] | None = None,
) -> Case:
    return Case(
        id=case_id,
        domain=hostname(candidate.url),
        status=status,
        candidate=candidate,
        evidence=evidence,
        verdict=Verdict(
            url=candidate.url,
            verdict=label,
            score=score,
            brand_target=brand,
            reasons=reasons,
            model_version=MODEL,
            scored_at=candidate.discovered_at + timedelta(minutes=2),
        ),
        decisions=decisions or [],
    )


def build_cases() -> list[Case]:
    cases: list[Case] = []

    url = "https://tamm-fines-pay.test/pay?ref=AD-55120"
    seen = _at(10, 42)
    cases.append(
        _case(
            "c-0001",
            Candidate(url=url, source=Source.LOOKALIKE, query="tamm", discovered_at=seen),
            _evidence(
                url,
                seen,
                title="TAMM | Pay Traffic Fines",
                text="Your traffic fine of AED 1,250 is overdue. Pay now to avoid a 50% "
                "penalty and vehicle impound. Enter your card details to settle the fine.",
                forms=[
                    FormInfo(
                        action="https://tamm-fines-pay.test/submit",
                        input_types=["text", "tel", "password"],
                        field_hints=["card number", "expiry", "cvv", "otp"],
                    )
                ],
                registrar=REGISTRAR_A,
                created=_utc(21),
                host=HOST_A,
            ),
            Label.FRAUD,
            94,
            "tamm",
            [
                _r(
                    "lookalike_domain",
                    30,
                    "Domain imitates TAMM: 'tamm' plus 'fines-pay' on a non-official domain",
                    "النطاق يقلّد «تم»: كلمة tamm مع fines-pay على نطاق غير رسمي",
                    "url",
                ),
                _r(
                    "new_domain",
                    12,
                    "Domain registered 3 days before discovery",
                    "تم تسجيل النطاق قبل 3 أيام من اكتشافه",
                    "rdap.created",
                ),
                _r(
                    "brand_on_wrong_domain",
                    20,
                    "Page shows the TAMM name and logo, but the official domain is tamm.abudhabi",
                    "الصفحة تعرض اسم وشعار «تم» بينما النطاق الرسمي هو tamm.abudhabi",
                    "screenshot",
                ),
                CARD_OTP,
                _r(
                    "scam_keywords",
                    12,
                    "Urgent payment wording: 'Pay now to avoid a 50% penalty'",
                    "عبارات دفع عاجلة: «ادفع الآن لتجنب غرامة 50٪»",
                    "text_excerpt",
                ),
            ],
            status="confirmed",
            decisions=[
                Decision(
                    action="confirm",
                    reason="Clear TAMM impersonation asking for card and OTP",
                    by="analyst",
                    at=_at(10, 55),
                )
            ],
        )
    )

    url = "https://uaepass-login.test/auth"
    seen = _at(10, 15)
    cases.append(
        _case(
            "c-0002",
            Candidate(url=url, source=Source.CT, query="uaepass", discovered_at=seen),
            _evidence(
                url,
                seen,
                title="UAE PASS - Login",
                text="Login with UAE PASS. Enter your Emirates ID, password and the "
                "verification code sent to your phone.",
                forms=[
                    FormInfo(
                        action="https://uaepass-login.test/verify",
                        input_types=["text", "password", "tel"],
                        field_hints=["emirates id", "password", "otp"],
                    )
                ],
                registrar=REGISTRAR_A,
                created=_utc(22),
                host=HOST_A,
            ),
            Label.FRAUD,
            89,
            "uaepass",
            [
                _r(
                    "lookalike_domain",
                    30,
                    "Domain contains 'uaepass' but is not uaepass.ae",
                    "النطاق يحتوي على uaepass لكنه ليس uaepass.ae",
                    "url",
                ),
                _r(
                    "new_certificate",
                    12,
                    "TLS certificate first seen 2 days before discovery",
                    "ظهرت شهادة TLS لأول مرة قبل يومين من الاكتشاف",
                    "ct",
                ),
                _r(
                    "password_otp_form",
                    25,
                    "Login form asks for a password and a one-time code",
                    "نموذج الدخول يطلب كلمة المرور ورمز التحقق لمرة واحدة",
                    "forms",
                ),
                _r(
                    "brand_on_wrong_domain",
                    22,
                    "Page copies the UAE PASS login screen on a non-official domain",
                    "الصفحة تنسخ شاشة دخول الهوية الرقمية على نطاق غير رسمي",
                    "screenshot",
                ),
            ],
        )
    )

    url = "https://emiratesnbd-support.test/"
    seen = _at(9, 58)
    cases.append(
        _case(
            "c-0003",
            Candidate(
                url=url,
                source=Source.MAPS,
                query="emirates nbd customer care",
                discovered_at=seen,
                extra=CandidateExtra(
                    listing_name="Emirates NBD Customer Care 24/7",
                    phone="04 555 0199",
                    address="Al Barsha, Dubai",
                ),
            ),
            _evidence(
                url,
                seen,
                title="Emirates NBD Support - Card Unblocking 24/7",
                text="Card blocked? Call our 24/7 support line or enter your card details "
                "below and an agent will unblock it within minutes.",
                forms=[
                    FormInfo(
                        action="https://emiratesnbd-support.test/unblock",
                        input_types=["text", "tel"],
                        field_hints=["card number", "mobile number"],
                    )
                ],
                registrar=REGISTRAR_B,
                created=_utc(15),
                host=HOST_B,
            ),
            Label.FRAUD,
            81,
            "emiratesnbd",
            [
                _r(
                    "helpline_mismatch",
                    35,
                    "Maps listing phone 04 555 0199 is not Emirates NBD's official "
                    "helpline 600 54 0000",
                    "رقم الهاتف في خرائط Google ‏04 555 0199 ليس رقم الخدمة الرسمي "
                    "لبنك الإمارات دبي الوطني 600 54 0000",
                    "candidate.extra.phone",
                ),
                _r(
                    "lookalike_domain",
                    25,
                    "Domain uses the Emirates NBD name but is not emiratesnbd.com",
                    "النطاق يستخدم اسم بنك الإمارات دبي الوطني لكنه ليس emiratesnbd.com",
                    "url",
                ),
                _r(
                    "new_domain",
                    12,
                    "Domain registered 9 days before discovery",
                    "تم تسجيل النطاق قبل 9 أيام من اكتشافه",
                    "rdap.created",
                ),
                _r(
                    "scam_keywords",
                    9,
                    "Promises '24/7 card unblocking' and asks for card details",
                    "يَعِد «بفك حظر البطاقة على مدار الساعة» ويطلب بيانات البطاقة",
                    "text_excerpt",
                ),
            ],
        )
    )

    url = "https://rta-fine-check.test/dubai"
    seen = _at(9, 31)
    cases.append(
        _case(
            "c-0004",
            Candidate(
                url=url,
                source=Source.SEARCH_AD,
                query="pay traffic fine dubai",
                discovered_at=seen,
            ),
            _evidence(
                url,
                seen,
                title="Check & Pay Dubai Traffic Fines Online",
                text="Check your fines instantly. Enter your plate number and Emirates ID.",
                forms=[
                    FormInfo(
                        action="https://rta-fine-check.test/lookup",
                        input_types=["text", "text"],
                        field_hints=["plate number", "emirates id"],
                    )
                ],
                registrar=REGISTRAR_B,
                created=_utc(19),
                host=("198.51.100.77", 64501, "Sample Cloud LLC", "abuse@cloud.test"),
            ),
            Label.SUSPICIOUS,
            58,
            "rta",
            [
                _r(
                    "lookalike_domain",
                    25,
                    "Domain combines 'rta' and 'fine' but is not rta.ae",
                    "النطاق يجمع بين rta و fine لكنه ليس rta.ae",
                    "url",
                ),
                _r(
                    "new_domain",
                    12,
                    "Domain registered 5 days before discovery",
                    "تم تسجيل النطاق قبل 5 أيام من اكتشافه",
                    "rdap.created",
                ),
                _r(
                    "scam_keywords",
                    15,
                    "Asks for plate number and Emirates ID to 'check fines'",
                    "يطلب رقم اللوحة والهوية الإماراتية «للاستعلام عن المخالفات»",
                    "text_excerpt",
                ),
                _r(
                    "paid_ad",
                    6,
                    "Promoted as a paid ad for 'pay traffic fine dubai'",
                    "يظهر كإعلان مدفوع لعبارة البحث «pay traffic fine dubai»",
                    "candidate.source",
                ),
            ],
        )
    )

    url = "https://s.test/x7Kp2"
    final = "https://tamm-violations.test/pay"
    seen = _at(9, 12)
    cases.append(
        _case(
            "c-0005",
            Candidate(url=url, source=Source.CITIZEN, discovered_at=seen),
            _evidence(
                url,
                seen,
                title="TAMM - Traffic Violations Payment",
                text="You have 2 unpaid traffic violations. Pay within 24 hours to avoid "
                "black points. Enter card details and the code sent by SMS.",
                forms=[
                    FormInfo(
                        action="https://tamm-violations.test/charge",
                        input_types=["text", "tel", "password"],
                        field_hints=["card number", "cvv", "otp"],
                    )
                ],
                registrar=REGISTRAR_A,
                created=_utc(21, 16),
                host=HOST_A,
                redirects=[
                    RedirectHop(url=url, status=301),
                    RedirectHop(url=final, status=200),
                ],
                final_url=final,
            ),
            Label.FRAUD,
            90,
            "tamm",
            [
                _r(
                    "shortener_redirect",
                    10,
                    "Short link redirects to tamm-violations.test",
                    "الرابط المختصر يحوّل إلى tamm-violations.test",
                    "redirect_chain",
                ),
                _r(
                    "lookalike_domain",
                    30,
                    "Final domain imitates TAMM: 'tamm' plus 'violations'",
                    "النطاق النهائي يقلّد «تم»: كلمة tamm مع violations",
                    "url",
                ),
                _r(
                    "brand_on_wrong_domain",
                    20,
                    "Page shows the TAMM name and logo on a non-official domain",
                    "الصفحة تعرض اسم وشعار «تم» على نطاق غير رسمي",
                    "screenshot",
                ),
                CARD_OTP,
                _r(
                    "new_domain",
                    10,
                    "Domain registered 3 days before discovery",
                    "تم تسجيل النطاق قبل 3 أيام من اكتشافه",
                    "rdap.created",
                ),
            ],
        )
    )

    for case_id, url, query, minute in (
        ("c-0006", "https://www.tamm.abudhabi/", "tamm traffic fines", 50),
        ("c-0007", "https://www.rta.ae/", "pay traffic fine dubai", 47),
    ):
        seen = _at(8, minute)
        cases.append(
            _case(
                case_id,
                Candidate(url=url, source=Source.SEARCH, query=query, discovered_at=seen),
                None,
                Label.LEGIT,
                0,
                None,
                [official_domain_reason(official_brand_for_domain(hostname(url)), hostname(url))],
            )
        )

    url = "https://uae-pass.test/"
    seen = _at(8, 20)
    cases.append(
        _case(
            "c-0008",
            Candidate(url=url, source=Source.LOOKALIKE, query="uaepass", discovered_at=seen),
            _evidence(
                url,
                seen,
                title="Domain parked",
                text="This domain may be for sale.",
                registrar=REGISTRAR_A,
                created=_utc(23),
                host=("203.0.113.200", 64502, "Parking Co.", "abuse@parking.test"),
            ),
            Label.SUSPICIOUS,
            42,
            "uaepass",
            [
                _r(
                    "lookalike_domain",
                    30,
                    "Domain is one hyphen away from uaepass.ae",
                    "النطاق يختلف عن uaepass.ae بشرطة واحدة فقط",
                    "url",
                ),
                _r(
                    "new_domain",
                    12,
                    "Domain registered 1 day before discovery",
                    "تم تسجيل النطاق قبل يوم واحد من اكتشافه",
                    "rdap.created",
                ),
            ],
            status="dismissed",
            decisions=[
                Decision(
                    action="dismiss",
                    reason="Parked page with no phishing content yet; re-check tomorrow",
                    by="analyst",
                    at=_at(8, 40),
                )
            ],
        )
    )
    return cases


def placeholder_verdict(url: str) -> Verdict:
    """Stand-in until the real engine is wired in. Clearly labelled as mock."""
    host = hostname(url)
    brand = official_brand_for_domain(host)
    now = datetime.now(UAE)
    if brand:
        return Verdict(
            url=url,
            verdict=Label.LEGIT,
            score=0,
            brand_target=None,
            reasons=[official_domain_reason(brand, host)],
            model_version=MODEL,
            scored_at=now,
        )
    return Verdict(
        url=url,
        verdict=Label.SUSPICIOUS,
        score=50,
        brand_target=None,
        reasons=[
            _r(
                "mock_placeholder",
                0,
                "Mock result: the real engine is not connected yet",
                "نتيجة تجريبية: المحرك الحقيقي غير متصل بعد",
            )
        ],
        model_version=MODEL,
        scored_at=now,
    )


MOCK_METRICS = Metrics(
    mode="mock",
    dataset="mock — sample numbers for UI layout only, not a measurement",
    model_version=MODEL,
    n_fraud=200,
    n_legit=200,
    tp=186,
    fp=6,
    tn=194,
    fn=14,
    precision=0.969,
    recall=0.93,
    fpr=0.03,
    f1=0.949,
    evaluated_at=_at(10, 0),
)
