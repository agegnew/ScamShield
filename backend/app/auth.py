"""Mock auth: real JWT login with roles replaces this in task 5 (14:00).

Mock rules: users 'admin' and 'analyst' log in with any non-empty password
and get the token 'mock-<username>'. Routes accept requests without a token.
"""

from fastapi import Header

from .api_models import UserInfo

MOCK_USERS = {"admin": "admin", "analyst": "analyst"}


def mock_login(username: str, password: str) -> UserInfo | None:
    role = MOCK_USERS.get(username)
    if role is None or not password:
        return None
    return UserInfo(username=username, role=role)


def current_user(authorization: str | None = Header(default=None)) -> UserInfo:
    if authorization and authorization.startswith("Bearer mock-"):
        username = authorization.removeprefix("Bearer mock-")
        role = MOCK_USERS.get(username)
        if role:
            return UserInfo(username=username, role=role)
    return UserInfo(username="analyst", role="analyst")
