import os
import tempfile
from pathlib import Path

# Point the app at a throwaway SQLite file before it is imported.
_DB_FILE = Path(tempfile.mkdtemp(prefix="scamshield-test-")) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_FILE.as_posix()}"
os.environ["SCAMSHIELD_MODE"] = "mock"
os.environ["SCAMSHIELD_SEED_MOCK"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    """API with a fresh database holding the 8 demo cases."""
    Base.metadata.drop_all(engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def session():
    """Empty database session."""
    Base.metadata.drop_all(engine)
    init_db()
    with SessionLocal() as db_session:
        yield db_session
