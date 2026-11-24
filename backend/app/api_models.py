"""Request and response shapes for the HTTP API (what the UI consumes)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .contracts import Candidate, Evidence, Label, Reason, Source, Verdict

CaseStatus = Literal["new", "confirmed", "dismissed"]
CheckVerdict = Literal["FRAUD", "SUSPICIOUS", "LEGIT", "UNKNOWN"]
EdgeType = Literal["same_ip", "same_registration_day", "same_final_host"]


class Health(BaseModel):
    status: Literal["ok"]
    mode: Literal["mock", "live"]
    version: str


class Decision(BaseModel):
    action: Literal["confirm", "dismiss"]
    reason: str
    by: str
    at: datetime


class Case(BaseModel):
    id: str
    domain: str
    status: CaseStatus
    candidate: Candidate
    evidence: Evidence | None = None
    verdict: Verdict
    decisions: list[Decision] = Field(default_factory=list)


class CaseSummary(BaseModel):
    id: str
    url: str
    domain: str
    source: Source
    query: str | None
    discovered_at: datetime
    verdict: Label
    score: int
    brand_target: str | None
    status: CaseStatus

    @classmethod
    def of(cls, case: Case) -> CaseSummary:
        return cls(
            id=case.id,
            url=case.candidate.url,
            domain=case.domain,
            source=case.candidate.source,
            query=case.candidate.query,
            discovered_at=case.candidate.discovered_at,
            verdict=case.verdict.verdict,
            score=case.verdict.score,
            brand_target=case.verdict.brand_target,
            status=case.status,
        )


class CaseList(BaseModel):
    items: list[CaseSummary]
    total: int


class RadarFeed(BaseModel):
    items: list[CaseSummary]
    counts_by_source: dict[str, int]


class DecisionRequest(BaseModel):
    action: Literal["confirm", "dismiss"]
    reason: str = Field(min_length=3, max_length=500)


class ScanRequest(BaseModel):
    url: str = Field(min_length=3, max_length=2048)


class ScanResponse(BaseModel):
    case_id: str
    status: Literal["queued", "done"]
    verdict: Verdict | None = None


class BatchRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=5000)


class BatchItem(BaseModel):
    url: str
    verdict: Label | None = None
    score: int | None = None
    brand_target: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    error: str | None = None


class BatchResponse(BaseModel):
    model_version: str
    items: list[BatchItem]


class CheckRequest(BaseModel):
    input: str = Field(min_length=3, max_length=2048, description="A link or a phone number")


class CheckResponse(BaseModel):
    kind: Literal["url", "phone"]
    input: str
    verdict: CheckVerdict
    score: int | None = None
    brand_target: str | None = None
    headline_en: str
    headline_ar: str
    advice_en: list[str]
    advice_ar: list[str]
    reasons: list[Reason] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str  # case id
    domain: str
    verdict: Label
    score: int
    brand_target: str | None


class GraphEdge(BaseModel):
    source: str  # case id
    target: str  # case id
    type: EdgeType
    detail: str


class Graph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class Metrics(BaseModel):
    mode: Literal["mock", "live"]
    dataset: str
    model_version: str
    n_fraud: int
    n_legit: int
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float
    recall: float
    fpr: float
    f1: float
    evaluated_at: datetime


class Takedown(BaseModel):
    case_id: str
    domain: str
    registrar: str | None
    registrar_abuse_email: str | None
    hosting_org: str | None
    hosting_abuse_email: str | None
    ip: str | None
    subject: str
    body_en: str
    body_ar: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    username: str
    role: Literal["admin", "analyst"]


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserInfo
