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
from ..auth import analyst_access, require_user
from ..contracts import Label, Source
from ..deps import get_repo
from ..graph import build_graph
from ..repo import CaseRepo
from ..takedown import build_takedown

# Analyst reads are open unless SCAMSHIELD_REQUIRE_LOGIN=1 (see auth.py).
router = APIRouter(prefix="/api", tags=["cases"], dependencies=[Depends(analyst_access)])


def _case_or_404(repo: CaseRepo, case_id: str) -> Case:
    case = repo.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"No case {case_id}")
    return case


@router.get("/radar/feed", response_model=RadarFeed)
def radar_feed(
    limit: int = Query(50, ge=1, le=500),
    repo: CaseRepo = Depends(get_repo),
) -> RadarFeed:
    """Newest auto-discovered URLs first (manual, citizen and batch excluded)."""
    return RadarFeed(
        items=repo.summaries(repo.radar(limit)), counts_by_source=repo.counts_by_source()
    )


@router.get("/cases", response_model=CaseList)
def list_cases(
    verdict: Label | None = None,
    source: Source | None = None,
    brand: str | None = None,
    status: CaseStatus | None = None,
    q: str | None = Query(None, description="Substring of the URL"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    repo: CaseRepo = Depends(get_repo),
) -> CaseList:
    found, total = repo.search(
        verdict=verdict.value if verdict else None,
        source=source.value if source else None,
        brand=brand,
        status=status,
        q=q,
        limit=limit,
        offset=offset,
    )
    return CaseList(items=repo.summaries(found), total=total)


@router.get("/cases/{case_id}", response_model=Case)
def get_case(case_id: str, repo: CaseRepo = Depends(get_repo)) -> Case:
    return _case_or_404(repo, case_id)


@router.post("/cases/{case_id}/decision", response_model=Case)
def decide(
    case_id: str,
    body: DecisionRequest,
    user: UserInfo = Depends(require_user),
    repo: CaseRepo = Depends(get_repo),
) -> Case:
    """Confirm or dismiss. Needs a logged-in analyst or admin; the log keeps who, when, why."""
    _case_or_404(repo, case_id)
    return repo.decide(case_id, body.action, body.reason, user.username)


@router.get("/cases/{case_id}/takedown", response_model=Takedown)
def takedown(case_id: str, repo: CaseRepo = Depends(get_repo)) -> Takedown:
    return build_takedown(_case_or_404(repo, case_id))


@router.get("/cases/{case_id}/report.pdf")
def report_pdf(case_id: str, repo: CaseRepo = Depends(get_repo)) -> None:
    _case_or_404(repo, case_id)
    raise HTTPException(status_code=501, detail="PDF export is not built yet (due 19:00)")


@router.get("/graph", response_model=Graph)
def graph(repo: CaseRepo = Depends(get_repo)) -> Graph:
    return build_graph(repo.all(limit=2000))
