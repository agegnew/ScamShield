import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from .. import engine as detection
from .. import message_check as mc
from ..api_models import (
    Blocklist,
    BlocklistEntry,
    CheckRequest,
    CheckResponse,
    CheckVerdict,
    MessageCheckRequest,
    MessagePart,
)
from ..blocklist import MAX_DOMAINS, blockable
from ..brands import brand_for_helpline, normalize_uae_phone
from ..contracts import Reason
from ..deps import get_repo
from ..messages import CITIZEN_TEXT, official_helpline_reason
from ..repo import CaseRepo
from ..urls import InvalidURL, normalize_url

router = APIRouter(prefix="/api", tags=["citizen"])

PHONE_PATTERN = re.compile(r"^[+\d\s\-().]+$")


def _response(
    kind: str,
    raw: str,
    verdict: CheckVerdict,
    score: int | None,
    brand: str | None,
    reasons: list[Reason],
    **extra,
) -> CheckResponse:
    return CheckResponse(
        kind=kind,
        input=raw,
        verdict=verdict,
        score=score,
        brand_target=brand,
        reasons=reasons,
        **CITIZEN_TEXT[verdict],
        **extra,
    )


ANALYST_DISMISSED = Reason(
    code="analyst_dismissed",
    weight=0,
    text_en="A ScamShield analyst reviewed this site and found no scam",
    text_ar="راجع محلل في ScamShield هذا الموقع ولم يجد احتيالًا",
    evidence_ref="decisions",
)
ANALYST_CONFIRMED = Reason(
    code="analyst_confirmed",
    weight=0,
    text_en="A ScamShield analyst confirmed this is a scam",
    text_ar="أكّد محلل في ScamShield أن هذا احتيال",
    evidence_ref="decisions",
)


def _from_case(kind: str, raw: str, case) -> CheckResponse:
    """A stored case's verdict, with the analyst's decision on top of the engine's."""
    v = case.verdict
    if case.status == "dismissed":
        return _response(kind, raw, "LEGIT", 0, None, [ANALYST_DISMISSED])
    if case.status == "confirmed":
        return _response(kind, raw, "FRAUD", max(v.score, 70), v.brand_target, [ANALYST_CONFIRMED, *v.reasons])
    return _response(kind, raw, v.verdict.value, v.score, v.brand_target, v.reasons)


@router.post("/check", response_model=CheckResponse)
def check(body: CheckRequest, repo: CaseRepo = Depends(get_repo)) -> CheckResponse:
    """Public checker: paste a link or a phone number. No login needed."""
    raw = body.input.strip()
    digits = re.sub(r"\D", "", raw)

    if PHONE_PATTERN.match(raw) and 3 <= len(digits) <= 15:
        brand = brand_for_helpline(raw)
        if brand:
            return _response("phone", raw, "LEGIT", 0, brand.id, [official_helpline_reason(brand)])
        case = repo.find_by_phone(normalize_uae_phone(raw))
        if case:
            return _from_case("phone", raw, case)
        return _response("phone", raw, "UNKNOWN", None, None, [])

    try:
        url = normalize_url(raw)
    except InvalidURL as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    case = repo.find_by_url(url)
    if case:
        return _from_case("url", raw, case)
    v = detection.score(url)
    return _response("url", raw, v.verdict.value, v.score, v.brand_target, v.reasons)


@router.get("/blocklist", response_model=Blocklist)
def blocklist(repo: CaseRepo = Depends(get_repo)) -> Blocklist:
    """Scam domains for the browser extension to block (public; synced every 10 minutes)."""
    entries = [
        BlocklistEntry(domain=host, brand_target=brand, score=score, confirmed=confirmed, case_id=case_id)
        for host, brand, score, confirmed, case_id in repo.scam_domains()
        if blockable(host)
    ][:MAX_DOMAINS]
    return Blocklist(generated_at=datetime.now(timezone.utc), count=len(entries), domains=entries)


