"""Detection engine entry point (Agegnew + Claude Code).

`score()` is the only function the API and the worker call. It returns a
Verdict for every URL, with or without Evidence (the site may be offline).

Layers, cheapest first (app/engine/checks.py):
  official domain (short-circuit) -> popular site -> phishing feeds -> URL model
  -> brand lookalike / typosquat -> URL shape -> scam themes in URL
  -> page signals -> domain age -> Maps helpline check

Domain age: when evidence.shared_hosting is true (e.g. *.vercel.app) the WHOIS
date is the platform's — never treat it as "old domain = safer";
domain_age_days() returns None in that case.
"""

from datetime import datetime, timezone

from ..brands import load_registry, official_brand_for_domain
from ..config import USE_FEEDS
from ..contracts import Candidate, Evidence, Label, Verdict
from ..messages import official_domain_reason
from ..themes import load_themes
from ..urls import hostname, registrable_domain
from . import model
from .checks import CHECKS, Ctx
from .lists import platform_of

FRAUD_AT = 70
SUSPICIOUS_AT = 30


def model_version() -> str:
    return f"engine-1/{model.model_name()}"


MODEL_VERSION = "engine-1"


def domain_age_days(evidence: Evidence | None, now: datetime | None = None) -> int | None:
    """Age of the scanned site's own domain, or None when unknown or meaningless."""
    if evidence is None or evidence.shared_hosting or not evidence.rdap:
        return None
    created = evidence.rdap.created
    if created is None:
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return ((now or datetime.now(timezone.utc)) - created).days


def label_for(points: int) -> Label:
    if points >= FRAUD_AT:
        return Label.FRAUD
    if points >= SUSPICIOUS_AT:
        return Label.SUSPICIOUS
    return Label.LEGIT


def score(
    url: str,
    evidence: Evidence | None = None,
    candidate: Candidate | None = None,
    use_feeds: bool | None = None,
) -> Verdict:
    now = datetime.now(timezone.utc)
    host = hostname(url)
    final_url = evidence.final_url if evidence and evidence.final_url else url
    final_host = hostname(final_url) or host

    for h in (final_host, host):
        brand = official_brand_for_domain(h)
        if brand:
            return Verdict(
                url=url,
                verdict=Label.LEGIT,
                score=0,
                reasons=[official_domain_reason(brand, h)],
                model_version=model_version(),
                scored_at=now,
            )

    domain = registrable_domain(host) if host else ""
    final_domain = registrable_domain(final_host) if final_host else ""
    platform = platform_of(final_host, final_domain) or platform_of(host, domain)
    if platform is None and evidence is not None and evidence.shared_hosting:
        platform = final_domain  # the fetcher knows a platform we don't list
    ctx = Ctx(
        url=url,
        host=host,
        domain=domain,
        final_url=final_url,
        final_host=final_host,
        final_domain=final_domain,
        platform=platform,
        evidence=evidence,
        candidate=candidate,
        brands=load_registry().brands,
        themes=load_themes().themes,
        use_feeds=USE_FEEDS if use_feeds is None else use_feeds,
    )
    reasons = [reason for check in CHECKS for reason in check(ctx)]
    points = max(0, min(100, sum(r.weight for r in reasons)))
    reasons.sort(key=lambda r: abs(r.weight), reverse=True)
    return Verdict(
        url=url,
        verdict=label_for(points),
        score=points,
        brand_target=ctx.brand_target,
        reasons=reasons,
        model_version=model_version(),
        scored_at=now,
    )
