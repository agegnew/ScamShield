"""Takedown request for a case, addressed to the registrar and the host."""

from urllib.parse import quote, urlencode

from .api_models import Case, Takedown
from .brands import brand_by_id


def build_takedown(case: Case) -> Takedown:
    ev = case.evidence
    # On a shared platform the domain's registrar is the platform's; report to the host only.
    rdap = ev.rdap if ev and not ev.shared_hosting else None
    brand = brand_by_id(case.verdict.brand_target)
    brand_en = brand.name_en if brand else "a UAE organisation"
    brand_ar = brand.name_ar if brand else "جهة إماراتية"

    url = case.candidate.url
    final_url = (ev.final_url if ev else None) or url
    ip = ev.ip if ev else None
    first_seen = case.candidate.discovered_at.isoformat()
    score = f"{case.verdict.score}/100 ({case.verdict.verdict.value})"
    points = [r for r in case.verdict.reasons if r.weight > 0]
    evidence_en = "\n".join(f"- {r.text_en}" for r in points) or "- See attached case file"
    evidence_ar = "\n".join(f"- {r.text_ar}" for r in points) or "- انظر ملف القضية المرفق"

    body_en = (
        "Hello,\n\n"
        f"We are reporting a phishing website impersonating {brand_en}, "
        "registered or hosted with you.\n\n"
        f"URL: {url}\n"
        f"Final URL: {final_url}\n"
        f"First seen: {first_seen}\n"
        f"IP address: {ip or 'unknown'}\n"
        f"Risk score: {score}\n\n"
        f"Evidence:\n{evidence_en}\n\n"
        f"Screenshots, WHOIS and hosting records are kept under case {case.id}.\n"
        "Please suspend this domain or site.\n\n"
        "ScamShield"
    )
    body_ar = (
        "مرحبًا،\n\n"
        f"نبلغكم عن موقع تصيّد احتيالي ينتحل صفة {brand_ar}، مسجّل أو مستضاف لديكم.\n\n"
        f"الرابط: {url}\n"
        f"الرابط النهائي: {final_url}\n"
        f"أول رصد: {first_seen}\n"
        f"عنوان IP: {ip or 'غير معروف'}\n"
        f"درجة الخطورة: {score}\n\n"
        f"الأدلة:\n{evidence_ar}\n\n"
        f"لقطات الشاشة وبيانات WHOIS والاستضافة محفوظة في القضية {case.id}.\n"
        "نرجو إيقاف هذا النطاق أو الموقع.\n\n"
        "ScamShield"
    )
    registrar_abuse = rdap.abuse_email if rdap else None
    hosting_abuse = ev.hosting_abuse_email if ev else None
    recipients = _recipients(registrar_abuse, hosting_abuse)
    subject = f"Phishing site impersonating {brand_en}: {case.domain}"
    return Takedown(
        case_id=case.id,
        domain=case.domain,
        registrar=rdap.registrar if rdap else None,
        registrar_abuse_email=registrar_abuse,
        hosting_org=ev.hosting_org if ev else None,
        hosting_abuse_email=hosting_abuse,
        ip=ip,
        subject=subject,
        body_en=body_en,
        body_ar=body_ar,
        recipients=recipients,
        mailto=_mailto(recipients, subject, body_en),
    )


def _recipients(*emails: str | None) -> list[str]:
    """Non-empty abuse addresses, first occurrence kept (case-insensitive)."""
    seen: set[str] = set()
    out: list[str] = []
    for email in emails:
        email = (email or "").strip()
        if email and "@" in email and email.lower() not in seen:
            seen.add(email.lower())
            out.append(email)
    return out


def _mailto(recipients: list[str], subject: str, body: str) -> str | None:
    """RFC 6068 mailto: link; line breaks become CRLF as the RFC asks."""
    if not recipients:
        return None
    to = ",".join(quote(r, safe="@") for r in recipients)
    query = urlencode({"subject": subject, "body": body.replace("\n", "\r\n")}, quote_via=quote)
    return f"mailto:{to}?{query}"
