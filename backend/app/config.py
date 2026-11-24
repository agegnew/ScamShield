import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

# Local runs read the repo's .env (docker-compose passes it in as env_file).
load_dotenv(REPO_DIR / ".env")

VERSION = "0.2.0"
MODE = os.getenv("SCAMSHIELD_MODE", "mock")
BRANDS_PATH = Path(os.getenv("SCAMSHIELD_BRANDS", str(REPO_DIR / "data" / "brands.json")))
THEMES_PATH = Path(os.getenv("SCAMSHIELD_THEMES", str(REPO_DIR / "data" / "scam_themes.json")))
MODELS_DIR = Path(os.getenv("SCAMSHIELD_MODELS", str(BACKEND_DIR / "models")))
FEEDS_DIR = Path(os.getenv("SCAMSHIELD_FEEDS", str(REPO_DIR / "data" / "datasets" / "raw")))
# Turn off to measure the engine without phishing feeds (honest evaluation).
USE_FEEDS = os.getenv("SCAMSHIELD_USE_FEEDS", "1") == "1"
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
# Radar caches (crt.sh answers, daily new-domain lists, saved SerpApi answers).
CACHE_DIR = Path(os.getenv("SCAMSHIELD_CACHE", str(REPO_DIR / "data" / "cache")))
JOB_MAX_ATTEMPTS = int(os.getenv("SCAMSHIELD_JOB_MAX_ATTEMPTS", "3"))

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# Login (JWT). Without SCAMSHIELD_JWT_SECRET a random secret is made once and
# kept in backend/.jwt-secret (gitignored), so tokens survive API reloads.
JWT_SECRET = os.getenv("SCAMSHIELD_JWT_SECRET", "")
JWT_SECRET_FILE = Path(os.getenv("SCAMSHIELD_JWT_SECRET_FILE", str(BACKEND_DIR / ".jwt-secret")))
TOKEN_HOURS = float(os.getenv("SCAMSHIELD_TOKEN_HOURS", "12"))
# Accounts created when the users table is empty (defaults are for the local demo).
ADMIN_PASSWORD = os.getenv("SCAMSHIELD_ADMIN_PASSWORD") or "admin123"
ANALYST_PASSWORD = os.getenv("SCAMSHIELD_ANALYST_PASSWORD") or "analyst123"
# SCAMSHIELD_REQUIRE_LOGIN=1 also closes the analyst reads; auth.py reads it per request.
