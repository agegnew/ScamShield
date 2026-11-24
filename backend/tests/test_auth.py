from datetime import datetime, timedelta, timezone

import jwt

from app import auth
from app.api_models import Case, DecisionLogEntry, LoginResponse, User, UserInfo

DECISION = {"action": "dismiss", "reason": "Official partner page"}


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---- login -----------------------------------------------------------------


def test_login_returns_a_signed_token_with_role(client):
    res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst123"})
    assert res.status_code == 200
    body = LoginResponse.model_validate(res.json())
    assert body.token_type == "bearer"
    assert body.user == UserInfo(username="analyst", role="analyst")
    claims = auth.decode_token(body.access_token)
    assert claims["sub"] == "analyst" and claims["role"] == "analyst"
    assert claims["exp"] > claims["iat"]


def test_wrong_password_and_unknown_user_get_the_same_401(client):
    wrong = client.post("/api/auth/login", json={"username": "admin", "password": "analyst123"})
    unknown = client.post("/api/auth/login", json={"username": "eve", "password": "admin123"})
    for res in (wrong, unknown):
        assert res.status_code == 401
        assert res.json()["detail"] == "Wrong username or password"
        assert res.headers["WWW-Authenticate"] == "Bearer"


def test_me_returns_the_token_holder(client, admin_headers):
    res = client.get("/api/auth/me", headers=admin_headers)
    assert res.status_code == 200
    assert res.json() == {"username": "admin", "role": "admin"}
    no_token = client.get("/api/auth/me")
    assert no_token.status_code == 401
    assert no_token.headers["WWW-Authenticate"] == "Bearer"


