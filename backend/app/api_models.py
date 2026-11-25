"""Request and response shapes for the HTTP API (what the UI consumes)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .brands import brand_by_id
from .contracts import BrandCategory, Candidate, Evidence, Label, Reason, Source, Verdict

CaseStatus = Literal["new", "confirmed", "dismissed"]
CheckVerdict = Literal["FRAUD", "SUSPICIOUS", "LEGIT", "UNKNOWN"]
EdgeType = Literal[
    "same_ip",
    "same_registration_day",
    "same_final_host",
    "same_favicon",
    "same_template",
    "same_tracker",
    "same_contact",
]


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
    brand_category: BrandCategory | None = Field(
        default=None, description="Sector of brand_target (bank, police, shopping, ...); null without a brand"
    )
    status: CaseStatus
    source_details: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "How the radar found it (docs/radar-ui.md). lookalike: variant; ct: issuer, issued_at; "
            "nrd: registered_on; search/search_ad: query, position, title, lang, replayed; "
            "maps: listing_name, phone, helpline_mismatch, rating, reviews, replayed"
        ),
    )

    @classmethod
    def of(cls, case: Case) -> CaseSummary:
        brand = brand_by_id(case.verdict.brand_target)
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
            brand_category=brand.category if brand else None,
            status=case.status,
            source_details=source_details(case),
        )


# Older finds stored "typo"/"combo"; the Radar page knows the dnstwist names.
_OLD_VARIANTS = {"combo": "dictionary"}


def source_details(case: Case) -> dict[str, Any]:
    """The few radar fields the Radar page shows per source, under stable names."""
    c, d = case.candidate, case.candidate.extra.details
    s = c.source
    out: dict[str, Any]
    if s == Source.LOOKALIKE:
        variant = d.get("variant")
        out = {"variant": _OLD_VARIANTS.get(variant, variant)}
    elif s == Source.CT:
        out = {"issuer": d.get("issuer"), "issued_at": d.get("cert_issued") or d.get("issued_at")}
    elif s == Source.NRD:
        out = {"registered_on": d.get("registered_on")}
    elif s in (Source.SEARCH, Source.SEARCH_AD):
        out = {"query": c.query, "position": d.get("position"), "title": d.get("title"),
               "lang": d.get("lang"), "replayed": bool(d.get("replayed"))}
    elif s == Source.MAPS:
        flags = d.get("flags") or []
        mismatch = "helpline_not_official" in flags or any(
            r.code == "helpline_mismatch" for r in case.verdict.reasons
        )
        out = {"listing_name": c.extra.listing_name, "phone": c.extra.phone, "helpline_mismatch": mismatch,
               "rating": d.get("rating"), "reviews": d.get("reviews"), "replayed": bool(d.get("replayed"))}
    else:
        out = {}
    return {k: v for k, v in out.items() if v is not None}


class CaseList(BaseModel):
    items: list[CaseSummary]
    total: int


class RadarFeed(BaseModel):
    items: list[CaseSummary]
    counts_by_source: dict[str, int] = Field(description="Every case per source, ignoring the filters")
    counts_by_category: dict[str, int] = Field(
        default_factory=dict,
        description="Radar finds per brand sector, ignoring the filters; brand-less finds under 'none'",
    )


# ---- radar runs (docs/radar-ui.md) ---------------------------------------------

RadarSourceName = Literal["lookalikes", "ct", "nrd", "search", "maps"]


class RadarRunSource(BaseModel):
    name: RadarSourceName
    status: Literal["waiting", "running", "done", "skipped", "failed"]
    checked: int | None = Field(default=None, description="Names / tokens / queries checked so far")
    total: int | None = Field(default=None, description="null while unknown")
    found: int | None = Field(default=None, description="URLs this source returned")
    new: int | None = Field(default=None, description="Of those, URLs not seen before")
    note: str | None = Field(default=None, description="e.g. needs_key, or the error type when failed")


class RadarRunPages(BaseModel):
    checked: int = Field(description="Page checks finished (or given up on)")
    total: int = Field(description="New finds queued for a page check, highest URL risk first")


class RadarRun(BaseModel):
    id: str
    trigger: Literal["manual", "schedule"]
    started_by: str | None
    status: Literal["running", "done", "failed"]
    started_at: datetime
    finished_at: datetime | None
    brands: list[str] | None = Field(default=None, description="Brands this run looked for; null = all")
    sources: list[RadarRunSource]
    pages: RadarRunPages
    verdicts: dict[str, int] = Field(
        default_factory=dict, description="Final verdicts of this run's new finds so far (FRAUD, SUSPICIOUS, LEGIT)"
    )
    error: str | None = None


class RadarSchedule(BaseModel):
    enabled: bool
    time: str = Field(description="Daily run time, HH:MM in `timezone`")
    timezone: str
    next_run_at: datetime | None


class RadarSourceInfo(BaseModel):
    name: RadarSourceName
    enabled: bool = Field(description="False when the source needs a key that isn't set")
    needs_key: str | None = None
    last_run_at: datetime | None = None
    last_new: int = 0


class RadarStatus(BaseModel):
    running: bool
    run: RadarRun | None = Field(description="The current run while running, else the last one")
    schedule: RadarSchedule
    sources: list[RadarSourceInfo]
    searches_left: int | None = Field(
        default=None, description="SerpApi searches left this month (null without a key)"
    )


class RadarRunRequest(BaseModel):
    sources: list[RadarSourceName] | None = Field(default=None, description="Omit for all enabled sources")
    brands: list[str] | None = Field(default=None, description="Brand ids; omit for all brands")


class RadarRunResponse(BaseModel):
    run: RadarRun


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


class BlocklistEntry(BaseModel):
    domain: str
    brand_target: str | None = None
    score: int
    confirmed: bool  # an analyst confirmed it (otherwise the engine rated it FRAUD)
    case_id: str


class Blocklist(BaseModel):
    generated_at: datetime
    count: int
    domains: list[BlocklistEntry]


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
    by_source: dict[str, dict[str, int]] | None = None


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
    recipients: list[str] = Field(
        default_factory=list, description="Registrar and host abuse emails, deduplicated"
    )
    mailto: str | None = Field(
        default=None,
        description="mailto: link with the recipients, subject and English body; None without recipients",
    )


class RelatedDomain(BaseModel):
    """Another case that shares infrastructure with this one (an edge of GET /api/graph)."""

    case_id: str
    domain: str
    verdict: Label
    score: int
    type: EdgeType
    detail: str


class EvidenceExport(BaseModel):
    """Downloadable evidence bundle for one case (GET /api/cases/{id}/export.json)."""

    generated_at: datetime
    scamshield_version: str
    model_version: str = Field(description="Detection engine that produced this export")
    case: Case
    takedown: Takedown
    related: list[RelatedDomain]


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


class User(BaseModel):
    """An account as admins see it (the password hash is never returned)."""

    username: str
    role: Literal["admin", "analyst"]
    disabled: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=256)
    role: Literal["admin", "analyst"]


class DecisionLogEntry(BaseModel):
    """One confirm / dismiss in the audit log: who, when, why."""

    case_id: str
    domain: str
    action: Literal["confirm", "dismiss"]
    reason: str
    by: str
    at: datetime
