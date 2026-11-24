from app import jobs
from app.db import JobRow


def test_enqueue_reuses_pending_job_with_same_key(session):
    a = jobs.enqueue(session, jobs.FETCH, {"url": "https://a.test/"}, dedupe_key="fetch:a")
    b = jobs.enqueue(session, jobs.FETCH, {"url": "https://a.test/"}, dedupe_key="fetch:a")
    assert a == b


def test_claim_takes_oldest_and_marks_running(session):
    first = jobs.enqueue(session, jobs.FETCH, {"url": "https://1.test/"})
    jobs.enqueue(session, jobs.FETCH, {"url": "https://2.test/"})
    job = jobs.claim(session)
    assert job.id == first
    assert job.status == "running"
    assert job.attempts == 1


def test_failed_job_waits_before_retry(session):
    job_id = jobs.enqueue(session, jobs.FETCH, {"url": "https://x.test/"})
    jobs.claim(session)
    jobs.fail(session, job_id, "boom")
    assert session.get(JobRow, job_id).status == "pending"
    assert jobs.claim(session) is None  # backoff not elapsed yet


def test_job_gives_up_after_max_attempts(session, monkeypatch):
    monkeypatch.setattr(jobs, "JOB_MAX_ATTEMPTS", 1)
    job_id = jobs.enqueue(session, jobs.FETCH, {"url": "https://x.test/"})
    jobs.claim(session)
    jobs.fail(session, job_id, "boom")
    row = session.get(JobRow, job_id)
    assert row.status == "failed"
    assert row.error == "boom"


def test_completed_key_can_be_enqueued_again(session):
    first = jobs.enqueue(session, jobs.RADAR, {"source": "ct"}, dedupe_key="radar:ct")
    jobs.claim(session)
    jobs.complete(session, first)
    second = jobs.enqueue(session, jobs.RADAR, {"source": "ct"}, dedupe_key="radar:ct")
    assert second != first
