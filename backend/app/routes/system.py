from fastapi import APIRouter, HTTPException

from ..api_models import Health, LoginRequest, LoginResponse, Metrics
from ..auth import mock_login
from ..brands import load_registry
from ..config import BACKEND_DIR, MODE, VERSION
from ..contracts import Brand
from ..mock.data import MOCK_METRICS

router = APIRouter(prefix="/api", tags=["system"])

EVAL_RESULTS = BACKEND_DIR / "eval" / "latest.json"


@router.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", mode=MODE, version=VERSION)


@router.get("/brands", response_model=list[Brand])
def brands() -> list[Brand]:
    return load_registry().brands


@router.get("/metrics", response_model=Metrics)
def metrics() -> Metrics:
    """Accuracy on the held-out test set (scripts/evaluate.py --save).
    Falls back to clearly-labelled sample numbers if no evaluation has been saved."""
    if EVAL_RESULTS.exists():
        return Metrics.model_validate_json(EVAL_RESULTS.read_text(encoding="utf-8"))
    return MOCK_METRICS


@router.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    user = mock_login(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Wrong username or password")
    return LoginResponse(access_token=f"mock-{user.username}", user=user)
