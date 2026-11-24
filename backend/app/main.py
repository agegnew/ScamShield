from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .auth import seed_users
from .config import ARTIFACTS_DIR, CORS_ORIGINS, MODE, SEED_MOCK, VERSION
from .db import SessionLocal, init_db
from .mock.data import build_cases
from .repo import CaseRepo
from .routes import cases, citizen, scan, system, users


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    with SessionLocal() as session:
        seed_users(session)  # admin + analyst when there are no accounts yet
        if SEED_MOCK:
            repo = CaseRepo(session)
            if repo.is_empty():
                repo.seed(build_cases())
    yield


app = FastAPI(
    title="ScamShield API",
    version=VERSION,
    lifespan=lifespan,
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


for module in (system, users, cases, scan, citizen):
    app.include_router(module.router)

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=ARTIFACTS_DIR), name="artifacts")
