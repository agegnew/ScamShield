"""Login and roles.

Passwords are salted scrypt hashes (standard library), stored as one string:
'scrypt$<n>$<r>$<p>$<salt>$<hash>'. Tokens are JWTs (HS256) with the claims
sub, role, iat and exp; clients send `Authorization: Bearer <token>`.

Who may call what:
- public: health, brands, metrics, the citizen checker, login
- analyst reads (radar, cases, graph, takedown, report, scan, batch): open for
  the demo dashboard unless SCAMSHIELD_REQUIRE_LOGIN=1
- confirm / dismiss a case: any logged-in user (analyst or admin)
- user accounts and the decision audit log: admins only
"""

import base64
import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import config
from .api_models import UserInfo
from .db import UserRow, utcnow
from .deps import get_session

log = logging.getLogger(__name__)

ALGORITHM = "HS256"
DEFAULT_PASSWORDS = {"admin": "admin123", "analyst": "analyst123"}

# ---- passwords -------------------------------------------------------------

# 16 MiB of memory and ~40 ms per hash; the parameters are stored in each hash.
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    salt_b64 = base64.b64encode(salt).decode()
    digest_b64 = base64.b64encode(digest).decode()
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt_b64}${digest_b64}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(
            password.encode(),
            salt=base64.b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except ValueError:  # malformed hash (binascii.Error is a ValueError too)
        return False
    return hmac.compare_digest(actual, expected)


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    """Checked against for unknown users, so they take as long as wrong passwords."""
    return hash_password(secrets.token_hex(16))


@lru_cache(maxsize=8)
def _seed_hash(password: str) -> str:
    # Seeding runs on every start into an empty table (and once per test);
    # hash each seed password once per process.
    return hash_password(password)


# ---- tokens ----------------------------------------------------------------

_secret: str | None = None


def _secret_from_file(path: Path) -> str:
    """Read the saved secret, or create it once (first start wins a race)."""
    try:
        saved = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        saved = ""
    if saved:
        return saved
    value = secrets.token_urlsafe(48)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(value)
    except FileExistsError:
        return path.read_text(encoding="utf-8").strip() or value
    except OSError:
        log.warning("cannot save the JWT secret to %s; tokens end when the API stops", path)
    return value


def jwt_secret() -> str:
    global _secret
    if _secret is None:
        _secret = config.JWT_SECRET or _secret_from_file(config.JWT_SECRET_FILE)
    return _secret


def create_token(username: str, role: str, expires_in: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    if expires_in is None:
        expires_in = timedelta(hours=config.TOKEN_HOURS)
    claims = {"sub": username, "role": role, "iat": now, "exp": now + expires_in}
    return jwt.encode(claims, jwt_secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Raises jwt.ExpiredSignatureError or another jwt.InvalidTokenError."""
    return jwt.decode(
        token,
        jwt_secret(),
        algorithms=[ALGORITHM],
        options={"require": ["sub", "role", "iat", "exp"]},
    )


# ---- accounts --------------------------------------------------------------


class UserExists(Exception):
    pass


def normalize_username(username: str) -> str:
    return username.strip().lower()


def get_user(session: Session, username: str) -> UserRow | None:
    return session.scalar(select(UserRow).where(UserRow.username == normalize_username(username)))


def authenticate(session: Session, username: str, password: str) -> UserRow | None:
    row = get_user(session, username)
    if row is None:
        verify_password(password, _dummy_hash())
        return None
    if not verify_password(password, row.password_hash) or row.disabled:
        return None
    return row


def list_users(session: Session) -> list[UserRow]:
    return list(session.scalars(select(UserRow).order_by(UserRow.id)))


def create_user(session: Session, username: str, password: str, role: str) -> UserRow:
    row = UserRow(
        username=normalize_username(username),
        password_hash=hash_password(password),
        role=role,
        disabled=False,
        created_at=utcnow(),
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise UserExists(row.username) from exc
    return row


def seed_users(session: Session) -> int:
    """Create the admin and analyst accounts if there are no users yet."""
    if session.scalar(select(func.count()).select_from(UserRow)):
        return 0
    accounts = {
        "admin": ("admin", config.ADMIN_PASSWORD),
        "analyst": ("analyst", config.ANALYST_PASSWORD),
    }
    session.add_all(
        UserRow(username=name, password_hash=_seed_hash(password), role=role, disabled=False)
        for name, (role, password) in accounts.items()
    )
    try:
        session.commit()
    except IntegrityError:  # another process seeded at the same moment
        session.rollback()
        return 0
    if config.MODE == "live":
        for name, (_role, password) in accounts.items():
            if password == DEFAULT_PASSWORDS[name]:
                log.warning("account %r uses the demo password; set SCAMSHIELD_*_PASSWORD", name)
    return len(accounts)


# ---- FastAPI dependencies --------------------------------------------------

bearer = HTTPBearer(
    auto_error=False,
    description="Log in with POST /api/auth/login and paste the access_token here.",
)


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> UserInfo:
    """Any logged-in user. 401 without a token or with a bad or expired one."""
    if credentials is None:
        raise unauthorized("Log in first")
    try:
        claims = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise unauthorized("Session expired, log in again") from None
    except jwt.InvalidTokenError:
        raise unauthorized("Invalid token, log in again") from None
    row = get_user(session, str(claims["sub"]))
    if row is None or row.disabled:
        raise unauthorized("Account not found or disabled")
    return UserInfo(username=row.username, role=row.role)


def require_admin(user: UserInfo = Depends(require_user)) -> UserInfo:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return user


def login_required() -> bool:
    """SCAMSHIELD_REQUIRE_LOGIN=1 closes the analyst reads (checked per request)."""
    return os.getenv("SCAMSHIELD_REQUIRE_LOGIN", "0").strip().lower() in ("1", "true", "yes")


def analyst_access(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> UserInfo | None:
    """Analyst reads: open by default so the demo dashboard works without login."""
    if not login_required():
        return None
    return require_user(credentials, session)
