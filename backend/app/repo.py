"""Case storage. Routes and the worker read and write cases only through this."""

import secrets
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from . import engine as detection
from .api_models import Case, CaseSummary, Decision
from .brands import normalize_uae_phone
from .contracts import Candidate, Evidence, Source, Verdict
from .db import CaseRow, DecisionRow, utcnow
from .urls import hostname

RADAR_SOURCES = (
    Source.LOOKALIKE,
    Source.CT,
    Source.NRD,
    Source.SEARCH,
    Source.SEARCH_AD,
    Source.MAPS,
)


def _utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def new_case_id() -> str:
    return f"c-{secrets.token_hex(4)}"


class CaseRepo:
    def __init__(self, session: Session) -> None:
        self.s = session

    # ---- reading -------------------------------------------------------

    @staticmethod
    def _query():
        return select(CaseRow).options(selectinload(CaseRow.decisions))

    @staticmethod
    def _to_case(row: CaseRow) -> Case:
        return Case(
            id=row.id,
            domain=row.domain,
            status=row.status,
            candidate=Candidate.model_validate(row.candidate_json),
            evidence=Evidence.model_validate(row.evidence_json) if row.evidence_json else None,
            verdict=Verdict.model_validate(row.verdict_json),
            decisions=[
                Decision(action=d.action, reason=d.reason, by=d.decided_by, at=_utc(d.at))
                for d in row.decisions
            ],
        )

    def get(self, case_id: str) -> Case | None:
        row = self.s.scalars(self._query().where(CaseRow.id == case_id)).first()
        return self._to_case(row) if row else None

    def all(self, limit: int | None = None) -> list[Case]:
        stmt = self._query().order_by(CaseRow.discovered_at.desc())
        if limit:
            stmt = stmt.limit(limit)
        return [self._to_case(r) for r in self.s.scalars(stmt)]

    def find_by_url(self, url: str) -> Case | None:
        """Exact URL first, then any case on the same host or redirecting to it."""
        row = self.s.scalars(self._query().where(CaseRow.url == url)).first()
        if row is None:
            host = hostname(url)
            row = self.s.scalars(
                self._query()
                .where(or_(CaseRow.domain == host, CaseRow.final_host == host))
                .order_by(CaseRow.discovered_at.desc())
            ).first()
        return self._to_case(row) if row else None

    def find_by_phone(self, digits: str) -> Case | None:
        row = self.s.scalars(self._query().where(CaseRow.phone_digits == digits)).first()
        return self._to_case(row) if row else None

    def search(
        self,
        verdict: str | None = None,
        source: str | None = None,
        brand: str | None = None,
        status: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Case], int]:
        conds = []
        if verdict:
            conds.append(CaseRow.verdict == verdict)
        if source:
            conds.append(CaseRow.source == source)
        if brand:
            conds.append(CaseRow.brand_target == brand)
        if status:
            conds.append(CaseRow.status == status)
        if q:
            conds.append(CaseRow.url.icontains(q, autoescape=True))
        total = self.s.scalar(select(func.count()).select_from(CaseRow).where(*conds)) or 0
        rows = self.s.scalars(
            self._query()
            .where(*conds)
            .order_by(CaseRow.discovered_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [self._to_case(r) for r in rows], total

    def radar(self, limit: int = 50) -> list[Case]:
        rows = self.s.scalars(
            self._query()
            .where(CaseRow.source.in_([s.value for s in RADAR_SOURCES]))
            .order_by(CaseRow.discovered_at.desc())
            .limit(limit)
        )
        return [self._to_case(r) for r in rows]

    def counts_by_source(self) -> dict[str, int]:
        found = dict(
            self.s.execute(select(CaseRow.source, func.count()).group_by(CaseRow.source)).all()
        )
        return {s.value: found.get(s.value, 0) for s in Source}

    def is_empty(self) -> bool:
        return not self.s.scalar(select(func.count()).select_from(CaseRow))

    @staticmethod
    def summaries(cases: list[Case]) -> list[CaseSummary]:
        return [CaseSummary.of(c) for c in cases]

    # ---- writing -------------------------------------------------------

    @staticmethod
    def _apply(row: CaseRow, evidence: Evidence | None, verdict: Verdict) -> None:
        row.evidence_json = evidence.model_dump(mode="json") if evidence else None
        row.final_host = hostname(evidence.final_url) if evidence and evidence.final_url else None
        row.verdict_json = verdict.model_dump(mode="json")
        row.verdict = verdict.verdict.value
        row.score = verdict.score
        row.brand_target = verdict.brand_target

    def add(
        self,
        candidate: Candidate,
        verdict: Verdict,
        evidence: Evidence | None = None,
        status: str = "new",
        decisions: list[Decision] | None = None,
        case_id: str | None = None,
    ) -> Case:
        phone = candidate.extra.phone
        row = CaseRow(
            id=case_id or new_case_id(),
            url=candidate.url,
            domain=hostname(candidate.url),
            source=candidate.source.value,
            status=status,
            discovered_at=_utc(candidate.discovered_at),
            phone_digits=normalize_uae_phone(phone) if phone else None,
            candidate_json=candidate.model_dump(mode="json"),
        )
        self._apply(row, evidence, verdict)
        for d in decisions or []:
            row.decisions.append(
                DecisionRow(action=d.action, reason=d.reason, decided_by=d.by, at=_utc(d.at))
            )
        self.s.add(row)
        self.s.commit()
        return self.get(row.id)

    def upsert_candidate(self, candidate: Candidate) -> tuple[Case, bool]:
        """Create a case for a new URL (scored from the URL alone). Returns (case, created)."""
        existing = self.s.scalars(self._query().where(CaseRow.url == candidate.url)).first()
        if existing:
            return self._to_case(existing), False
        try:
            return self.add(candidate, detection.score(candidate.url, candidate=candidate)), True
        except IntegrityError:  # another worker inserted the same URL first
            self.s.rollback()
            row = self.s.scalars(self._query().where(CaseRow.url == candidate.url)).one()
            return self._to_case(row), False

    def save_analysis(self, case_id: str, evidence: Evidence, verdict: Verdict) -> Case | None:
        row = self.s.get(CaseRow, case_id)
        if row is None:
            return None
        self._apply(row, evidence, verdict)
        self.s.commit()
        return self.get(case_id)

    def decide(self, case_id: str, action: str, reason: str, by: str) -> Case | None:
        row = self.s.get(CaseRow, case_id)
        if row is None:
            return None
        row.decisions.append(DecisionRow(action=action, reason=reason, decided_by=by, at=utcnow()))
        row.status = "confirmed" if action == "confirm" else "dismissed"
        self.s.commit()
        return self.get(case_id)

    def seed(self, cases: list[Case]) -> None:
        for c in cases:
            self.add(c.candidate, c.verdict, c.evidence, c.status, c.decisions, case_id=c.id)
