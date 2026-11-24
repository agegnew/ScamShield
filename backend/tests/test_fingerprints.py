"""Simon's fingerprint, cloaking and visual-match logic, without the network."""

from datetime import datetime, timezone

from app.api_models import Case
from app.contracts import (
    Candidate,
    Contacts,
    Evidence,
    Fingerprints,
    FormInfo,
    Label,
    Source,
    Verdict,
)
from app.graph import build_graph
from app.workers import references
from app.workers.cloaking import compare
from app.workers.fingerprint import contacts, hamming, murmur3_32, tracking_ids

NOW = datetime.now(timezone.utc)


def test_murmur3_matches_reference():
    assert (murmur3_32(b"hello"), murmur3_32(b""), murmur3_32(b"abc")) == (613153351, 0, -1277324294)


def test_trackers_and_contacts():
    html = """<script>gtag('config','G-AB12CD34EF');fbq('init', '123456789012345');</script>
              <a href="https://wa.me/971501234567">WhatsApp</a> <a href="https://t.me/fines_support">tg</a>"""
    assert tracking_ids(html) == ["facebook_pixel:123456789012345", "google_analytics:G-AB12CD34EF"]
    found = contacts("Call 050 123 4567 or mail help@pay-fines.com", html)
    assert found.phones == ["+971501234567"]
    assert found.whatsapp == ["+971501234567"]
    assert found.telegram == ["fines_support"]
    assert found.emails == ["help@pay-fines.com"]


def test_hamming():
    assert hamming("ff00", "ff01") == 1


def page(error=None, final_url="https://a-fines.com/", title="Pay fine", sensitive=(), dhash="0" * 16):
    return Evidence(
        url="https://a-fines.com/",
        final_url=final_url,
        title=title,
        fetch_error=error,
        forms=[FormInfo(sensitive=list(sensitive))],
        fingerprints=Fingerprints(screenshot_dhash=dhash),
        fetched_at=NOW,
    )


def test_same_page_has_no_cloaking_signal():
    assert compare(page(), page()) == []


def test_cloaked_scam_is_flagged():
    mobile = page(sensitive=["card", "otp"], dhash="ffffffffffffffff")
    desktop = page(final_url="https://www.google.com/", title="Google", dhash="0000000000000000")
    assert compare(mobile, desktop) == ["different_destination", "forms_hidden_from_desktop", "different_page"]


def test_desktop_blocked():
    assert compare(page(), page(error="Error: net::ERR_CONNECTION_RESET")) == ["desktop_blocked"]


def test_visual_match_on_reused_official_favicon(monkeypatch):
    refs = [{"brand": "tamm", "domain": "tamm.abudhabi", "final_url": "https://www.tamm.abudhabi/",
             "favicon_sha256": "abc123", "dom_hash": "d1"}]
    monkeypatch.setattr(references, "load", lambda: refs)
    match = references.visual_match("https://tamm-pay.xyz/", Fingerprints(favicon_sha256="abc123"))
    assert (match.brand, match.kind) == ("tamm", "same_favicon")
    assert references.visual_match("https://www.tamm.abudhabi/", Fingerprints(favicon_sha256="abc123")) is None


def _case(case_id: str, fp: Fingerprints) -> Case:
    url = f"https://{case_id}.test/"
    return Case(
        id=case_id, domain=f"{case_id}.test", status="new",
        candidate=Candidate(url=url, source=Source.LOOKALIKE, discovered_at=NOW),
        evidence=Evidence(url=url, final_url=url, fingerprints=fp, fetched_at=NOW),
        verdict=Verdict(url=url, verdict=Label.FRAUD, score=80, reasons=[], model_version="t", scored_at=NOW),
    )


def test_graph_links_sites_sharing_tracker_and_whatsapp():
    shared = Fingerprints(tracking_ids=["google_analytics:G-AB12CD34EF"],
                          contacts=Contacts(whatsapp=["+971501234567"]))
    graph = build_graph([_case("a", shared), _case("b", shared), _case("c", Fingerprints())])
    assert {(e.source, e.target, e.type) for e in graph.edges} == {
        ("a", "b", "same_tracker"),
        ("a", "b", "same_contact"),
    }



def test_graph_ignores_fingerprints_of_parked_pages():
    # Hostinger's parking page carries Hostinger's tracker: it must not link unrelated domains.
    shared = Fingerprints(tracking_ids=["google_analytics:G-S4HMJ5EXYY"])
    cases = [_case("a", shared), _case("b", shared)]
    for case in cases:
        case.evidence.page_kind = "parked"
    assert build_graph(cases).edges == []
