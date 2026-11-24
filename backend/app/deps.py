from collections.abc import Iterator

from sqlalchemy.orm import Session

from .db import SessionLocal
from .repo import CaseRepo


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def get_repo() -> Iterator[CaseRepo]:
    with SessionLocal() as session:
        yield CaseRepo(session)
