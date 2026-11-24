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
    "login": ("/api/auth/login", {"username": "analyst", "password": "any"}),
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
    print(f"Wrote {len(GETS) + len(POSTS)} mock files and openapi.json to {OUT}")


if __name__ == "__main__":
    main()
