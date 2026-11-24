"""What each job type does. Glue between radar, fetcher, enrichment and engine."""

import logging

from sqlalchemy.orm import Session

from .. import engine as detection
from .. import jobs
from ..brands import load_registry
from ..engine import feeds
from ..repo import CaseRepo
from . import enrich as enrichment
from . import fetcher
from .radar import SOURCES

log = logging.getLogger("scamshield.pipeline")


def run_fetch(session: Session, url: str) -> None:
    """Fetch + enrich + score one URL and save the result on its case.

    The fetcher checks every request against the SSRF guard and returns Evidence with
    fetch_error for offline or blocked sites; enrichment still adds WHOIS/DNS for offline ones.
    """
    repo = CaseRepo(session)
    case = repo.find_by_url(url)
    if case is None or case.candidate.url != url:
        log.warning("fetch job for unknown URL %s, skipping", url)
        return

    evidence = enrichment.enrich(fetcher.fetch(url))
    verdict = detection.score(url, evidence=evidence, candidate=case.candidate)
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
    jobs.FETCH: lambda session, payload: run_fetch(session, payload["url"]),
    jobs.RADAR: lambda session, payload: run_radar(session, payload["source"]),
    jobs.FEEDS: lambda session, payload: feeds.refresh(),
}