@router.post("/check/message", response_model=CheckResponse)
def check_message(body: MessageCheckRequest, repo: CaseRepo = Depends(get_repo)) -> CheckResponse:
    """Public: a whole SMS / WhatsApp message (text or screenshot). Each link and number is checked,
    the wording is matched against UAE scam types, and Claude reads the message (see message_check.py)."""
    text = (body.text or "").strip()
    image = None
    if body.image:
        try:
            image = mc.parse_image(body.image)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not text and not image:
        raise HTTPException(status_code=422, detail="Paste the message or add a screenshot")

    ai = mc.ask_ai(text or None, image)
    if image and ai is None and not text:
        raise HTTPException(status_code=503, detail="Reading screenshots is unavailable right now. Paste the message text instead.")
    full = "\n".join(filter(None, [text, ai.get("transcript") if ai else None]))

    links = list(dict.fromkeys(mc.find_links(full) + [l for l in (ai or {}).get("links", []) if l.strip()]))
    phones: dict[str, str] = {}
    for raw in mc.find_phones(full) + [p for p in (ai or {}).get("phone_numbers", []) if p.strip()]:
        phones.setdefault(mc.phone_key(raw), raw)

    parts: list[MessagePart] = []
    part_reasons: list[Reason] = []
    for kind, value in [("url", v) for v in links[:8]] + [("phone", v) for v in list(phones.values())[:5]]:
        try:
            r = check(CheckRequest(input=value[:2048]), repo)
        except Exception:  # an unreadable link or number: skip it, check the rest
            continue
        parts.append(MessagePart(kind=r.kind, input=value, verdict=r.verdict, score=r.score, brand_target=r.brand_target))
        what_en, what_ar = ("Link", "الرابط") if r.kind == "url" else ("Number", "الرقم")
        if r.verdict in ("FRAUD", "SUSPICIOUS"):
            top = max(r.reasons, key=lambda x: x.weight, default=None)
            part_reasons.append(Reason(
                code="message_part_flagged", weight=r.score or 0,
                text_en=f"{what_en} {value}: {r.verdict} {r.score}/100" + (f" ({top.text_en})" if top else ""),
                text_ar=f"{what_ar} {value}: {r.verdict} {r.score}/100" + (f" ({top.text_ar})" if top else ""),
                evidence_ref=r.kind))
        elif r.verdict == "LEGIT" and r.reasons:
            part_reasons.append(Reason(
                code="message_part_official", weight=-10,
                text_en=f"{what_en} {value}: {r.reasons[0].text_en}", text_ar=f"{what_ar} {value}: {r.reasons[0].text_ar}",
                evidence_ref=r.kind))

    wording = mc.wording_reasons(full)
    ai_r, ai_floor = mc.ai_reason(ai) if ai else (None, None)
    flagged = [p.score or 0 for p in parts if p.verdict in ("FRAUD", "SUSPICIOUS")]
    score = max([*flagged, min(60, 40 + 10 * (len(wording) - 1)) if wording else 0, ai_floor or 0])
    if ai_r is not None and ai_r.code == "ai_cleared" and not wording and max(flagged, default=0) < 70:
        score = min(score, 20)
    if not parts and not wording and ai is None:
        verdict: CheckVerdict = "UNKNOWN"
    else:
        verdict = "FRAUD" if score >= 70 else "SUSPICIOUS" if score >= 30 else "LEGIT"
    brand = next((p.brand_target for p in parts if p.brand_target and p.verdict != "LEGIT"), None)
    reasons = ([ai_r] if ai_r else []) + sorted(part_reasons, key=lambda r: -r.weight) + wording
    return _response(
        "message", text[:300] or "(screenshot)", verdict, score if verdict != "UNKNOWN" else None, brand, reasons,
        parts=parts, transcript=(ai or {}).get("transcript") if image else None,
    )
