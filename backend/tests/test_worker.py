import socket
from datetime import datetime, timezone

import pytest

from app.contracts import Candidate, Evidence, Rdap, Source
from app.db import SessionLocal
from app.workers import enrich, fetcher, pipeline, runner, safety
from app.workers.radar import SOURCES


@pytest.fixture(autouse=True)
def no_network_lookups(monkeypatch):
    """Enrichment would call RDAP/DNS; tests use fixed facts instead."""
    monkeypatch.setattr(
        enrich,
        "lookup",
        lambda url: {
            "shared_hosting": False,
            "rdap": Rdap(created=datetime(2026, 11, 20, tzinfo=timezone.utc), registrar="Test Registrar"),
            "ip": "203.0.113.9",
            "asn": 64500,
            "hosting_org": "Test Hosting",
            "hosting_abuse_email": "abuse@hosting.test",
        },
    )


def _no_dns(*_args, **_kwargs):
    raise socket.gaierror("NXDOMAIN")


def _public_dns(*_args, **_kwargs):
    return [(2, 1, 6, "", ("93.184.216.34", 443))]


def test_offline_site_still_gets_domain_evidence(client, monkeypatch):
    monkeypatch.setattr(safety, "_resolve", _no_dns)
    case_id = client.post("/api/scan", json={"url": "https://brand-new.test/x"}).json()["case_id"]

    assert runner.run_once() is True
    case = client.get(f"/api/cases/{case_id}").json()
    assert case["evidence"]["fetch_error"] == "Offline: cannot resolve brand-new.test"
    assert case["evidence"]["rdap"]["registrar"] == "Test Registrar"  # enrichment still ran
    assert runner.run_once() is False


def test_private_address_is_blocked_and_not_enriched(client, monkeypatch):
    monkeypatch.setattr(safety, "_resolve", lambda *a, **k: [(2, 1, 6, "", ("10.0.0.5", 80))])
    case_id = client.post("/api/scan", json={"url": "http://intranet.test/"}).json()["case_id"]
    runner.run_once()
    evidence = client.get(f"/api/cases/{case_id}").json()["evidence"]
    assert evidence["fetch_error"].startswith("Blocked:")
    assert evidence["rdap"] is None


def test_worker_saves_fetcher_evidence(client, monkeypatch):
    monkeypatch.setattr(safety, "_resolve", _public_dns)

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
    assert case["evidence"]["hosting_org"] == "Test Hosting"


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
    def broken(url):
        raise RuntimeError("browser crashed")

    monkeypatch.setattr(fetcher, "fetch", broken)
    client.post("/api/scan", json={"url": "https://crash.test/"})
    assert runner.run_once() is True  # error caught, job set to retry
    assert runner.run_once() is False  # retry is in backoff


def test_all_five_radar_sources_are_registered():
    assert set(SOURCES) == {"lookalikes", "ct", "nrd", "search", "maps"}
