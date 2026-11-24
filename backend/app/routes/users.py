"""Login, the current user, user accounts and the decision audit log."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api_models import DecisionLogEntry, LoginRequest, LoginResponse, User, UserCreate, UserInfo
from ..auth import (
    UserExists,
    authenticate,
    create_token,
    create_user,
    list_users,
    require_admin,
    require_user,
    unauthorized,
)
from ..db import CaseRow, DecisionRow, UserRow
from ..deps import get_session

router = APIRouter(prefix="/api")


def _utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _user(row: UserRow) -> User:
    return User(
        username=row.username,
        role=row.role,
        disabled=row.disabled,
        created_at=_utc(row.created_at),
    )


@router.post("/auth/login", response_model=LoginResponse, tags=["auth"])
def login(body: LoginRequest, session: Session = Depends(get_session)) -> LoginResponse:
    row = authenticate(session, body.username, body.password)
    if row is None:
        raise unauthorized("Wrong username or password")
    return LoginResponse(
        access_token=create_token(row.username, row.role),
        user=UserInfo(username=row.username, role=row.role),
    )


@router.get("/auth/me", response_model=UserInfo, tags=["auth"])
def me(user: UserInfo = Depends(require_user)) -> UserInfo:
    return user


@router.get("/users", response_model=list[User], tags=["admin"])
def users(
    _admin: UserInfo = Depends(require_admin), session: Session = Depends(get_session)
) -> list[User]:
    return [_user(row) for row in list_users(session)]


@router.post("/users", response_model=User, status_code=201, tags=["admin"])
def add_user(
    body: UserCreate,
    _admin: UserInfo = Depends(require_admin),
    session: Session = Depends(get_session),
) -> User:
    try:
        row = create_user(session, body.username, body.password, body.role)
    except UserExists as exc:
        raise HTTPException(status_code=409, detail=f"User {exc} already exists") from None
    return _user(row)


@router.get("/decisions", response_model=list[DecisionLogEntry], tags=["admin"])
def decisions(
    limit: int = Query(100, ge=1, le=1000),
    _admin: UserInfo = Depends(require_admin),
    session: Session = Depends(get_session),
) -> list[DecisionLogEntry]:
    """Audit log: every confirm / dismiss across all cases, newest first."""
    rows = session.execute(
        select(DecisionRow, CaseRow.domain)
        .join(CaseRow, DecisionRow.case_id == CaseRow.id)
        .order_by(DecisionRow.at.desc(), DecisionRow.id.desc())
        .limit(limit)
    ).all()
    return [
        DecisionLogEntry(
            case_id=d.case_id,
            domain=domain,
            action=d.action,
            reason=d.reason,
            by=d.decided_by,
            at=_utc(d.at),
        )
        for d, domain in rows
    ]
