from fastapi import APIRouter, HTTPException

from ..api_models import Health, LoginRequest, LoginResponse, Metrics
from ..auth import mock_login
from ..brands import load_registry
from ..config import MODE, VERSION
from ..contracts import Brand
from ..mock.data import MOCK_METRICS

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", mode=MODE, version=VERSION)


@router.get("/brands", response_model=list[Brand])
def brands() -> list[Brand]:
    return load_registry().brands


@router.get("/metrics", response_model=Metrics)
def metrics() -> Metrics:
    """Accuracy on the held-out test set. In mock mode the numbers are layout samples."""
    return MOCK_METRICS


@router.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    user = mock_login(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Wrong username or password")
    return LoginResponse(access_token=f"mock-{user.username}", user=user)
