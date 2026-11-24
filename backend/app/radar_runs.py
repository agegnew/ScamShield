"""Radar runs: the "Run radar now" button and the daily 03:00 run (docs/radar-ui.md).

start() records a run and queues one radar job; the worker's execute() runs each chosen source
in turn, writing progress as it goes, stores the new URLs as cases (scored from the URL at once)
and queues a page check for the riskiest of them. The run is done when every source has finished
and every queued page check is done; status() works that out when asked.
"""

import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import jobs
from .api_models import (
    RadarRun,
    RadarRunPages,
    RadarRunSource,
    RadarSchedule,
    RadarSourceInfo,
    RadarStatus,
)
from .brands import load_registry
from .db import CaseRow, JobRow, RadarRunRow, SessionLocal, utcnow

log = logging.getLogger("scamshield.radar_runs")

SOURCE_ORDER = ("lookalikes", "ct", "nrd", "search", "maps")
# The UAE has no daylight saving, so a fixed +4 offset is Asia/Dubai all year.
UAE = timezone(timedelta(hours=4), "Asia/Dubai")
DAILY = os.getenv("SCAMSHIELD_RADAR_DAILY", "1") == "1"
DAILY_AT = os.getenv("SCAMSHIELD_RADAR_DAILY_AT", "03:00")
# Page checks per run, riskiest URL first; the rest keep their URL-only verdict.
MAX_FETCH = int(os.getenv("SCAMSHIELD_RADAR_MAX_FETCH", "300"))
# A run still "running" after this long lost its worker; a new run may start.
STALE_AFTER = timedelta(hours=6)
PROGRESS_EVERY = 1.0  # seconds between progress writes

TERMINAL = {"done", "skipped", "failed"}


class AlreadyRunning(Exception):
    def __init__(self, run: RadarRunRow) -> None:
        super().__init__(run.id)
        self.run = run


def _sources():
    from .workers.radar import SOURCES  # worker packages are imported only when a run executes

    return SOURCES


def _needs_key(name: str) -> str | None:
    return "SERPAPI_KEY" if name in ("search", "maps") else None


def _has_key(name: str) -> bool:
    key = _needs_key(name)
    return not key or bool(os.getenv(key))


# ---- starting ------------------------------------------------------------------


def current(session: Session) -> RadarRunRow | None:
    """The run in progress, unless it went stale."""
    row = session.scalars(
        select(RadarRunRow).where(RadarRunRow.status == "running").order_by(RadarRunRow.started_at.desc())
    ).first()
    if row is None:
        return None
    if _utc(row.started_at) < utcnow() - STALE_AFTER:
        row.status, row.error, row.finished_at = "failed", "stale: the worker stopped", utcnow()
        session.commit()
        return None
    finish_if_done(session, row)  # every page check may have finished since anyone last looked
    return row if row.status == "running" else None


def start(
    session: Session,
    trigger: str = "manual",
    started_by: str | None = None,
    sources: list[str] | None = None,
    brands: list[str] | None = None,
) -> RadarRunRow:
    """Record a run and queue it for the radar worker. Raises AlreadyRunning or ValueError."""
    unknown = [s for s in sources or [] if s not in SOURCE_ORDER]
    if unknown:
        raise ValueError(f"unknown source: {', '.join(unknown)}")
    known = {b.id for b in load_registry().brands}
    unknown = [b for b in brands or [] if b not in known]
    if unknown:
        raise ValueError(f"unknown brand: {', '.join(unknown)}")
    running = current(session)
    if running:
        raise AlreadyRunning(running)
    chosen = [s for s in SOURCE_ORDER if not sources or s in sources]
    now = utcnow()
    row = RadarRunRow(
        id=f"run-{now:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}",
        trigger=trigger,
        started_by=started_by,
        status="running",
        started_at=now,
        brands=sorted(set(brands)) if brands else None,
        sources=[
            {"name": s, "status": "waiting"} if _has_key(s) else {"name": s, "status": "skipped", "note": "needs_key"}
            for s in chosen
        ],
        case_ids=[],
        fetch_ids=[],
    )
    session.add(row)
    session.commit()
    jobs.enqueue(session, jobs.RADAR, {"run": row.id}, dedupe_key=f"radar-run:{row.id}")
    log.info("radar run %s started (%s by %s): %s", row.id, trigger, started_by, chosen)
    return row


