"""Radar runs: status for the Radar page, the "Run radar now" button and run history (docs/radar-ui.md).

The feed itself is GET /api/radar/feed in cases.py.
"""

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .. import radar_runs
from ..api_models import RadarRun, RadarRunRequest, RadarRunResponse, RadarStatus, UserInfo
from ..auth import analyst_access, require_user
from ..deps import get_session

router = APIRouter(prefix="/api/radar", tags=["radar"])


@router.get("/status", response_model=RadarStatus, dependencies=[Depends(analyst_access)])
def radar_status(session: Session = Depends(get_session)) -> RadarStatus:
    """The current run (or the last one), the daily schedule and each source's state.
    Poll every 2 s while `running`, every 30 s otherwise."""
    return radar_runs.status(session)


@router.get("/runs", response_model=list[RadarRun], dependencies=[Depends(analyst_access)])
def radar_runs_list(
    limit: int = Query(10, ge=1, le=50), session: Session = Depends(get_session)
) -> list[RadarRun]:
    """The last runs, newest first."""
    return radar_runs.runs(session, limit)


@router.post(
    "/run",
    status_code=202,
    response_model=RadarRunResponse,
    responses={409: {"description": "A run is already going; the body is {detail, run}"}},
)
def radar_run(
    body: RadarRunRequest | None = Body(default=None),
    user: UserInfo = Depends(require_user),
    session: Session = Depends(get_session),
):
    """Start a radar run now (analyst or admin). Omit `sources` for all, `brands` for every brand."""
    body = body or RadarRunRequest()
    try:
        row = radar_runs.start(
            session, trigger="manual", started_by=user.username, sources=body.sources, brands=body.brands
        )
    except radar_runs.AlreadyRunning as exc:
        run = radar_runs.to_model(session, exc.run)
        return JSONResponse(
            status_code=409, content={"detail": "radar_already_running", "run": run.model_dump(mode="json")}
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RadarRunResponse(run=radar_runs.to_model(session, row))
