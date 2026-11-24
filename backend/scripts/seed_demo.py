"""Demo data: real cases scanned ahead of time, so a cold-start demo is never empty or offline.

Run from backend/ (uses DATABASE_URL like the API; SQLite file by default):
  python -m scripts.seed_demo scan ../data/demo/urls.txt     # add URLs as cases, fetch + score them now
  python -m scripts.seed_demo fetch                          # fetch + score every case still without evidence
                                                             # (e.g. what the radar found)
  python -m scripts.seed_demo export ../data/demo            # write cases.json + their screenshots
  python -m scripts.seed_demo load ../data/demo              # load a snapshot (skips URLs already stored)

The API loads data/demo/ by itself on start when SCAMSHIELD_SEED_DEMO=1.

urls.txt: one URL per line, optionally followed by its source (lookalike, ct, nrd, search,
search_ad, maps, manual, citizen, batch); blank lines and # comments are skipped.
Fetching needs the worker packages and Playwright Chromium.
"""

import argparse
import json
import logging
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app import engine
from app.config import ARTIFACTS_DIR
from app.contracts import Candidate, Source
from app.db import CaseRow, JobRow, SessionLocal, init_db, utcnow
from app.demo_data import SNAPSHOT, load_snapshot, screenshots_of
from app.repo import CaseRepo
from app.urls import InvalidURL, normalize_url

log = logging.getLogger("scamshield.seed_demo")


def analyse(case_id: str, url: str) -> str:
    """Fetch + enrich + score one case and save it; returns a one-line summary."""
    from app.workers import evidence as collector

    with SessionLocal() as session:
        repo = CaseRepo(session)
        case = repo.get(case_id)
        evidence = collector.collect(url)
        verdict = engine.score(url, evidence=evidence, candidate=case.candidate if case else None)
        repo.save_analysis(case_id, evidence, verdict)
        # The worker would otherwise fetch the same URL again.
        for job in session.scalars(
            select(JobRow).where(JobRow.dedupe_key == f"fetch:{case_id}", JobRow.status == "pending")
        ):
            job.status, job.finished_at = "done", utcnow()
        session.commit()
    return f"{verdict.verdict.value:<10} {verdict.score:>3}  {url}"


def _run(pairs: list[tuple[str, str]], workers: int) -> None:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(analyse, cid, url) for cid, url in pairs]
        for i, future in enumerate(futures, 1):
            try:
                print(f"[{i}/{len(pairs)}] {future.result()}", flush=True)
            except Exception as exc:  # one bad site must not stop the seeding
                print(f"[{i}/{len(pairs)}] failed {pairs[i - 1][1]}: {type(exc).__name__}: {exc}", flush=True)


def read_urls(path: Path) -> list[tuple[str, Source]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        source = Source(parts[1]) if len(parts) > 1 else Source.MANUAL
        out.append((parts[0], source))
    return out


def cmd_scan(args) -> int:
    pairs = []
    with SessionLocal() as session:
        repo = CaseRepo(session)
        for raw, source in read_urls(args.file):
            try:
                url = normalize_url(raw)
            except InvalidURL as exc:
                print(f"skip {raw}: {exc}")
                continue
            case, _ = repo.upsert_candidate(
                Candidate(url=url, source=source, discovered_at=datetime.now(timezone.utc))
            )
            if case.evidence is None or args.rescan:
                pairs.append((case.id, case.candidate.url))
    _run(pairs, args.workers)
    return 0


def cmd_fetch(args) -> int:
    with SessionLocal() as session:
        rows = session.execute(
            select(CaseRow.id, CaseRow.url).where(CaseRow.evidence_json.is_(None)).order_by(CaseRow.discovered_at)
        ).all()
    pairs = [(r.id, r.url) for r in rows][: args.limit or None]
    print(f"{len(pairs)} cases without evidence")
    _run(pairs, args.workers)
    return 0


def cmd_export(args) -> int:
    out: Path = args.dir
    (out / "screenshots").mkdir(parents=True, exist_ok=True)
    with SessionLocal() as session:
        cases = [c for c in CaseRepo(session).all() if c.evidence is not None and c.verdict.score >= args.min_score]
    copied = 0
    for case in cases:
        for rel in screenshots_of(case):
            src = ARTIFACTS_DIR / rel
            if src.exists():
                shutil.copy2(src, out / "screenshots" / Path(rel).name)
                copied += 1
    data = [c.model_dump(mode="json") for c in cases]
    (out / SNAPSHOT).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"exported {len(cases)} cases and {copied} screenshots to {out}")
    return 0


def cmd_load(args) -> int:
    print(f"loaded {load_snapshot(args.dir)} cases from {args.dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("scan", help="add URLs from a file as cases and analyse them now")
    p.add_argument("file", type=Path)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--rescan", action="store_true", help="analyse again even if evidence exists")
    p.set_defaults(func=cmd_scan)
    p = sub.add_parser("fetch", help="analyse every case that has no evidence yet")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--limit", type=int, default=0)
    p.set_defaults(func=cmd_fetch)
    p = sub.add_parser("export", help="write analysed cases + screenshots to a folder")
    p.add_argument("dir", type=Path)
    p.add_argument("--min-score", type=int, default=0)
    p.set_defaults(func=cmd_export)
    p = sub.add_parser("load", help="load a snapshot folder into the database")
    p.add_argument("dir", type=Path)
    p.set_defaults(func=cmd_load)
    args = parser.parse_args(argv)
    init_db()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
