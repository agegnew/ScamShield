from app.api_models import Case, CaseList, CheckResponse, Graph, RadarFeed, Takedown
from app.brands import normalize_uae_phone


def test_health_reports_mock_mode(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["mode"] == "mock"
    assert res.headers["X-ScamShield-Mode"] == "mock"


def test_brands_load_from_registry(client):
    ids = {b["id"] for b in client.get("/api/brands").json()}
    assert {"tamm", "uaepass", "emiratesnbd", "rta"} <= ids


def test_radar_feed_is_newest_first_and_excludes_citizen_submissions(client):
    feed = RadarFeed.model_validate(client.get("/api/radar/feed").json())
    times = [item.discovered_at for item in feed.items]
    assert times == sorted(times, reverse=True)
    assert all(item.source.value != "citizen" for item in feed.items)
    assert feed.counts_by_source["citizen"] == 1


def test_cases_filter_by_verdict(client):
    body = CaseList.model_validate(client.get("/api/cases", params={"verdict": "FRAUD"}).json())
    assert body.total == 4
    assert all(item.verdict.value == "FRAUD" for item in body.items)


def test_case_detail_and_404(client):
    case = Case.model_validate(client.get("/api/cases/c-0001").json())
    assert case.evidence.rdap.registrar
    assert client.get("/api/cases/c-9999").status_code == 404


def test_decision_updates_status_and_records_user(client):
    res = client.post(
        "/api/cases/c-0002/decision",
        json={"action": "confirm", "reason": "Copies UAE PASS login"},
        headers={"Authorization": "Bearer mock-admin"},
    )
    case = Case.model_validate(res.json())
    assert case.status == "confirmed"
    assert case.decisions[-1].by == "admin"


def test_decision_rejects_unknown_action(client):
    res = client.post("/api/cases/c-0002/decision", json={"action": "delete", "reason": "nope"})
    assert res.status_code == 422


def test_scan_rejects_non_http_and_adds_scheme(client):
    assert client.post("/api/scan", json={"url": "ftp://example.test/x"}).status_code == 422
    res = client.post("/api/scan", json={"url": "new-site.test/login"})
    assert res.status_code == 200
    case = client.get(f"/api/cases/{res.json()['case_id']}").json()
    assert case["candidate"]["url"] == "http://new-site.test/login"


def test_batch_returns_one_row_per_url_with_errors_inline(client):
    urls = ["https://tamm-fines-pay.test/pay?ref=AD-55120", "https://www.rta.ae/", "ftp://bad"]
    items = client.post("/api/batch", json={"urls": urls}).json()["items"]
    assert [i["verdict"] for i in items] == ["FRAUD", "LEGIT", None]
    assert items[2]["error"]

    csv_text = client.post("/api/batch?format=csv", json={"urls": urls}).text
    assert csv_text.splitlines()[0] == "url,verdict,score,brand_target,reason_codes,error"
    assert len(csv_text.splitlines()) == 4


def test_check_official_helpline_is_legit(client):
    res = CheckResponse.model_validate(client.post("/api/check", json={"input": "+971 600 54 0000"}).json())
    assert res.kind == "phone"
    assert res.verdict == "LEGIT"
    assert res.brand_target == "emiratesnbd"


def test_check_scam_listing_phone_is_fraud(client):
    res = CheckResponse.model_validate(client.post("/api/check", json={"input": "045550199"}).json())
    assert res.verdict == "FRAUD"
    assert res.headline_ar


def test_check_unknown_phone_is_unknown(client):
    res = client.post("/api/check", json={"input": "050 123 4567"}).json()
    assert res["verdict"] == "UNKNOWN"
    assert res["score"] is None


def test_check_redirect_target_matches_shortened_case(client):
    res = client.post("/api/check", json={"input": "tamm-violations.test/pay"}).json()
    assert res["kind"] == "url"
    assert res["verdict"] == "FRAUD"


def test_graph_links_cases_sharing_infrastructure(client):
    graph = Graph.model_validate(client.get("/api/graph").json())
    node_ids = {n.id for n in graph.nodes}
    assert all(e.source in node_ids and e.target in node_ids for e in graph.edges)
    pairs = {(e.source, e.target, e.type) for e in graph.edges}
    assert ("c-0001", "c-0005", "same_ip") in pairs
    assert ("c-0001", "c-0005", "same_registration_day") in pairs
    assert all(n.verdict.value != "LEGIT" for n in graph.nodes)


def test_takedown_includes_abuse_contacts_and_both_languages(client):
    td = Takedown.model_validate(client.get("/api/cases/c-0001/takedown").json())
    assert td.registrar_abuse_email == "abuse@registrar.test"
    assert td.hosting_abuse_email == "abuse@hosting.test"
    assert "tamm-fines-pay.test" in td.body_en
    assert "الأدلة" in td.body_ar


def test_login_and_screenshot_served(client):
    assert client.post("/api/auth/login", json={"username": "admin", "password": "x"}).status_code == 200
    assert client.post("/api/auth/login", json={"username": "eve", "password": "x"}).status_code == 401
    assert client.get("/artifacts/mock/screenshot.svg").status_code == 200


def test_normalize_uae_phone_variants():
    assert normalize_uae_phone("+971 4 555 0199") == "45550199"
    assert normalize_uae_phone("04 555 0199") == "45550199"
    assert normalize_uae_phone("00971 600 54 0000") == "600540000"
