import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

VERSION = "0.2.0"
MODE = os.getenv("SCAMSHIELD_MODE", "mock")
BRANDS_PATH = Path(os.getenv("SCAMSHIELD_BRANDS", str(REPO_DIR / "data" / "brands.json")))
THEMES_PATH = Path(os.getenv("SCAMSHIELD_THEMES", str(REPO_DIR / "data" / "scam_themes.json")))
ARTIFACTS_DIR = Path(os.getenv("SCAMSHIELD_ARTIFACTS", str(BACKEND_DIR / "artifacts")))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "SCAMSHIELD_CORS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]

# SQLite file for local runs; docker-compose points this at Postgres.
DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'scamshield.db').as_posix()}"
)
# Load the demo cases into an empty database (on by default in mock mode).
SEED_MOCK = os.getenv("SCAMSHIELD_SEED_MOCK", "1" if MODE == "mock" else "0") == "1"

WORKER_POLL_SECONDS = float(os.getenv("SCAMSHIELD_WORKER_POLL", "2"))
JOB_MAX_ATTEMPTS = int(os.getenv("SCAMSHIELD_JOB_MAX_ATTEMPTS", "3"))

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
