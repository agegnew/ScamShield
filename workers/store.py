"""SQLite store for discovered URLs, the scan queue and collected evidence."""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("SCAMSHIELD_DB", Path(__file__).resolve().parent.parent / "data" / "scamshield.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    query TEXT,
    discovered_at TEXT NOT NULL,
    extra TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    status TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    error TEXT
);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status);
CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY,
    candidate_id INTEGER NOT NULL REFERENCES candidates(id),
    data TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

SOURCES = {"lookalike", "ct", "nrd", "search", "search_ad", "maps", "meta_ad", "manual", "citizen", "batch"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def add_candidate(conn, url: str, source: str, query: str | None = None, extra: dict | None = None) -> int | None:
    """Store a URL and queue a scan. Returns the new candidate id, or None if the URL was already known."""
    if source not in SOURCES:
        raise ValueError(f"unknown source {source}")
    cur = conn.execute(
        "INSERT OR IGNORE INTO candidates (url, source, query, discovered_at, extra) VALUES (?, ?, ?, ?, ?)",
        (url, source, query, now(), json.dumps(extra or {}, ensure_ascii=False)),
    )
    if not cur.rowcount:
        return None
    conn.execute("INSERT INTO jobs (candidate_id, created_at) VALUES (?, ?)", (cur.lastrowid, now()))
    return cur.lastrowid


def claim_job(conn) -> sqlite3.Row | None:
    return conn.execute(
        """UPDATE jobs SET status = 'running', attempts = attempts + 1, started_at = ?
           WHERE id = (SELECT id FROM jobs WHERE status = 'queued' ORDER BY id LIMIT 1)
           RETURNING id, candidate_id, (SELECT url FROM candidates WHERE id = candidate_id) AS url""",
        (now(),),
    ).fetchone()


def finish_job(conn, job_id: int, candidate_id: int, evidence: dict | None, error: str | None = None) -> None:
    if evidence is not None:
        conn.execute("INSERT INTO evidence (candidate_id, data, created_at) VALUES (?, ?, ?)",
                     (candidate_id, json.dumps(evidence, ensure_ascii=False), now()))
    conn.execute("UPDATE jobs SET status = ?, finished_at = ?, error = ? WHERE id = ?",
                 ("error" if error else "done", now(), error, job_id))


def requeue_stuck(conn) -> int:
    """Put jobs left 'running' by a crashed worker back in the queue."""
    return conn.execute("UPDATE jobs SET status = 'queued' WHERE status = 'running'").rowcount
