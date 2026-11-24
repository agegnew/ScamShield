"""Radar v2 (docs/radar-ui.md): runs, feed categories and details, the SerpApi budget, new brands."""

import os
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app import engine, jobs, radar_runs
from app.brand_match import match_brand
from app.brands import brand_by_id
from app.contracts import Candidate, CandidateExtra, Source
from app.db import JobRow, SessionLocal
from app.engine.checks import _page_names
from app.repo import CaseRepo
from app.workers import pipeline
from app.workers.radar import SOURCES, search, serp

NOW = datetime.now(timezone.utc)


def _cand(url, source, brand=None, query=None, listing_name=None, phone=None, **details):
    return Candidate(
        url=url, source=source, query=query or brand, discovered_at=NOW,
        extra=CandidateExtra(brand=brand, listing_name=listing_name, phone=phone, details=details),
    )


def _fake(monkeypatch, name, found):
    def discover(brands):
        SOURCES[name].report(1, 2)
        SOURCES[name].report(2, 2)
        return found

    monkeypatch.setattr(SOURCES[name], "discover", discover)


def _execute(run_id):
    with SessionLocal() as session:
        pipeline.HANDLERS[jobs.RADAR](session, {"run": run_id})


def _finish_page_checks():
    with SessionLocal() as session:
        for job in session.scalars(select(JobRow).where(JobRow.type == jobs.FETCH)):
            job.status = "done"
        session.commit()


# ---- runs -------------------------------------------------------------------------


def test_run_needs_login_starts_once_and_skips_keyless_sources(client, analyst_headers):
    assert client.post("/api/radar/run").status_code == 401
    res = client.post("/api/radar/run", json={"sources": ["lookalikes", "search"]}, headers=analyst_headers)
    assert res.status_code == 202, res.text
    run = res.json()["run"]
    assert run["trigger"] == "manual" and run["started_by"] == "analyst" and run["status"] == "running"
    assert [(s["name"], s["status"], s.get("note")) for s in run["sources"]] == [
        ("lookalikes", "waiting", None), ("search", "skipped", "needs_key")]

    again = client.post("/api/radar/run", headers=analyst_headers)
    assert again.status_code == 409
    assert again.json()["detail"] == "radar_already_running" and again.json()["run"]["id"] == run["id"]
    bad = client.post("/api/radar/run", json={"brands": ["nope"]}, headers=analyst_headers)
    assert bad.status_code == 400
    assert client.get("/api/radar/status").json()["running"] is True


def test_run_finds_checks_riskiest_first_and_finishes(client, analyst_headers, monkeypatch):
    _fake(monkeypatch, "lookalikes", [
        _cand("https://example-garden-blog.org/", Source.LOOKALIKE, variant="omission"),
        _cand("https://tamm-fines-pay.com/", Source.LOOKALIKE, brand="tamm", variant="dictionary"),
    ])
    _fake(monkeypatch, "ct", [_cand("https://uaepass-verify.online/", Source.CT, brand="uaepass",
                                    cert_issued="2026-11-24T10:00:00", issuer="R3")])
    run_id = client.post("/api/radar/run", json={"sources": ["lookalikes", "ct"]},
                         headers=analyst_headers).json()["run"]["id"]
    _execute(run_id)

    status = client.get("/api/radar/status").json()
    run = status["run"]
    assert status["running"] is True  # discovery done, page checks still queued
    lookalikes = run["sources"][0]
    assert (lookalikes["status"], lookalikes["found"], lookalikes["new"]) == ("done", 2, 2)
    assert (lookalikes["checked"], lookalikes["total"]) == (2, 2)
    assert run["pages"] == {"checked": 0, "total": 3}
    assert run["verdicts"] == {"FRAUD": 0, "SUSPICIOUS": 0, "LEGIT": 0}  # all three, even at zero

    with SessionLocal() as session:  # riskiest URL is checked first
        first = session.scalars(select(JobRow).where(JobRow.type == jobs.FETCH).order_by(JobRow.id)).first()
    assert first.payload["url"] == "https://tamm-fines-pay.com/"

    _finish_page_checks()
    status = client.get("/api/radar/status").json()
    assert status["running"] is False
    assert status["run"]["status"] == "done" and status["run"]["finished_at"]
    assert status["run"]["pages"] == {"checked": 3, "total": 3}
    assert sum(status["run"]["verdicts"].values()) == 3
    assert {s["name"]: s["last_new"] for s in status["sources"]}["lookalikes"] == 2
    assert client.post("/api/radar/run", headers=analyst_headers).status_code == 202  # free again
    assert client.get("/api/radar/runs").json()[1]["id"] == run_id