# ---- running (worker) -------------------------------------------------------------


def _update(run_id: str, name: str, **fields) -> None:
    """Change one source's entry in its own session (progress arrives from inside discover())."""
    with SessionLocal() as s:
        row = s.get(RadarRunRow, run_id)
        if row is None:
            return
        row.sources = [{**e, **fields} if e["name"] == name else e for e in row.sources]
        s.commit()


def _progress_writer(run_id: str, name: str):
    last = [0.0]

    def write(checked: int, total: int | None) -> None:
        now = time.monotonic()
        if now - last[0] >= PROGRESS_EVERY or (total is not None and checked >= total):
            last[0] = now
            _update(run_id, name, checked=checked, total=total)

    return write


def execute(session: Session, run_id: str) -> None:
    from .repo import CaseRepo
    from .workers.radar import serp

    row = session.get(RadarRunRow, run_id)
    if row is None or row.status != "running":
        return
    wanted = set(row.brands or [])
    brands = [b for b in load_registry().brands if not wanted or b.id in wanted]
    names = [e["name"] for e in row.sources if e["status"] == "waiting"]
    repo = CaseRepo(session)
    # SerpApi: one budget shared by the Search and Maps radars for the whole run.
    searches = serp.run_budget(row.trigger) if any(n in ("search", "maps") for n in names) else 0
    with serp.budget(searches) as spend:
        for name in names:
            source = _sources()[name]
            _update(run_id, name, status="running", checked=0)
            source.progress = _progress_writer(run_id, name)
            try:
                found = source.discover(brands)
            except Exception as exc:  # one broken source must not stop the run
                log.exception("radar run %s: %s failed", run_id, name)
                _update(run_id, name, status="failed", note=type(exc).__name__)
                continue
            finally:
                source.progress = None
            new = []
            for candidate in found:
                case, created = repo.upsert_candidate(candidate)
                if created:
                    new.append(case)
            _queue_page_checks(session, run_id, new)
            fields = {"status": "done", "found": len(found), "new": len(new)}
            if name in ("search", "maps"):
                fields["note"] = f"{spend.spent} live searches so far"
            _update(run_id, name, **fields)
            log.info("radar run %s: %s found %d, %d new", run_id, name, len(found), len(new))
    with SessionLocal() as s:
        finish_if_done(s, s.get(RadarRunRow, run_id))


def _queue_page_checks(session: Session, run_id: str, new_cases: list) -> None:
    """Riskiest first, up to MAX_FETCH per run; the rest keep their URL-only verdict."""
    row = session.get(RadarRunRow, run_id)
    session.refresh(row)
    room = max(0, MAX_FETCH - len(row.fetch_ids or []))
    ranked = sorted(new_cases, key=lambda c: -c.verdict.score)
    to_fetch = ranked[:room]
    for case in to_fetch:
        jobs.enqueue(session, jobs.FETCH, {"url": case.candidate.url}, dedupe_key=f"fetch:{case.id}")
    row.case_ids = (row.case_ids or []) + [c.id for c in new_cases]
    row.fetch_ids = (row.fetch_ids or []) + [c.id for c in to_fetch]
    session.commit()


# ---- reading -----------------------------------------------------------------------


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _pages(session: Session, row: RadarRunRow) -> tuple[RadarRunPages, set[str]]:
    """Page-check progress, and the ids whose check is still pending."""
    ids = row.fetch_ids or []
    if not ids:
        return RadarRunPages(checked=0, total=0), set()
    keys = [f"fetch:{i}" for i in ids]
    finished = set()
    for key, status in session.execute(
        select(JobRow.dedupe_key, JobRow.status).where(JobRow.dedupe_key.in_(keys))
    ):
        if status in ("done", "failed"):
            finished.add(key.split(":", 1)[1])
    pending = set(ids) - finished
    return RadarRunPages(checked=len(ids) - len(pending), total=len(ids)), pending


