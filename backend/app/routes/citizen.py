import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from .. import engine as detection
from ..api_models import Blocklist, BlocklistEntry, CheckRequest, CheckResponse, CheckVerdict
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
) -> CheckResponse:
    return CheckResponse(
        kind=kind,
        input=raw,
        verdict=verdict,
        score=score,
        brand_target=brand,
        reasons=reasons,
        **CITIZEN_TEXT[verdict],
    )


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
            v = case.verdict
            return _response("phone", raw, v.verdict.value, v.score, v.brand_target, v.reasons)
        return _response("phone", raw, "UNKNOWN", None, None, [])

    try:
        url = normalize_url(raw)
    except InvalidURL as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    case = repo.find_by_url(url)
    v = case.verdict if case else detection.score(url)
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
