"""Demo snapshot: real cases scanned ahead of time (data/demo/), loaded so a cold-start demo is
never empty and still works offline. Written by `python -m scripts.seed_demo export`."""

import json
import logging
import shutil
from pathlib import Path

from sqlalchemy import select

from . import engine
from .api_models import Case
from .config import ARTIFACTS_DIR
from .db import CaseRow, SessionLocal
from .repo import CaseRepo

log = logging.getLogger("scamshield.demo_data")

SNAPSHOT = "cases.json"


def screenshots_of(case: Case) -> list[str]:
    """Screenshot paths (relative to ARTIFACTS_DIR) that the case's evidence points at."""
    ev = case.evidence
    if ev is None:
        return []
    paths = [ev.screenshot_path]
    if ev.cloaking and ev.cloaking.desktop:
        paths.append(ev.cloaking.desktop.screenshot_path)
    return [p for p in paths if p and not p.startswith("mock/")]


def load_snapshot(directory: Path) -> int:
    """Add the snapshot's cases that are not stored yet (by URL), copy their screenshots and score
    them again with the current engine. Returns how many were added."""
    path = directory / SNAPSHOT
    if not path.exists():
        return 0
    cases = [Case.model_validate(c) for c in json.loads(path.read_text(encoding="utf-8"))]
    added = 0
    with SessionLocal() as session:
        repo = CaseRepo(session)
        known_urls = set(session.scalars(select(CaseRow.url)))
        known_ids = set(session.scalars(select(CaseRow.id)))
        for case in cases:
            if case.candidate.url in known_urls:
                continue
            for rel in screenshots_of(case):
                src, dst = directory / "screenshots" / Path(rel).name, ARTIFACTS_DIR / rel
                if src.exists() and not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
            verdict = engine.score(case.candidate.url, evidence=case.evidence, candidate=case.candidate)
            repo.add(
                case.candidate,
                verdict,
                case.evidence,
                case.status,
                case.decisions,
                case_id=None if case.id in known_ids else case.id,
            )
            added += 1
    if added:
        log.info("loaded %d demo cases from %s", added, directory)
    return added