def finish_if_done(session: Session, row: RadarRunRow | None) -> None:
    if row is None or row.status != "running":
        return
    if any(e["status"] not in TERMINAL for e in row.sources):
        return
    pages, pending = _pages(session, row)
    if pending:
        return
    tried = [e for e in row.sources if e["status"] != "skipped"]
    row.status = "failed" if tried and all(e["status"] == "failed" for e in tried) else "done"
    if row.status == "failed":
        row.error = "every source failed"
    row.finished_at = utcnow()
    session.commit()
    log.info("radar run %s %s", row.id, row.status)


def to_model(session: Session, row: RadarRunRow) -> RadarRun:
    pages, pending = _pages(session, row)
    final_ids = [i for i in row.case_ids or [] if i not in pending]
    verdicts: dict[str, int] = {}
    if final_ids:
        for (verdict,) in session.execute(select(CaseRow.verdict).where(CaseRow.id.in_(final_ids))):
            verdicts[verdict] = verdicts.get(verdict, 0) + 1
    return RadarRun(
        id=row.id,
        trigger=row.trigger,
        started_by=row.started_by,
        status=row.status,
        started_at=_utc(row.started_at),
        finished_at=_utc(row.finished_at),
        brands=row.brands,
        sources=[RadarRunSource(**e) for e in row.sources],
        pages=pages,
        verdicts=verdicts,
        error=row.error,
    )


def runs(session: Session, limit: int = 10) -> list[RadarRun]:
    rows = session.scalars(select(RadarRunRow).order_by(RadarRunRow.started_at.desc()).limit(limit)).all()
    for row in rows:
        finish_if_done(session, row)
    return [to_model(session, r) for r in rows]


def next_daily(now: datetime | None = None) -> datetime:
    """The next DAILY_AT in UAE time, strictly after `now`."""
    now = (now or utcnow()).astimezone(UAE)
    hour, minute = (int(x) for x in DAILY_AT.split(":"))
    due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return due if due > now else due + timedelta(days=1)


_searches_cache: tuple[float, int | None] = (0.0, None)


def _searches_left() -> int | None:
    """SerpApi searches left, asked at most every 2 minutes (the status is polled every 2 s)."""
    global _searches_cache
    if not os.getenv("SERPAPI_KEY"):
        return None
    at, value = _searches_cache
    if time.monotonic() - at > 120 or value is None:
        from .workers.radar.serp import searches_left

        value = searches_left()
        _searches_cache = (time.monotonic(), value)
    return value


def status(session: Session) -> RadarStatus:
    row = current(session) or session.scalars(
        select(RadarRunRow).order_by(RadarRunRow.started_at.desc())
    ).first()
    recent = session.scalars(select(RadarRunRow).order_by(RadarRunRow.started_at.desc()).limit(20)).all()
    sources = []
    for name in SOURCE_ORDER:
        last = next(
            ((r, e) for r in recent for e in r.sources if e["name"] == name and e["status"] == "done"), None
        )
        sources.append(
            RadarSourceInfo(
                name=name,
                enabled=_has_key(name),
                needs_key=_needs_key(name),
                last_run_at=_utc(last[0].started_at) if last else None,
                last_new=(last[1].get("new") or 0) if last else 0,
            )
        )
    return RadarStatus(
        running=bool(row and row.status == "running"),
        run=to_model(session, row) if row else None,
        schedule=RadarSchedule(
            enabled=DAILY, time=DAILY_AT, timezone="Asia/Dubai", next_run_at=next_daily() if DAILY else None
        ),
        sources=sources,
        searches_left=_searches_left(),
    )


# ---- the daily run (called by the worker loop) ---------------------------------------


def maybe_start_daily(state: dict) -> None:
    """Start the daily run once DAILY_AT passes. A worker started after 03:00 waits for tomorrow."""
    if not DAILY:
        return
    now = utcnow()
    due = state.setdefault("daily_due", next_daily(now))
    if now < due:
        return
    state["daily_due"] = next_daily(now)
    with SessionLocal() as session:
        try:
            start(session, trigger="schedule")
        except AlreadyRunning:
            log.info("daily radar run skipped: a run is still going")
