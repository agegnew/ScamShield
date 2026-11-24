"""User-facing text in English and Arabic, shared by the engine and the API."""

from .contracts import Brand, Reason

CITIZEN_TEXT: dict[str, dict[str, object]] = {
    "FRAUD": {
        "headline_en": "This looks like a scam",
        "headline_ar": "يبدو أن هذا احتيال",
        "advice_en": [
            "Do not enter card details or any code.",
            "If you already paid, call your bank now.",
            "Report it to Abu Dhabi Police through the Aman service: 8002626.",
        ],
        "advice_ar": [
            "لا تُدخل بيانات بطاقتك أو أي رمز.",
            "إذا دفعت بالفعل، اتصل ببنكك فورًا.",
            "أبلغ شرطة أبوظبي عبر خدمة أمان: 8002626.",
        ],
    },
    "SUSPICIOUS": {
        "headline_en": "Be careful with this",
        "headline_ar": "كن حذرًا",
        "advice_en": [
            "Open the official website by typing its address yourself.",
            "Never share codes sent to your phone.",
        ],
        "advice_ar": [
            "افتح الموقع الرسمي بكتابة عنوانه بنفسك.",
            "لا تشارك أبدًا الرموز المرسلة إلى هاتفك.",
        ],
    },
    "LEGIT": {
        "headline_en": "No warning signs found",
        "headline_ar": "لم نجد علامات تحذيرية",
        "advice_en": ["Even so, never share one-time codes with anyone."],
        "advice_ar": ["ومع ذلك، لا تشارك رموز التحقق لمرة واحدة مع أي شخص."],
    },
    "UNKNOWN": {
        "headline_en": "We don't know this number",
        "headline_ar": "هذا الرقم غير معروف لدينا",
        "advice_en": [
            "Banks and government offices never ask for codes by phone.",
            "Call back on the number published on the official website.",
        ],
        "advice_ar": [
            "البنوك والجهات الحكومية لا تطلب الرموز عبر الهاتف أبدًا.",
            "اتصل بالرقم المنشور على الموقع الرسمي.",
        ],
    },
}


def official_domain_reason(brand: Brand, host: str) -> Reason:
    return Reason(
        code="official_domain",
        weight=-50,
        text_en=f"Official {brand.name_en} domain ({host})",
        text_ar=f"نطاق رسمي لـ{brand.name_ar} ({host})",
        evidence_ref="url",
    )


def official_helpline_reason(brand: Brand) -> Reason:
    return Reason(
        code="official_helpline",
        weight=-50,
        text_en=f"This is an official {brand.name_en} helpline",
        text_ar=f"هذا رقم خدمة رسمي لـ{brand.name_ar}",
        evidence_ref="brands.helplines",
    )
