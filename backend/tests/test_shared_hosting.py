from datetime import datetime, timezone

from app.api_models import Case
from app.contracts import Candidate, Evidence, Label, Rdap, Source, Verdict
from app.engine import domain_age_days
from app.graph import build_graph
from app.takedown import build_takedown

NOW = datetime(2026, 11, 24, tzinfo=timezone.utc)
OLD_PLATFORM_WHOIS = Rdap(
    created=datetime(2015, 4, 1, tzinfo=timezone.utc),
    registrar="Platform Registrar",
    abuse_email="abuse@platform-registrar.test",
)


def _evidence(url: str, shared: bool) -> Evidence:
    return Evidence(
        url=url,
        final_url=url,
        rdap=OLD_PLATFORM_WHOIS,
        ip="198.51.100.10",
        hosting_org="Platform Inc.",
        hosting_abuse_email="abuse@platform.test",
        shared_hosting=shared,
        fetched_at=NOW,
    )


def _case(case_id: str, url: str, shared: bool) -> Case:
    return Case(
        id=case_id,
        domain=url.split("/")[2],
        status="new",
        candidate=Candidate(url=url, source=Source.NRD, discovered_at=NOW),
        evidence=_evidence(url, shared),
        verdict=Verdict(
            url=url,
            verdict=Label.FRAUD,
            score=80,
            reasons=[],
            model_version="test",
            scored_at=NOW,
        ),
    )


def test_domain_age_ignored_on_shared_platform():
    assert domain_age_days(_evidence("https://tamm-pay.vercel.test/", shared=True), NOW) is None
    assert domain_age_days(_evidence("https://tamm-pay.test/", shared=False), NOW) > 3000


def test_shared_platform_sites_are_not_linked_by_platform_ip_or_whois():
    graph = build_graph(
        [
            _case("c-a", "https://tamm-pay.vercel.test/", shared=True),
            _case("c-b", "https://bank-help.vercel.test/", shared=True),
        ]
    )
    assert graph.edges == []


def test_own_domains_on_same_ip_are_still_linked():
    graph = build_graph(
        [
            _case("c-a", "https://tamm-pay.test/", shared=False),
            _case("c-b", "https://tamm-fines.test/", shared=False),
        ]
    )
    assert {e.type for e in graph.edges} == {"same_ip", "same_registration_day"}


def test_takedown_on_shared_platform_goes_to_host_not_registrar():
    td = build_takedown(_case("c-a", "https://tamm-pay.vercel.test/", shared=True))
    assert td.registrar is None
    assert td.registrar_abuse_email is None
    assert td.hosting_abuse_email == "abuse@platform.test"


def test_nrd_source_shows_in_radar_feed(client):
    client.post("/api/scan", json={"url": "https://x.test/"})  # manual, not radar
    counts = client.get("/api/radar/feed").json()["counts_by_source"]
    assert "nrd" in counts
