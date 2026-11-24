from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import ARTIFACTS_DIR, CORS_ORIGINS, MODE, VERSION
from .routes import cases, citizen, scan, system

app = FastAPI(
    title="ScamShield API",
    version=VERSION,
    description=(
        "Finds and scores UAE-brand scam sites. "
        "Every response carries the header X-ScamShield-Mode: mock | live."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-ScamShield-Mode"],
)


@app.middleware("http")
async def mode_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-ScamShield-Mode"] = MODE
    return response


for module in (system, cases, scan, citizen):
    app.include_router(module.router)

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=ARTIFACTS_DIR), name="artifacts")
