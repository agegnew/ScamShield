"""Shared data formats for ScamShield.

Every lane exchanges these shapes: radar workers (Simon) produce Candidate and
Evidence, the engine produces Verdict, the API (Agegnew) serves them to the UI
(Nati), and the brand registry (Samri) is a BrandRegistry in data/brands.json.

Change a field only after telling the whole team.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Source(str, Enum):
    """Where a URL came from."""

    LOOKALIKE = "lookalike"  # generated typo/brand variant that turned out to be registered
    CT = "ct"  # new TLS certificate seen in Certificate Transparency (crt.sh)
    NRD = "nrd"  # newly registered domain from the daily public list
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
    domain_tokens: list[str] = Field(
        default_factory=list,
        description="Strings that betray this brand inside a scam domain, e.g. 'enbd'. 4+ chars",
    )
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
    brand: str | None = Field(default=None, description="Brand.id the radar matched, if any")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Radar metadata, e.g. lookalike variant, certificate issuer, search position, "
            "Maps flags. details.replayed=true means it came from a saved SerpApi answer"
        ),
    )


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
    sensitive: list[str] = Field(
        default_factory=list,
        description="Sensitive data asked for: password, card, otp, emirates_id, phone, email",
    )


class DownloadSignal(BaseModel):
    """A link or text pushing a remote-access app or an APK install."""

    kind: str = Field(description="remote_access_link | remote_access_text | app_download_link")
    href: str | None = None
    text: str | None = None


class Contacts(BaseModel):
    phones: list[str] = Field(default_factory=list)
    whatsapp: list[str] = Field(default_factory=list)
    telegram: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)


class Fingerprints(BaseModel):
    """Traits that link sites run by the same people (scam network)."""

    favicon_mmh3: int | None = Field(
        default=None, description="Shodan favicon hash: search http.favicon.hash:<value>"
    )
    favicon_sha256: str | None = None
    dom_hash: str | None = Field(default=None, description="Page template (tag structure) hash")
    screenshot_dhash: str | None = Field(default=None, description="64-bit look-alike hash of the page")
    tracking_ids: list[str] = Field(default_factory=list, description="e.g. google_analytics:G-AB12")
    contacts: Contacts = Field(default_factory=Contacts)


class VisualMatch(BaseModel):
    """The page reuses an official brand site's favicon or template on a non-official host."""

    brand: str
    kind: Literal["same_favicon", "same_template"]
    reference_url: str | None = None
    reference_screenshot: str | None = None


class DesktopVisit(BaseModel):
    final_url: str | None = None
    http_status: int | None = None
    title: str | None = None
    screenshot_path: str | None = None
    fetch_error: str | None = None


class CloakingCheck(BaseModel):
    """Second visit as a foreign desktop browser, compared with the UAE phone visit."""

    signals: list[str] = Field(
        default_factory=list,
        description="desktop_blocked | different_destination | forms_hidden_from_desktop | different_page",
    )
    desktop: DesktopVisit | None = None


class Rdap(BaseModel):
    created: datetime | None = None
    registrar: str | None = None
    abuse_email: str | None = None


class Evidence(BaseModel):
    """What the fetcher and enrichment saw for one URL."""

    url: str
    profile: str = Field(default="mobile_ae", description="Browser profile used for the visit")
    final_url: str | None = None
    redirect_chain: list[RedirectHop] = Field(default_factory=list)
    http_status: int | None = None
    screenshot_path: str | None = Field(
        default=None,
        description="Relative to the artifacts dir; served at /artifacts/<path>",
    )
    screenshot_sha256: str | None = Field(
        default=None, description="Hash of the screenshot file, for the evidence chain"
    )
    title: str | None = None
    text_excerpt: str | None = Field(default=None, description="First ~2000 chars of visible text")
    forms: list[FormInfo] = Field(default_factory=list)
    download_signals: list[DownloadSignal] = Field(default_factory=list)
    fingerprints: Fingerprints | None = None
    visual_match: VisualMatch | None = None
    cloaking: CloakingCheck | None = None
    rdap: Rdap | None = None
    ip: str | None = None
    asn: int | None = None
    hosting_org: str | None = None
    hosting_abuse_email: str | None = None
    shared_hosting: bool = Field(
        default=False,
        description=(
            "Site lives on a free/shared platform (e.g. *.vercel.app). WHOIS age, registrar "
            "and IP then belong to the platform, not the scammer: never read them as trust"
        ),
    )
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
