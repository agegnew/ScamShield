"""What each job type does. Glue between radar, fetcher, enrichment and engine."""

import logging

from sqlalchemy.orm import Session

from .. import jobs, radar_runs
from ..brands import load_registry
from ..engine import feeds
from ..repo import CaseRepo
from . import ai_review
from . import evidence as collector
from .radar import SOURCES

log = logging.getLogger("scamshield.pipeline")


def run_fetch(session: Session, url: str) -> None:
    """Fetch + enrich + visual match + cloaking check, then score and save on the case.

    The fetcher checks every request against the SSRF guard and returns Evidence with
    fetch_error for offline or blocked sites; enrichment still adds WHOIS/DNS for offline ones.
    """
    repo = CaseRepo(session)
    case = repo.find_by_url(url)
    if case is None or case.candidate.url != url:
        log.warning("fetch job for unknown URL %s, skipping", url)
        return

    evidence = collector.collect(url)
    # Borderline pages also get Claude's look (ai_review.py); off without ANTHROPIC_API_KEY.
    evidence, verdict = ai_review.score_with_review(url, evidence, case.candidate)
    repo.save_analysis(case.id, evidence, verdict)
    log.info("scored %s -> %s %s", url, verdict.verdict.value, verdict.score)


def run_radar(session: Session, source_name: str) -> int:
    """Run one radar source; store new URLs as cases and queue a fetch for each."""
    source = SOURCES[source_name]
    repo = CaseRepo(session)
    created = 0
    for candidate in source.discover(load_registry().brands):
        case, is_new = repo.upsert_candidate(candidate)
        if is_new:
            created += 1
            jobs.enqueue(session, jobs.FETCH, {"url": case.candidate.url}, f"fetch:{case.id}")
    log.info("radar %s: %d new URLs", source_name, created)
    return created


HANDLERS = {
    jobs.SCAN: lambda session, payload: run_fetch(session, payload["url"]),
    jobs.FETCH: lambda session, payload: run_fetch(session, payload["url"]),
    # {"run": id} = a whole radar run (button or daily schedule); {"source": name} = one source.
    jobs.RADAR: lambda session, payload: (
        radar_runs.execute(session, payload["run"]) if "run" in payload else run_radar(session, payload["source"])
    ),
    jobs.FEEDS: lambda session, payload: feeds.refresh(),
}
