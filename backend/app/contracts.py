"""Shared data formats for ScamShield.

Every lane exchanges these shapes: radar workers (Simon) produce Candidate and
Evidence, the engine produces Verdict, the API (Agegnew) serves them to the UI
(Nati), and the brand registry (Samri) is a BrandRegistry in data/brands.json.

Change a field only after telling the whole team.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Source(str, Enum):
    """Where a URL came from."""

    LOOKALIKE = "lookalike"  # generated typo/brand variant that turned out to be registered
    CT = "ct"  # new TLS certificate seen in Certificate Transparency (crt.sh)
    SEARCH = "search"  # organic Google result
    SEARCH_AD = "search_ad"  # paid Google ad
    MAPS = "maps"  # Google Maps listing website
    MANUAL = "manual"  # analyst pasted it
    CITIZEN = "citizen"  # public citizen checker
    BATCH = "batch"  # batch file / evaluation run


class Label(str, Enum):
    FRAUD = "FRAUD"
    SUSPICIOUS = "SUSPICIOUS"
    LEGIT = "LEGIT"


BrandCategory = Literal[
    "government", "police", "bank", "telecom", "transport", "utility", "delivery"
]


class Brand(BaseModel):
    id: str = Field(description="Short slug, e.g. 'tamm'")
    name_en: str
    name_ar: str
    category: BrandCategory
    official_domains: list[str] = Field(
        description="Registrable domains only, e.g. 'tamm.abudhabi'; subdomains count as official"
    )
    helplines: list[str] = Field(
        default_factory=list,
        description="As printed on the official site, e.g. '600 54 0000'",
    )
    keywords_en: list[str] = Field(default_factory=list)
    keywords_ar: list[str] = Field(default_factory=list)
    logo: str | None = Field(default=None, description="Path under data/logos/")


class BrandRegistry(BaseModel):
    version: str
    brands: list[Brand]


class ScamTheme(BaseModel):
    """A scam type that does not copy one brand (jobs, property, delivery fees...)."""

    id: str = Field(description="Short slug, e.g. 'delivery_fees'")
    name_en: str
    name_ar: str
    keywords_en: list[str] = Field(description="Lower-case words/phrases seen on scam pages")
    keywords_ar: list[str]
    search_queries_en: list[str] = Field(
        default_factory=list, description="Queries the search radar runs for this theme"
    )
    search_queries_ar: list[str] = Field(default_factory=list)
    sources: list[str] = Field(
        default_factory=list, description="News or police warning links this theme is based on"
    )


class ScamThemeRegistry(BaseModel):
    version: str
    themes: list[ScamTheme]


class CandidateExtra(BaseModel):
    listing_name: str | None = None  # Maps listing title
    phone: str | None = None  # Maps listing phone
    address: str | None = None


class Candidate(BaseModel):
    """A URL found by the radar or submitted by a person."""

    url: str
    source: Source
    query: str | None = Field(
        default=None, description="Search query, brand keyword or listing search that found it"
    )
    discovered_at: datetime
    extra: CandidateExtra = Field(default_factory=CandidateExtra)


class RedirectHop(BaseModel):
    url: str
    status: int | None = None


class FormInfo(BaseModel):
    """A form on the page. Never contains values typed into it."""

    action: str | None = None
    input_types: list[str] = Field(
        default_factory=list, description="HTML input types, e.g. ['text', 'password', 'tel']"
    )
    field_hints: list[str] = Field(
        default_factory=list,
        description="Lower-cased name/label/placeholder words, e.g. ['card number', 'cvv', 'otp']",
    )


class Rdap(BaseModel):
    created: datetime | None = None
    registrar: str | None = None
    abuse_email: str | None = None


class Evidence(BaseModel):
    """What the fetcher and enrichment saw for one URL."""

    url: str
    final_url: str | None = None
    redirect_chain: list[RedirectHop] = Field(default_factory=list)
    http_status: int | None = None
    screenshot_path: str | None = Field(
        default=None,
        description="Relative to the artifacts dir; served at /artifacts/<path>",
    )
    title: str | None = None
    text_excerpt: str | None = Field(default=None, description="First ~2000 chars of visible text")
    forms: list[FormInfo] = Field(default_factory=list)
    rdap: Rdap | None = None
    ip: str | None = None
    asn: int | None = None
    hosting_org: str | None = None
    hosting_abuse_email: str | None = None
    fetched_at: datetime
    fetch_error: str | None = Field(
        default=None,
        description="Set when the page could not be loaded; the engine still scores the URL",
    )


class Reason(BaseModel):
    code: str = Field(description="Stable machine code, e.g. 'lookalike_domain'")
    weight: int = Field(description="Points this reason adds (negative = lowers risk)")
    text_en: str
    text_ar: str
    evidence_ref: str | None = Field(
        default=None, description="Which evidence backs it, e.g. 'rdap.created', 'screenshot'"
    )


class Verdict(BaseModel):
    url: str
    verdict: Label
    score: int = Field(ge=0, le=100)
    brand_target: str | None = Field(default=None, description="Brand.id being impersonated")
    reasons: list[Reason]
    model_version: str
    scored_at: datetime
