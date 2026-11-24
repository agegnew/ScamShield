import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

VERSION = "0.1.0"
MODE = os.getenv("SCAMSHIELD_MODE", "mock")
BRANDS_PATH = Path(os.getenv("SCAMSHIELD_BRANDS", str(REPO_DIR / "data" / "brands.json")))
ARTIFACTS_DIR = Path(os.getenv("SCAMSHIELD_ARTIFACTS", str(BACKEND_DIR / "artifacts")))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "SCAMSHIELD_CORS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]
