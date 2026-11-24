import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

from app.api_models import Case, EvidenceExport, Takedown
from app.contracts import (
    CloakingCheck,
    DesktopVisit,
    DownloadSignal,
    Evidence,
    Label,
    Rdap,
    Verdict,
)
from app.graph import related_domains
from app.mock.data import build_cases
from app.report import build_report
from app.takedown import build_takedown

NOW = datetime(2026, 11, 24, 13, 30, tzinfo=timezone.utc)


def _pages(pdf: bytes) -> int:
    return len(re.findall(rb"/Type /Page\b", pdf))


def _mock(case_id: str) -> Case:
    return next(c for c in build_cases() if c.id == case_id)


def test_report_pdf_for_full_case(client):
    res = client.get("/api/cases/c-0001/report.pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.headers["content-disposition"] == 'attachment; filename="scamshield-c-0001.pdf"'
    assert res.content.startswith(b"%PDF")
    assert _pages(res.content) >= 2


def test_report_pdf_without_evidence(client):
    res = client.get("/api/cases/c-0006/report.pdf")
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")


def test_report_pdf_unknown_case_is_404(client):
    assert client.get("/api/cases/c-9999/report.pdf").status_code == 404


def test_report_survives_missing_screenshot_odd_text_and_shared_hosting():
    case = _mock("c-0002")
    ev = case.evidence
    ev.screenshot_path = "screenshots/missing.png"
    ev.screenshot_sha256 = "0" * 64
    ev.title = "UAE PASS \U0001f6a8 تسجيل الدخول \x00\x07"
    ev.url = case.candidate.url = "https://uaepass-login.test/" + "a" * 600
    ev.shared_hosting = True
    ev.download_signals = [DownloadSignal(kind="remote_access_link", href="https://anydesk.test/")]
    ev.cloaking = CloakingCheck(
        signals=["desktop_blocked"],
        desktop=DesktopVisit(fetch_error="timeout", screenshot_path="../../etc/passwd"),
    )
    pdf = build_report(case, related_domains(case.id, build_cases()), now=NOW)
    assert pdf.startswith(b"%PDF")


def test_report_without_whois_or_reasons():
    case = _mock("c-0004")
    case.evidence = Evidence(
        url=case.candidate.url, fetched_at=NOW, fetch_error="Offline: NXDOMAIN"
    )
    case.verdict = Verdict(
        url=case.candidate.url,
        verdict=Label.SUSPICIOUS,
        score=40,
        reasons=[],
        model_version="test",
        scored_at=NOW,
    )
    assert build_report(case, [], now=NOW).startswith(b"%PDF")


def test_takedown_recipients_and_mailto(client):
    td = Takedown.model_validate(client.get("/api/cases/c-0001/takedown").json())
    assert td.recipients == ["abuse@registrar.test", "abuse@hosting.test"]
    assert td.mailto.startswith("mailto:abuse@registrar.test,abuse@hosting.test?")
    assert " " not in td.mailto and "\n" not in td.mailto
    query = parse_qs(urlsplit(td.mailto).query)
    assert query["subject"] == [td.subject]
    assert query["body"] == [td.body_en.replace("\n", "\r\n")]


def test_takedown_recipients_deduplicated_and_empty_without_contacts():
    case = _mock("c-0001")
    case.evidence.rdap = Rdap(registrar="Same Co", abuse_email="Abuse@same.test")
    case.evidence.hosting_abuse_email = "abuse@same.test"
    assert build_takedown(case).recipients == ["Abuse@same.test"]

    td = build_takedown(_mock("c-0006"))  # no evidence
    assert td.recipients == []
    assert td.mailto is None


def test_takedown_first_seen_is_readable_utc():
    case = _mock("c-0001")
    case.candidate.discovered_at = datetime(2026, 11, 24, 17, 37, 37, 981352, tzinfo=timezone(timedelta(hours=4)))
    td = build_takedown(case)
    assert "First seen: 2026-11-24 13:37 UTC\n" in td.body_en
    assert "2026-11-24 13:37 UTC" in td.body_ar


def test_related_domains_seen_from_one_case():
    related = related_domains("c-0001", build_cases())
    assert {(r.case_id, r.type) for r in related} >= {("c-0005", "same_ip"), ("c-0002", "same_ip")}
    assert all(r.case_id != "c-0001" for r in related)
    assert next(r for r in related if r.case_id == "c-0005").domain == "s.test"


def test_export_json_bundle(client):
    res = client.get("/api/cases/c-0001/export.json")
    assert res.status_code == 200
    assert res.headers["content-disposition"] == 'attachment; filename="scamshield-c-0001.json"'
    bundle = EvidenceExport.model_validate(res.json())
    assert bundle.case.id == "c-0001"
    assert bundle.takedown.recipients
    assert bundle.model_version
    assert ("c-0005", "same_ip") in {(r.case_id, r.type) for r in bundle.related}
    assert client.get("/api/cases/c-9999/export.json").status_code == 404
