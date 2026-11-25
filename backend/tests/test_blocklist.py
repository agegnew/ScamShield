from app.blocklist import blockable


def test_blockable_hosts():
    assert blockable("aramexdelivery.live")
    assert blockable("www.moi-portal.com")
    assert blockable("tamm-pay.pages.dev")  # a scam on a shared platform
    assert not blockable("pages.dev")  # the platform itself
    assert not blockable("sites.google.com")  # anyone can publish there
    assert not blockable("tamm.abudhabi")  # official
    assert not blockable("emiratesnbd.com")  # official
    assert not blockable("adpolice.gov.ae")
    assert not blockable("")


def test_blocklist_endpoint(client):
    data = client.get("/api/blocklist").json()
    assert data["count"] == len(data["domains"])
    hosts = [d["domain"] for d in data["domains"]]
    assert len(hosts) == len(set(hosts))
    for d in data["domains"]:
        assert d["score"] >= 0 and d["case_id"]
        assert blockable(d["domain"])


# ---- what earns a block (25 Nov: the hackathon's own submission site was blocked) -------------

from datetime import datetime, timezone  # noqa: E402

from app.contracts import Candidate, Label, Reason, Source, Verdict  # noqa: E402
from app.repo import CaseRepo  # noqa: E402

NOW = datetime.now(timezone.utc)


def _case(repo, url, score, *codes, status="new"):
    verdict = Verdict(
        url=url, verdict=Label.FRAUD if score >= 70 else Label.SUSPICIOUS, score=score, brand_target=None,
        reasons=[Reason(code=c, weight=10, text_en=c, text_ar=c) for c in codes],
        model_version="test", scored_at=NOW,
    )
    case = repo.add(Candidate(url=url, source=Source.LOOKALIKE, discovered_at=NOW), verdict)
    if status != "new":
        repo.decide(case.id, "confirm" if status == "confirmed" else "dismiss", "test", "analyst")
    return case


def blocked_hosts(session):
    return {host for host, *_ in CaseRepo(session).scam_domains()}


def test_fraud_on_the_name_alone_is_not_blocked(session):
    repo = CaseRepo(session)
    _case(repo, "http://aramex-track.info/", 100, "url_model", "lookalike_domain", "suspicious_tld")
    _case(repo, "https://podium.aevsoft.cc/x/dashboard.php", 95, "url_model", "credential_form", "suspicious_tld")
    assert blocked_hosts(session) == set()


def test_fraud_with_hard_evidence_is_blocked(session):
    repo = CaseRepo(session)
    _case(repo, "https://moi-portal.com/", 75, "lookalike_domain", "brand_on_wrong_domain", "impersonation_confirmed")
    _case(repo, "http://fly-dubai.co/", 100, "lookalike_domain", "platform_warning")
    _case(repo, "https://2h.ae/pPGKr", 70, "threat_feed")
    assert blocked_hosts(session) == {"moi-portal.com", "fly-dubai.co", "2h.ae"}


def test_analyst_decisions_win(session):
    repo = CaseRepo(session)
    _case(repo, "http://aramex-track.info/", 100, "url_model", "lookalike_domain", status="confirmed")
    _case(repo, "http://fly-dubai.co/", 100, "platform_warning", status="dismissed")
    assert blocked_hosts(session) == {"aramex-track.info"}
