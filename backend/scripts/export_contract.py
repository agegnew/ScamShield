"""Write docs/api/openapi.json and docs/api/mock/*.json from the running app.

Run from backend/:  python -m scripts.export_contract
Uses a throwaway database seeded with the demo cases, so the files are exactly
what the API returns in mock mode.
"""

import json
import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = (
    f"sqlite:///{(Path(tempfile.mkdtemp(prefix='scamshield-export-')) / 'export.db').as_posix()}"
)
os.environ["SCAMSHIELD_MODE"] = "mock"
os.environ["SCAMSHIELD_SEED_MOCK"] = "1"
# Demo accounts and a throwaway signing key, so the sample token is useless elsewhere.
os.environ["SCAMSHIELD_ADMIN_PASSWORD"] = "admin123"
os.environ["SCAMSHIELD_ANALYST_PASSWORD"] = "analyst123"
os.environ["SCAMSHIELD_JWT_SECRET"] = "export-only-secret-never-used-by-a-real-api"
os.environ["SCAMSHIELD_REQUIRE_LOGIN"] = "0"
# Samples must not depend on (or spend) a real SerpApi key.
os.environ["SERPAPI_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.config import REPO_DIR  # noqa: E402
from app.main import app  # noqa: E402

OUT = REPO_DIR / "docs" / "api"
MOCK = OUT / "mock"

GETS = {
    "health": "/api/health",
    "brands": "/api/brands",
    "radar_feed": "/api/radar/feed",
    "cases": "/api/cases",
    "case_c-0001_fraud_lookalike": "/api/cases/c-0001",
    "case_c-0003_fraud_maps": "/api/cases/c-0003",
    "case_c-0005_fraud_shortlink": "/api/cases/c-0005",
    "case_c-0006_legit": "/api/cases/c-0006",
    "takedown_c-0001": "/api/cases/c-0001/takedown",
    "graph": "/api/graph",
    "metrics": "/api/metrics",
}

POSTS = {
    "check_url_fraud": ("/api/check", {"input": "tamm-violations.test/pay"}),
    "check_phone_official": ("/api/check", {"input": "600 54 0000"}),
    "check_phone_unknown": ("/api/check", {"input": "050 123 4567"}),
    "scan": ("/api/scan", {"url": "https://new-site.test/login"}),
    "batch": (
        "/api/batch",
        {"urls": ["https://tamm-fines-pay.test/pay?ref=AD-55120", "https://www.rta.ae/"]},
    ),
    "login": ("/api/auth/login", {"username": "analyst", "password": "analyst123"}),
}

# After starting a radar run for TAMM (search and Maps show as skipped: no key in samples).
RADAR_GETS = {
    "radar_status": "/api/radar/status",
    "radar_runs": "/api/radar/runs",
}

# Sent with an admin token.
ADMIN_GETS = {
    "auth_me": "/api/auth/me",
    "users": "/api/users",
    "decisions": "/api/decisions",
}


def write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    MOCK.mkdir(parents=True, exist_ok=True)
    with TestClient(app) as client:
        write(OUT / "openapi.json", app.openapi())
        for name, path in GETS.items():
            res = client.get(path)
            res.raise_for_status()
            write(MOCK / f"{name}.json", res.json())
        for name, (path, body) in POSTS.items():
            res = client.post(path, json=body)
            res.raise_for_status()
            write(MOCK / f"{name}.json", res.json())
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        for name, path in ADMIN_GETS.items():
            res = client.get(path, headers=headers)
            res.raise_for_status()
            write(MOCK / f"{name}.json", res.json())
        # Radar run: what the button gets back, then the status the page polls while it runs.
        res = client.post("/api/radar/run", json={"brands": ["tamm"]}, headers=headers)
        res.raise_for_status()
        write(MOCK / "radar_run.json", res.json())
        for name, path in RADAR_GETS.items():
            res = client.get(path)
            res.raise_for_status()
            write(MOCK / f"{name}.json", res.json())
    total = len(GETS) + len(POSTS) + len(ADMIN_GETS) + 1 + len(RADAR_GETS)
    print(f"Wrote {total} mock files and openapi.json to {OUT}")


if __name__ == "__main__":
    main()
