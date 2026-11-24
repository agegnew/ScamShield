"""Scan queue worker: takes queued URLs, collects evidence, stores it.

Usage:
    python -m workers.runner add https://a.example https://b.example   # queue URLs (source=manual)
    python -m workers.runner batch urls.txt                            # queue one URL per line (source=batch)
    python -m workers.runner run [--workers 3] [--once]                # process the queue
"""
import argparse
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from workers import store
from workers.evidence import collect

log = logging.getLogger("runner")
IDLE_SLEEP_S = 2


def work_one() -> bool:
    conn = store.connect()
    job = store.claim_job(conn)
    if not job:
        return False
    try:
        evidence = collect(job["url"])
        store.finish_job(conn, job["id"], job["candidate_id"], evidence,
                         error=evidence["fetch_error"] if evidence["status"] == "blocked" else None)
        log.info("%s %s -> %s", evidence["status"], job["url"], evidence.get("final_url"))
    except Exception as exc:
        store.finish_job(conn, job["id"], job["candidate_id"], None, error=f"{type(exc).__name__}: {exc}")
        log.exception("job %s failed", job["id"])
    return True


def worker_loop(once: bool) -> None:
    while True:
        if not work_one():
            if once:
                return
            time.sleep(IDLE_SLEEP_S)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("add").add_argument("urls", nargs="+")
    sub.add_parser("batch").add_argument("file")
    run = sub.add_parser("run")
    run.add_argument("--workers", type=int, default=3)
    run.add_argument("--once", action="store_true", help="stop when the queue is empty")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(threadName)s %(message)s")

    conn = store.connect()
    if args.cmd in ("add", "batch"):
        urls = args.urls if args.cmd == "add" else [l.strip() for l in open(args.file) if l.strip()]
        source = "manual" if args.cmd == "add" else "batch"
        added = sum(store.add_candidate(conn, url, source) is not None for url in urls)
        print(f"queued {added}, already known {len(urls) - added}")
        return

    stuck = store.requeue_stuck(conn)
    if stuck:
        log.info("requeued %d stuck jobs", stuck)
    with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="w") as pool:
        for _ in range(args.workers):
            pool.submit(worker_loop, args.once)


if __name__ == "__main__":
    main()
