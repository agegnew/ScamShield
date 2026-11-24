"""Worker process: runs queued jobs and (optionally) starts the daily radar run (03:00 UAE).

    python -m app.workers.runner                      # everything in one process (local dev)
    SCAMSHIELD_WORKER_JOBS=scan,fetch,feeds python -m app.workers.runner   # page fetching only
    SCAMSHIELD_WORKER_JOBS=radar SCAMSHIELD_WORKER_SCHEDULE=1 python -m app.workers.runner

docker-compose runs two: `worker` fetches pages (user scans first) and `radar` runs the
slow discovery sources, so a scan never waits behind a radar run. Scale fetching with
`docker compose up --scale worker=3`; the queue hands each job to one worker.
"""

import logging
import os
import time

from .. import jobs, radar_runs
from ..config import WORKER_POLL_SECONDS
from ..db import SessionLocal, init_db
from ..engine import feeds
from .pipeline import HANDLERS
from .radar import SOURCES

log = logging.getLogger("scamshield.worker")

JOB_TYPES = tuple(
    t.strip() for t in os.getenv("SCAMSHIELD_WORKER_JOBS", ",".join(jobs.ALL_TYPES)).split(",") if t.strip()
)
SCHEDULE = os.getenv("SCAMSHIELD_WORKER_SCHEDULE", "1") == "1"


def schedule_radar(next_due: dict) -> None:
    """The whole radar runs once a day (radar_runs.DAILY_AT, 03:00 UAE) and on the Radar page's
    "Run radar now" button; phishing feeds refresh every hour."""
    radar_runs.maybe_start_daily(next_due)
    now = time.monotonic()
    if now >= next_due.get("_feeds", 0):
        with SessionLocal() as session:
            jobs.enqueue(session, jobs.FEEDS, {}, dedupe_key="feeds")
        next_due["_feeds"] = now + feeds.REFRESH_MINUTES * 60


def run_once(types: tuple[str, ...] = jobs.ALL_TYPES) -> bool:
    """Claim and run one job. Returns False when there is nothing to do."""
    with SessionLocal() as session:
        job = jobs.claim(session, types)
        if job is None:
            return False
        job_id, job_type, payload = job.id, job.type, dict(job.payload)

    with SessionLocal() as session:
        handler = HANDLERS.get(job_type)
        try:
            if handler is None:
                raise ValueError(f"unknown job type {job_type}")
            handler(session, payload)
        except Exception as exc:  # one bad job must not stop the worker
            session.rollback()
            log.exception("job %s (%s) failed", job_id, job_type)
            jobs.fail(session, job_id, f"{type(exc).__name__}: {exc}")
        else:
            jobs.complete(session, job_id)
    return True


def run_forever() -> None:
    init_db()
    with SessionLocal() as session:
        requeued = jobs.requeue_stale(session)
    log.info(
        "worker started; jobs %s; daily radar run: %s (next %s; sources %s); requeued %d stale jobs",
        list(JOB_TYPES),
        SCHEDULE and radar_runs.DAILY,
        radar_runs.next_daily().isoformat(timespec="minutes"),
        [name for name, s in SOURCES.items() if s.has_key()],
        requeued,
    )
    next_due: dict = {}
    while True:
        if SCHEDULE:
            schedule_radar(next_due)
        if not run_once(JOB_TYPES):
            time.sleep(WORKER_POLL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        run_forever()
    except KeyboardInterrupt:
        log.info("worker stopped")
