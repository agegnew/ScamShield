from fastapi import APIRouter, Depends, HTTPException, Query

from ..api_models import (
    Case,
    CaseList,
    CaseStatus,
    DecisionRequest,
    Graph,
    RadarFeed,
    Takedown,
    UserInfo,
)
from ..auth import current_user
from ..contracts import Label, Source
from ..graph import build_graph
from ..mock.store import MockStore, get_store
from ..takedown import build_takedown

router = APIRouter(prefix="/api", tags=["cases"])


def _case_or_404(store: MockStore, case_id: str) -> Case:
    case = store.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"No case {case_id}")
    return case


@router.get("/radar/feed", response_model=RadarFeed)
def radar_feed(
    limit: int = Query(50, ge=1, le=500),
    store: MockStore = Depends(get_store),
) -> RadarFeed:
    """Newest auto-discovered URLs first (manual and batch submissions excluded)."""
    radar_sources = {Source.LOOKALIKE, Source.CT, Source.SEARCH, Source.SEARCH_AD, Source.MAPS}
    items = [c for c in store.all() if c.candidate.source in radar_sources][:limit]
    return RadarFeed(items=store.summaries(items), counts_by_source=store.counts_by_source())


@router.get("/cases", response_model=CaseList)
def list_cases(
    verdict: Label | None = None,
    source: Source | None = None,
    brand: str | None = None,
    status: CaseStatus | None = None,
    q: str | None = Query(None, description="Substring of the URL"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    store: MockStore = Depends(get_store),
) -> CaseList:
    found = store.search(
        verdict=verdict.value if verdict else None,
        source=source.value if source else None,
        brand=brand,
        status=status,
        q=q,
    )
    return CaseList(items=store.summaries(found[offset : offset + limit]), total=len(found))


@router.get("/cases/{case_id}", response_model=Case)
def get_case(case_id: str, store: MockStore = Depends(get_store)) -> Case:
    return _case_or_404(store, case_id)


@router.post("/cases/{case_id}/decision", response_model=Case)
def decide(
    case_id: str,
    body: DecisionRequest,
    user: UserInfo = Depends(current_user),
    store: MockStore = Depends(get_store),
) -> Case:
    _case_or_404(store, case_id)
    return store.decide(case_id, body.action, body.reason, user.username)


@router.get("/cases/{case_id}/takedown", response_model=Takedown)
def takedown(case_id: str, store: MockStore = Depends(get_store)) -> Takedown:
    return build_takedown(_case_or_404(store, case_id))


@router.get("/cases/{case_id}/report.pdf")
def report_pdf(case_id: str, store: MockStore = Depends(get_store)) -> None:
    _case_or_404(store, case_id)
    raise HTTPException(status_code=501, detail="PDF export is not built yet (due 19:00)")


@router.get("/graph", response_model=Graph)
def graph(store: MockStore = Depends(get_store)) -> Graph:
    return build_graph(store.all())