def test_mock_and_forged_tokens_are_rejected(client):
    forged = jwt.encode(
        {
            "sub": "admin",
            "role": "admin",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "some-other-secret-that-is-long-enough-0123",
        algorithm="HS256",
    )
    for token in ("mock-admin", forged):
        assert client.get("/api/auth/me", headers=_bearer(token)).status_code == 401


def test_expired_token_gets_401(client):
    token = auth.create_token("analyst", "analyst", expires_in=timedelta(minutes=-5))
    res = client.post("/api/cases/c-0002/decision", json=DECISION, headers=_bearer(token))
    assert res.status_code == 401
    assert res.json()["detail"] == "Session expired, log in again"


# ---- decisions ---------------------------------------------------------------


def test_decision_needs_login(client):
    res = client.post("/api/cases/c-0002/decision", json=DECISION)
    assert res.status_code == 401
    assert res.headers["WWW-Authenticate"] == "Bearer"
    assert client.get("/api/cases/c-0002").json()["status"] == "new"


def test_decision_by_analyst_is_logged_with_who_when_why(client, analyst_headers, admin_headers):
    before = datetime.now(timezone.utc)
    res = client.post("/api/cases/c-0002/decision", json=DECISION, headers=analyst_headers)
    assert res.status_code == 200
    case = Case.model_validate(res.json())
    assert case.status == "dismissed"
    last = case.decisions[-1]
    assert (last.by, last.action, last.reason) == ("analyst", "dismiss", "Official partner page")
    assert last.at >= before - timedelta(seconds=1)

    log = client.get("/api/decisions", headers=admin_headers)
    assert log.status_code == 200
    entries = [DecisionLogEntry.model_validate(e) for e in log.json()]
    newest = entries[0]
    assert (newest.case_id, newest.by, newest.action) == ("c-0002", "analyst", "dismiss")
    assert newest.domain == case.domain
    assert [e.at for e in entries] == sorted((e.at for e in entries), reverse=True)
    assert len(entries) >= 3  # 2 seeded demo decisions + this one


def test_decision_log_limit(client, admin_headers):
    res = client.get("/api/decisions", params={"limit": 1}, headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1


# ---- admin only --------------------------------------------------------------


def test_admin_endpoints_are_403_for_analysts(client, analyst_headers, admin_headers):
    for path in ("/api/users", "/api/decisions"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=analyst_headers).status_code == 403
        assert client.get(path, headers=admin_headers).status_code == 200
    new_user = {"username": "sneaky", "password": "password123", "role": "admin"}
    assert client.post("/api/users", json=new_user, headers=analyst_headers).status_code == 403


def test_users_list_never_contains_hashes(client, admin_headers):
    res = client.get("/api/users", headers=admin_headers)
    users = [User.model_validate(u) for u in res.json()]
    assert {(u.username, u.role) for u in users} == {("admin", "admin"), ("analyst", "analyst")}
    assert "hash" not in res.text and "scrypt" not in res.text


def test_admin_creates_user_who_can_log_in(client, admin_headers):
    body = {"username": "Fatima", "password": "s3cure-pass", "role": "analyst"}
    res = client.post("/api/users", json=body, headers=admin_headers)
    assert res.status_code == 201
    assert User.model_validate(res.json()).username == "fatima"

    login = client.post("/api/auth/login", json={"username": "fatima", "password": "s3cure-pass"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    decided = client.post("/api/cases/c-0004/decision", json=DECISION, headers=_bearer(token))
    assert decided.json()["decisions"][-1]["by"] == "fatima"

    duplicate = client.post("/api/users", json=body, headers=admin_headers)
    assert duplicate.status_code == 409


def test_create_user_validates_password_and_role(client, admin_headers):
    short = {"username": "omar", "password": "short", "role": "analyst"}
    bad_role = {"username": "omar", "password": "long-enough-1", "role": "root"}
    for body in (short, bad_role):
        assert client.post("/api/users", json=body, headers=admin_headers).status_code == 422


def test_deleted_or_disabled_user_token_stops_working(client, admin_headers):
    from app.db import SessionLocal, UserRow

    with SessionLocal() as session:
        row = auth.get_user(session, "admin")
        row.disabled = True
        session.commit()
    assert client.get("/api/auth/me", headers=admin_headers).status_code == 401
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 401
    with SessionLocal() as session:
        assert session.get(UserRow, row.id).disabled


# ---- open reads and SCAMSHIELD_REQUIRE_LOGIN ---------------------------------


def test_reads_are_open_by_default(client):
    assert client.get("/api/cases").status_code == 200
    assert client.get("/api/radar/feed").status_code == 200
    # A stale token does not break the open dashboard.
    assert client.get("/api/cases", headers=_bearer("mock-analyst")).status_code == 200


def test_require_login_closes_analyst_reads_but_not_public_ones(
    client, analyst_headers, monkeypatch
):
    monkeypatch.setenv("SCAMSHIELD_REQUIRE_LOGIN", "1")
    for path in ("/api/cases", "/api/radar/feed", "/api/graph", "/api/cases/c-0001"):
        res = client.get(path)
        assert res.status_code == 401, path
        assert res.headers["WWW-Authenticate"] == "Bearer"
        assert client.get(path, headers=analyst_headers).status_code == 200, path
    assert client.post("/api/scan", json={"url": "new-site.test/x"}).status_code == 401
    assert client.post("/api/batch", json={"urls": ["https://www.rta.ae/"]}).status_code == 401

    assert client.post("/api/check", json={"input": "tamm-violations.test/pay"}).status_code == 200
    for path in ("/api/health", "/api/brands", "/api/metrics"):
        assert client.get(path).status_code == 200, path


# ---- building blocks ---------------------------------------------------------


def test_password_hash_is_salted_and_verifies():
    first, second = auth.hash_password("admin123"), auth.hash_password("admin123")
    assert first != second and first.startswith("scrypt$")
    assert auth.verify_password("admin123", first)
    assert not auth.verify_password("admin124", first)
    assert not auth.verify_password("admin123", "not-a-hash")


def test_secret_file_is_created_once_and_reused(tmp_path):
    path = tmp_path / ".jwt-secret"
    secret = auth._secret_from_file(path)
    assert len(secret) >= 32
    assert auth._secret_from_file(path) == secret
    assert path.read_text(encoding="utf-8") == secret


def test_seeding_is_idempotent(session):
    assert auth.seed_users(session) == 2
    assert auth.seed_users(session) == 0
    assert [u.username for u in auth.list_users(session)] == ["admin", "analyst"]
