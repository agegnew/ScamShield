"""Detection engine entry point (Agegnew + Claude Code).

`score()` is the only function the API and the worker call. It must return a
Verdict for every URL, with or without Evidence (the site may be offline).

v0 knows only the official-domain allowlist. Task 9 adds the layers, cheapest
first: threat feeds -> URL model -> brand lookalike -> AR/EN scam keywords ->
page signals -> helpline check.

Domain age: when evidence.shared_hosting is true (e.g. *.vercel.app) the WHOIS
date is the platform's — never treat it as "old domain = safer"; use
domain_age_days(), which returns None in that case.
"""

from datetime import datetime, timezone

from ..brands import official_brand_for_domain
from ..contracts import Candidate, Evidence, Label, Reason, Verdict
from ..messages import official_domain_reason
from ..urls import hostname

MODEL_VERSION = "engine-0"
FRAUD_AT = 70
SUSPICIOUS_AT = 30


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
) -> Verdict:
    target = evidence.final_url if evidence and evidence.final_url else url
    host = hostname(target)
    now = datetime.now(timezone.utc)

    brand = official_brand_for_domain(host)
    if brand:
        return Verdict(
            url=url,
            verdict=Label.LEGIT,
            score=0,
            reasons=[official_domain_reason(brand, host)],
            model_version=MODEL_VERSION,
            scored_at=now,
        )

    return Verdict(
        url=url,
        verdict=Label.SUSPICIOUS,
        score=50,
        reasons=[
            Reason(
                code="engine_incomplete",
                weight=0,
                text_en="Not scored yet: the detection engine is still being built",
                text_ar="لم يتم التقييم بعد: محرك الكشف قيد البناء",
            )
        ],
        model_version=MODEL_VERSION,
        scored_at=now,
    )