def test_page_checks_are_capped_per_run(client, analyst_headers, monkeypatch):
    monkeypatch.setattr(radar_runs, "MAX_FETCH", 1)
    _fake(monkeypatch, "lookalikes", [
        _cand("https://tamm-fines-pay.com/", Source.LOOKALIKE, brand="tamm"),
        _cand("https://example-garden-blog.org/", Source.LOOKALIKE),
    ])
    run_id = client.post("/api/radar/run", json={"sources": ["lookalikes"]},
                         headers=analyst_headers).json()["run"]["id"]
    _execute(run_id)
    run = client.get("/api/radar/status").json()["run"]
    assert run["pages"]["total"] == 1
    _finish_page_checks()
    run = client.get("/api/radar/status").json()["run"]
    assert run["status"] == "done" and sum(run["verdicts"].values()) == 2  # the unchecked one keeps its URL verdict


def test_a_broken_source_does_not_stop_the_run(client, analyst_headers, monkeypatch):
    def broken(brands):
        raise RuntimeError("crt.sh down")

    monkeypatch.setattr(SOURCES["ct"], "discover", broken)
    _fake(monkeypatch, "nrd", [])
    run_id = client.post("/api/radar/run", json={"sources": ["ct", "nrd"]},
                         headers=analyst_headers).json()["run"]["id"]
    _execute(run_id)
    run = client.get("/api/radar/status").json()["run"]
    assert [(s["name"], s["status"], s.get("note")) for s in run["sources"]] == [
        ("ct", "failed", "RuntimeError"), ("nrd", "done", None)]
    assert run["status"] == "done"


def test_daily_run_time_and_trigger(client, monkeypatch):
    monkeypatch.setattr(radar_runs, "DAILY_AT", "03:00")
    uae = radar_runs.UAE
    assert radar_runs.next_daily(datetime(2026, 11, 25, 1, 0, tzinfo=uae)) == datetime(2026, 11, 25, 3, 0, tzinfo=uae)
    assert radar_runs.next_daily(datetime(2026, 11, 25, 4, 0, tzinfo=uae)) == datetime(2026, 11, 26, 3, 0, tzinfo=uae)

    state: dict = {}
    radar_runs.maybe_start_daily(state)  # a worker started now waits for the next 03:00
    assert client.get("/api/radar/status").json()["run"] is None
    state["daily_due"] = NOW - timedelta(minutes=1)
    radar_runs.maybe_start_daily(state)
    run = client.get("/api/radar/status").json()["run"]
    assert run["trigger"] == "schedule" and run["started_by"] is None
    assert state["daily_due"] > NOW
    schedule = client.get("/api/radar/status").json()["schedule"]
    assert schedule["time"] == "03:00" and schedule["timezone"] == "Asia/Dubai"


# ---- feed: categories and source details ------------------------------------------------


