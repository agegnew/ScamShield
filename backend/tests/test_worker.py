import socket
from datetime import datetime, timezone

from app.contracts import Candidate, Evidence, Source
from app.db import SessionLocal
from app.workers import fetcher, pipeline, runner, safety
from app.workers.radar import SOURCES


def _no_dns(*_args, **_kwargs):
    raise socket.gaierror("NXDOMAIN")


def test_scan_then_worker_records_blocked_fetch(client, monkeypatch):
    monkeypatch.setattr(safety, "_resolve", _no_dns)
    case_id = client.post("/api/scan", json={"url": "https://brand-new.test/x"}).json()["case_id"]

    assert runner.run_once() is True
    case = client.get(f"/api/cases/{case_id}").json()
    assert case["evidence"]["fetch_error"].startswith("Blocked: cannot resolve")
    assert case["verdict"]["model_version"]
    assert runner.run_once() is False


def test_worker_saves_fetcher_evidence(client, monkeypatch):
    monkeypatch.setattr(safety, "_resolve", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))])

    def fake_fetch(url):
        return Evidence(
            url=url,
            final_url="https://landing.test/",
            title="Fake landing",
            fetched_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(fetcher, "fetch", fake_fetch)
    case_id = client.post("/api/scan", json={"url": "https://short.test/abc"}).json()["case_id"]
    runner.run_once()
    case = client.get(f"/api/cases/{case_id}").json()
    assert case["evidence"]["title"] == "Fake landing"
    assert case["evidence"]["final_url"] == "https://landing.test/"


def test_radar_stores_new_urls_and_queues_fetches(client, monkeypatch):
    found = [
        Candidate(
            url="https://tamm-refund.test/",
            source=Source.LOOKALIKE,
            query="tamm",
            discovered_at=datetime.now(timezone.utc),
        )
    ]
    monkeypatch.setattr(SOURCES["lookalikes"], "discover", lambda brands: found)
    monkeypatch.setattr(safety, "_resolve", _no_dns)

    with SessionLocal() as session:
        assert pipeline.run_radar(session, "lookalikes") == 1
        assert pipeline.run_radar(session, "lookalikes") == 0  # already known

    feed = client.get("/api/radar/feed").json()["items"]
    assert feed[0]["url"] == "https://tamm-refund.test/"
    assert runner.run_once() is True  # the queued fetch
    assert runner.run_once() is False


def test_failing_job_is_retried_not_fatal(client, monkeypatch):
    monkeypatch.setattr(safety, "_resolve", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))])

    def broken(url):
        raise RuntimeError("browser crashed")

    monkeypatch.setattr(fetcher, "fetch", broken)
    client.post("/api/scan", json={"url": "https://crash.test/"})
    assert runner.run_once() is True  # error caught, job set to retry
    assert runner.run_once() is False  # retry is in backoff
