import os
import tempfile
from pathlib import Path

# Point the app at a throwaway SQLite file before it is imported.
_DB_FILE = Path(tempfile.mkdtemp(prefix="scamshield-test-")) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_FILE.as_posix()}"
os.environ["SCAMSHIELD_MODE"] = "mock"
os.environ["SCAMSHIELD_SEED_MOCK"] = "1"
# Fixed login settings, whatever the local .env says.
os.environ["SCAMSHIELD_JWT_SECRET"] = "test-secret-not-for-production-0123456789"
os.environ["SCAMSHIELD_ADMIN_PASSWORD"] = "admin123"
os.environ["SCAMSHIELD_ANALYST_PASSWORD"] = "analyst123"
os.environ["SCAMSHIELD_REQUIRE_LOGIN"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402

PASSWORDS = {"admin": "admin123", "analyst": "analyst123"}


@pytest.fixture
def client():
    """API with a fresh database holding the 8 demo cases and the 2 seeded accounts."""
    Base.metadata.drop_all(engine)
    with TestClient(app) as test_client:
        yield test_client


def _login(client, username: str) -> dict[str, str]:
    res = client.post(
        "/api/auth/login", json={"username": username, "password": PASSWORDS[username]}
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def admin_headers(client) -> dict[str, str]:
    return _login(client, "admin")


@pytest.fixture
def analyst_headers(client) -> dict[str, str]:
    return _login(client, "analyst")


@pytest.fixture
def session():
    """Empty database session."""
    Base.metadata.drop_all(engine)
    init_db()
    with SessionLocal() as db_session:
        yield db_session