def test_feed_filters_counts_and_source_details(client):
    with SessionLocal() as session:
        repo = CaseRepo(session)
        for c in [
            _cand("http://tamm-pay.com/", Source.LOOKALIKE, brand="tamm", variant="combo"),
            _cand("https://emiratesnbd-verify.top/login", Source.SEARCH, brand="emiratesnbd",
                  query="emirates nbd online banking login", position=3, title="Login", lang="en"),
            _cand("https://emiratesnbd-secure.top/", Source.SEARCH_AD, brand="emiratesnbd", position=1),
            _cand("https://maps.example/place", Source.MAPS, brand="aramex", listing_name="Aramex Help",
                  phone="+971500000000", flags=["helpline_not_official"], rating=4.1, replayed=True),
            _cand("http://uaepass-update.xyz/", Source.NRD, brand="uaepass", registered_on="2026-11-24"),
            _cand("https://cheap-deals-today.top/", Source.CT, cert_issued="2026-11-24T10:00:00", issuer="R3"),
        ]:
            repo.upsert_candidate(c)

    feed = client.get("/api/radar/feed?limit=100").json()
    by_url = {i["url"]: i for i in feed["items"]}
    assert by_url["http://tamm-pay.com/"]["source_details"] == {"variant": "dictionary"}  # old name mapped
    assert by_url["http://tamm-pay.com/"]["brand_category"] == "government"
    search_item = by_url["https://emiratesnbd-verify.top/login"]
    assert search_item["brand_category"] == "bank"
    assert search_item["source_details"]["query"] == "emirates nbd online banking login"
    assert search_item["source_details"]["position"] == 3 and search_item["source_details"]["replayed"] is False
    maps_item = by_url["https://maps.example/place"]["source_details"]
    assert maps_item["helpline_mismatch"] is True and maps_item["listing_name"] == "Aramex Help"
    assert maps_item["replayed"] is True
    assert by_url["http://uaepass-update.xyz/"]["source_details"] == {"registered_on": "2026-11-24"}
    assert by_url["https://cheap-deals-today.top/"]["source_details"] == {
        "issuer": "R3", "issued_at": "2026-11-24T10:00:00"}

    searched = client.get("/api/radar/feed?source=search").json()["items"]
    assert {i["source"] for i in searched} == {"search", "search_ad"}
    banks = client.get("/api/radar/feed?category=bank").json()["items"]
    assert banks and all(i["brand_category"] == "bank" for i in banks)
    none = client.get("/api/radar/feed?category=none").json()["items"]
    assert none and all(i["brand_target"] is None for i in none)
    assert [i["url"] for i in client.get("/api/radar/feed?q=uaepass-update").json()["items"]] == [
        "http://uaepass-update.xyz/"]

    counts = client.get("/api/radar/feed?category=bank").json()["counts_by_category"]
    assert counts["bank"] >= 2 and counts["none"] >= 1 and counts["government"] >= 1  # filters ignored


# ---- SerpApi budget ---------------------------------------------------------------------


@pytest.fixture
def serp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(serp, "CACHE_DIR", tmp_path)
    return tmp_path


def _age(params, hours):
    path = serp._cache_path(params)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"organic_results": []}', encoding="utf-8")
    old = (NOW - timedelta(hours=hours)).timestamp()
    os.utime(path, (old, old))


def test_plan_spends_on_new_then_stalest_weighted_queries(serp_cache):
    a = serp.Query({"engine": "google", "q": "a"}, 3.0, "a")  # never searched, important
    b = serp.Query({"engine": "google", "q": "b"}, 1.0, "b")  # never searched
    c = serp.Query({"engine": "google", "q": "c"}, 2.0, "c")  # 30 h old
    d = serp.Query({"engine": "google", "q": "d"}, 3.0, "d")  # fresh: reused for free
    _age(c.params, 30)
    _age(d.params, 1)
    assert [q.label for q in serp.plan([d, c, b, a], 2)] == ["a", "b"]
    assert [q.label for q in serp.plan([d, c, b, a], 10)] == ["a", "b", "c"]


def test_serpapi_spends_only_planned_searches(serp_cache, monkeypatch):
    calls = []

    class Ok:
        status_code = 200
        text = '{"organic_results": [{"link": "https://x.test/"}]}'

        def json(self):
            return {"organic_results": [{"link": "https://x.test/"}]}

    monkeypatch.setenv("SERPAPI_KEY", "test-key")
    monkeypatch.setattr(serp.requests, "get", lambda url, params, timeout: calls.append(params["q"]) or Ok())
    a, b = {"engine": "google", "q": "a"}, {"engine": "google", "q": "b"}
    with serp.budget(5) as spend:
        spend.allow({serp._cache_path(a).name})
        assert serp.serpapi(a)["organic_results"]  # live
        assert serp.serpapi(b) == {}  # not planned: no search, nothing saved
        assert serp.serpapi(a)["_replayed"] is True  # fresh answer reused
    assert calls == ["a"] and spend.spent == 1


