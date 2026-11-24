from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from .. import engine as detection
from ..api_models import (
    Case,
    CaseList,
    CaseStatus,
    DecisionRequest,
    EvidenceExport,
    Graph,
    RadarFeed,
    Takedown,
    UserInfo,
)
from ..auth import analyst_access, require_user
from ..config import VERSION
from ..contracts import Label, Source
from ..deps import get_repo
from ..graph import build_graph, related_domains
from ..repo import CaseRepo
from ..report import build_report
from ..takedown import build_takedown

# Analyst reads are open unless SCAMSHIELD_REQUIRE_LOGIN=1 (see auth.py).
router = APIRouter(prefix="/api", tags=["cases"], dependencies=[Depends(analyst_access)])


def _case_or_404(repo: CaseRepo, case_id: str) -> Case:
    case = repo.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"No case {case_id}")
    return case


RadarFeedSource = Literal["lookalike", "ct", "nrd", "search", "maps"]
FeedCategory = Literal[
    "government", "police", "bank", "telecom", "transport", "utility", "delivery", "shopping", "travel", "none"
]


@router.get("/radar/feed", response_model=RadarFeed)
def radar_feed(
    limit: int = Query(50, ge=1, le=500),
    source: RadarFeedSource | None = Query(None, description="'search' also returns search_ad"),
    category: FeedCategory | None = Query(None, description="Brand sector; 'none' = no brand named"),
    verdict: Label | None = None,
    brand: str | None = None,
    q: str | None = Query(None, description="Substring of the domain"),
    repo: CaseRepo = Depends(get_repo),
) -> RadarFeed:
    """Newest auto-discovered URLs first (manual, citizen and batch excluded). The counts ignore
    the filters, so tab and chip numbers stay put while filtering."""
    found = repo.radar(
        limit, source=source, category=category, verdict=verdict.value if verdict else None, brand=brand, q=q
    )
    return RadarFeed(
        items=repo.summaries(found),
        counts_by_source=repo.counts_by_source(),
        counts_by_category=repo.counts_by_category(),
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


@router.get(
    "/cases/{case_id}/report.pdf",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}, "description": "A4 PDF, English + Arabic"}
    },
)
def report_pdf(case_id: str, repo: CaseRepo = Depends(get_repo)) -> Response:
    """Police-ready evidence report: verdict, reasons, screenshot, WHOIS, hosting, redirects,
    related domains, analyst decisions and takedown contacts. Downloads as a file."""
    case = _case_or_404(repo, case_id)
    pdf = build_report(case, related_domains(case.id, repo.all(limit=2000)))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="scamshield-{case.id}.pdf"'},
    )


@router.get("/cases/{case_id}/export.json", response_model=EvidenceExport)
def export_json(
    case_id: str, response: Response, repo: CaseRepo = Depends(get_repo)
) -> EvidenceExport:
    """Evidence bundle for hand-over: the full case, the takedown request and related domains.
    Downloads as a file."""
    case = _case_or_404(repo, case_id)
    response.headers["Content-Disposition"] = f'attachment; filename="scamshield-{case.id}.json"'
    return EvidenceExport(
        generated_at=datetime.now(timezone.utc),
        scamshield_version=VERSION,
        model_version=detection.core.model_version(),
        case=case,
        takedown=build_takedown(case),
        related=related_domains(case.id, repo.all(limit=2000)),
    )


@router.get("/graph", response_model=Graph)
def graph(repo: CaseRepo = Depends(get_repo)) -> Graph:
    return build_graph(repo.all(limit=2000))
