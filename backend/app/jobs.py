"""Database-backed job queue: the API enqueues, the worker claims and runs."""

from datetime import timedelta

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from .config import JOB_MAX_ATTEMPTS
from .db import JobRow, utcnow

SCAN = "scan"  # payload: {"url": str} — a person asked (scan box, citizen): runs first
FETCH = "fetch"  # payload: {"url": str} — found by the radar
RADAR = "radar"  # payload: {"source": RadarSource.name}
FEEDS = "feeds"  # payload: {} — refresh phishing feeds
ALL_TYPES = (SCAN, FETCH, RADAR, FEEDS)

# Lower runs first: people waiting on a result beat background discovery.
_PRIORITY = case((JobRow.type == SCAN, 0), (JobRow.type == FEEDS, 1), else_=2)

STALE_AFTER = timedelta(minutes=10)


def enqueue(
    session: Session,
    job_type: str,
    payload: dict,
    dedupe_key: str | None = None,
    delay: timedelta | None = None,
) -> int:
    """Add a job. With a dedupe_key, an identical pending/running job is reused."""
    if dedupe_key:
        existing = session.scalars(
            select(JobRow.id).where(
                JobRow.dedupe_key == dedupe_key, JobRow.status.in_(("pending", "running"))
            )
        ).first()
        if existing:
            return existing
    job = JobRow(
        type=job_type,
        payload=payload,
        dedupe_key=dedupe_key,
        run_after=utcnow() + (delay or timedelta(0)),
    )
    session.add(job)
    session.commit()
    return job.id


def claim(session: Session, types: tuple[str, ...] = ALL_TYPES) -> JobRow | None:
    """Take the next due job of the given types: user scans first, then oldest.
    SKIP LOCKED lets several workers share the queue."""
    job = session.scalars(
        select(JobRow)
        .where(
            JobRow.status == "pending",
            JobRow.run_after <= utcnow(),
            JobRow.type.in_(types),
        )
        .order_by(_PRIORITY, JobRow.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).first()
    if job is None:
        session.commit()
        return None
    job.status = "running"
    job.locked_at = utcnow()
    job.attempts += 1
    session.commit()
    return job


def complete(session: Session, job_id: int) -> None:
    job = session.get(JobRow, job_id)
    job.status = "done"
    job.error = None
    job.finished_at = utcnow()
    session.commit()


def fail(session: Session, job_id: int, error: str) -> None:
    """Retry with backoff (30s, 60s, ...) until JOB_MAX_ATTEMPTS, then mark failed."""
    job = session.get(JobRow, job_id)
    job.error = error[:2000]
    if job.attempts < JOB_MAX_ATTEMPTS:
        job.status = "pending"
        job.run_after = utcnow() + timedelta(seconds=30 * job.attempts)
    else:
        job.status = "failed"
        job.finished_at = utcnow()
    session.commit()


def requeue_stale(session: Session) -> int:
    """Put back jobs left 'running' by a worker that crashed."""
    stale = session.scalars(
        select(JobRow).where(JobRow.status == "running", JobRow.locked_at < utcnow() - STALE_AFTER)
    ).all()
    for job in stale:
        job.status = "pending"
    session.commit()
    return len(stale)