def test_run_budget_spreads_the_month(monkeypatch):
    monkeypatch.setattr(serp, "RUN_MAX", 40)
    monkeypatch.setattr(serp, "RESERVE", 30)
    assert serp.run_budget("manual", left=250) == 40
    assert serp.run_budget("manual", left=12) == 12
    assert serp.run_budget("schedule", left=250, today=date(2026, 11, 25)) == 36  # 220 over 6 days
    assert serp.run_budget("schedule", left=250, today=date(2026, 11, 1)) == 7  # 220 over 30 days
    assert serp.run_budget("schedule", left=20, today=date(2026, 11, 25)) == 0  # only the reserve is left
    assert serp.run_budget("manual", left=0) == 0


def test_search_radar_spends_two_thirds_on_victim_searches_first(serp_cache, monkeypatch):
    calls = []

    class Empty:
        status_code = 200
        text = "{}"

        def json(self):
            return {}

    monkeypatch.setenv("SERPAPI_KEY", "test-key")
    monkeypatch.setattr(serp.requests, "get", lambda url, params, timeout: calls.append(params["q"]) or Empty())
    with serp.budget(6):
        search.GoogleSearch().discover([brand_by_id("tamm"), brand_by_id("emiratesnbd")])
    generic = {q for q, _ in search.GENERIC_QUERIES}
    assert len(calls) == 4 and set(calls) <= generic


def test_search_hits_on_popular_sites_are_skipped_but_not_on_free_hosting():
    assert serp.is_neutral("www.dailymotion.com") and serp.is_neutral("www.youtube.com")
    assert serp.is_neutral("www.tamm.abudhabi")  # government
    assert not serp.is_neutral("sites.google.com")  # anyone can publish a fake page there
    assert not serp.is_neutral("tamm-pay.wixsite.com") and not serp.is_neutral("evil.pages.dev")


# ---- new brands -------------------------------------------------------------------------


@pytest.mark.parametrize("url", [
    "https://www.emiratesislamic.ae/", "https://rakpolice.gov.ae/", "https://www.noon.com/uae-en/",
    "https://www.emirates.com/ae/english/", "https://www.etihad.com/", "https://www.parkin.ae/",
])
def test_new_brands_official_sites_are_legit(url):
    v = engine.score(url)
    assert v.verdict.value == "LEGIT" and v.score == 0


def test_new_brands_no_false_typos_and_longest_token_wins():
    assert all(r.code != "typosquat" for r in engine.score("https://parking.ae/").reasons)  # parkin.ae
    assert all(r.code != "typosquat" for r in engine.score("https://more.com/").reasons)  # mohre
    assert match_brand("dubaicustoms-uae.com") == "dubaicustoms"  # not adcustoms' "customs-uae"
    assert match_brand("parking-dubai.com") is None and match_brand("parkin-pay.com") == "parkin"
    assert match_brand("afternoon-tea.ae") is None and match_brand("noon-uae.shop") == "noon"
    assert match_brand("emirates247.com") is None and match_brand("emirates-airline-gift.com") == "emiratesairline"
    assert engine.score("https://dubaidutyfree-winner.com/claim").verdict.value == "FRAUD"


def test_common_words_are_not_brand_names_on_pages():
    assert _page_names(brand_by_id("noon")) == []  # "noon", Arabic "نون"
    assert "emirates" not in _page_names(brand_by_id("emiratesairline"))
    assert "emirates airline" in _page_names(brand_by_id("emiratesairline"))
    assert "طلبات" not in _page_names(brand_by_id("talabat"))  # Arabic for "orders"
    assert brand_by_id("noon").category == "shopping" and brand_by_id("flydubai").category == "travel"
