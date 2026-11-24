import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from .. import engine as detection
from .. import jobs
from ..api_models import BatchItem, BatchRequest, BatchResponse, ScanRequest, ScanResponse
from ..contracts import Candidate, Source
from ..deps import get_repo
from ..repo import CaseRepo
from ..urls import InvalidURL, normalize_url

router = APIRouter(prefix="/api", tags=["scan"])


@router.post("/scan", response_model=ScanResponse)
def scan(body: ScanRequest, repo: CaseRepo = Depends(get_repo)) -> ScanResponse:
    """Create (or reuse) a case for the URL. Returns a URL-only verdict now and
    queues a full fetch; poll GET /api/cases/{case_id} for the final result."""
    try:
        url = normalize_url(body.url)
    except InvalidURL as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    case, _ = repo.upsert_candidate(
        Candidate(url=url, source=Source.MANUAL, discovered_at=datetime.now(timezone.utc))
    )
    if case.evidence is not None:
        return ScanResponse(case_id=case.id, status="done", verdict=case.verdict)
    jobs.enqueue(repo.s, jobs.FETCH, {"url": case.candidate.url}, f"fetch:{case.id}")
    return ScanResponse(case_id=case.id, status="queued", verdict=case.verdict)


@router.post("/batch", response_model=BatchResponse)
def batch(
    body: BatchRequest,
    format: str = Query("json", pattern="^(json|csv)$"),
    repo: CaseRepo = Depends(get_repo),
):
    """Score many URLs at once without storing them. `?format=csv` returns a file."""
    items: list[BatchItem] = []
    for raw in body.urls:
        try:
            url = normalize_url(raw)
        except InvalidURL as exc:
            items.append(BatchItem(url=raw, error=str(exc)))
            continue
        known = repo.find_by_url(url)
        verdict = known.verdict if known else detection.score(url)
        items.append(
            BatchItem(
                url=raw,
                verdict=verdict.verdict,
                score=verdict.score,
                brand_target=verdict.brand_target,
                reason_codes=[r.code for r in verdict.reasons],
            )
        )
    result = BatchResponse(model_version=detection.core.model_version(), items=items)
    if format == "json":
        return result

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["url", "verdict", "score", "brand_target", "reason_codes", "error"])
    for item in items:
        writer.writerow(
            [
                item.url,
                item.verdict.value if item.verdict else "",
                "" if item.score is None else item.score,
                item.brand_target or "",
                ";".join(item.reason_codes),
                item.error or "",
            ]
        )
    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="scamshield-batch.csv"'},
    )
