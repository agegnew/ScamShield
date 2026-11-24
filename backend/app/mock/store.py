"""In-memory case store used in mock mode. The database version (Gate 1)
keeps the same method names so routes don't change."""

from collections import Counter
from datetime import datetime

from ..api_models import Case, CaseSummary, Decision
from ..brands import normalize_uae_phone
from ..contracts import Candidate, Source
from ..urls import hostname
from .data import UAE, build_cases, placeholder_verdict


class MockStore:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.cases: dict[str, Case] = {c.id: c for c in build_cases()}
        self._next_id = len(self.cases) + 1

    def all(self) -> list[Case]:
        return sorted(self.cases.values(), key=lambda c: c.candidate.discovered_at, reverse=True)

    def get(self, case_id: str) -> Case | None:
        return self.cases.get(case_id)

    def find_by_url(self, url: str) -> Case | None:
        host = hostname(url)
        for case in self.cases.values():
            if case.candidate.url == url:
                return case
        for case in self.cases.values():
            final = case.evidence.final_url if case.evidence else None
            if case.domain == host or (final and hostname(final) == host):
                return case
        return None

    def find_by_phone(self, digits: str) -> Case | None:
        for case in self.cases.values():
            phone = case.candidate.extra.phone
            if phone and normalize_uae_phone(phone) == digits:
                return case
        return None

    def search(
        self,
        verdict: str | None = None,
        source: str | None = None,
        brand: str | None = None,
        status: str | None = None,
        q: str | None = None,
    ) -> list[Case]:
        result = []
        for case in self.all():
            if verdict and case.verdict.verdict.value != verdict:
                continue
            if source and case.candidate.source.value != source:
                continue
            if brand and case.verdict.brand_target != brand:
                continue
            if status and case.status != status:
                continue
            if q and q.lower() not in case.candidate.url.lower():
                continue
            result.append(case)
        return result

    def counts_by_source(self) -> dict[str, int]:
        counts = Counter(c.candidate.source.value for c in self.cases.values())
        return {s.value: counts.get(s.value, 0) for s in Source}

    def add_scan(self, url: str, source: Source = Source.MANUAL) -> Case:
        existing = self.find_by_url(url)
        if existing and existing.candidate.url == url:
            return existing
        case_id = f"c-{self._next_id:04d}"
        self._next_id += 1
        now = datetime.now(UAE)
        case = Case(
            id=case_id,
            domain=hostname(url),
            status="new",
            candidate=Candidate(url=url, source=source, discovered_at=now),
            evidence=None,
            verdict=placeholder_verdict(url),
        )
        self.cases[case_id] = case
        return case

    def decide(self, case_id: str, action: str, reason: str, by: str) -> Case | None:
        case = self.cases.get(case_id)
        if case is None:
            return None
        case.decisions.append(Decision(action=action, reason=reason, by=by, at=datetime.now(UAE)))
        case.status = "confirmed" if action == "confirm" else "dismissed"
        return case

    def summaries(self, cases: list[Case]) -> list[CaseSummary]:
        return [CaseSummary.of(c) for c in cases]


store = MockStore()


def get_store() -> MockStore:
    return store
