"""Worker process: schedules radar sources and runs queued jobs.

    python -m app.workers.runner

Run several copies to go faster; the queue hands each job to one worker.
"""

import logging
import time

from .. import jobs
from ..config import WORKER_POLL_SECONDS
from ..db import SessionLocal, init_db
from ..engine import feeds
from .pipeline import HANDLERS
from .radar import SOURCES

log = logging.getLogger("scamshield.worker")


def schedule_radar(next_due: dict[str, float]) -> None:
    now = time.monotonic()
    with SessionLocal() as session:
        for name, source in SOURCES.items():
            if not source.enabled() or now < next_due.get(name, 0):
                continue
            jobs.enqueue(session, jobs.RADAR, {"source": name}, dedupe_key=f"radar:{name}")
            next_due[name] = now + source.interval_minutes * 60
        if now >= next_due.get("_feeds", 0):
            jobs.enqueue(session, jobs.FEEDS, {}, dedupe_key="feeds")
            next_due["_feeds"] = now + feeds.REFRESH_MINUTES * 60


def run_once() -> bool:
    """Claim and run one job. Returns False when the queue is empty."""
    with SessionLocal() as session:
        job = jobs.claim(session)
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
        "worker started; radar sources enabled: %s; requeued %d stale jobs",
        [name for name, s in SOURCES.items() if s.enabled()],
        requeued,
    )
    next_due: dict[str, float] = {}
    while True:
        schedule_radar(next_due)
        if not run_once():
            time.sleep(WORKER_POLL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        run_forever()
    except KeyboardInterrupt:
        log.info("worker stopped")
