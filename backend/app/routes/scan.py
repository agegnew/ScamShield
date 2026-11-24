import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ..api_models import BatchItem, BatchRequest, BatchResponse, ScanRequest, ScanResponse
from ..mock.data import MODEL, placeholder_verdict
from ..mock.store import MockStore, get_store
from ..urls import InvalidURL, normalize_url

router = APIRouter(prefix="/api", tags=["scan"])


@router.post("/scan", response_model=ScanResponse)
def scan(body: ScanRequest, store: MockStore = Depends(get_store)) -> ScanResponse:
    try:
        url = normalize_url(body.url)
    except InvalidURL as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    case = store.add_scan(url)
    return ScanResponse(case_id=case.id, status="done", verdict=case.verdict)


@router.post("/batch", response_model=BatchResponse)
def batch(
    body: BatchRequest,
    format: str = Query("json", pattern="^(json|csv)$"),
    store: MockStore = Depends(get_store),
):
    """Score many URLs at once. `?format=csv` returns a CSV file."""
    items: list[BatchItem] = []
    for raw in body.urls:
        try:
            url = normalize_url(raw)
        except InvalidURL as exc:
            items.append(BatchItem(url=raw, error=str(exc)))
            continue
        known = store.find_by_url(url)
        verdict = known.verdict if known else placeholder_verdict(url)
        items.append(
            BatchItem(
                url=raw,
                verdict=verdict.verdict,
                score=verdict.score,
                brand_target=verdict.brand_target,
                reason_codes=[r.code for r in verdict.reasons],
            )
        )
    result = BatchResponse(model_version=MODEL, items=items)
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
