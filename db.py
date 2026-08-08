"""SQLite storage with dedup on (source, url)."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loker.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    title TEXT,
    company TEXT,
    location TEXT,
    url TEXT UNIQUE,
    salary TEXT,
    tags TEXT,
    remote INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    return conn


def upsert_jobs(jobs: list[dict]) -> tuple[int, int, list[dict]]:
    """Insert new jobs, skip duplicates. Returns (total_rows, new_added, new_jobs)."""
    conn = connect()
    added = 0
    new_jobs = []
    for j in jobs:
        # normalize: strip query params (Glints adds unique tracking params per render)
        url = j["url"].split("?")[0]
        try:
            conn.execute(
                """INSERT INTO jobs (source, title, company, location, url, salary, tags, remote)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (j["source"], j["title"], j["company"], j["location"],
                 url, j.get("salary", ""), ",".join(j.get("tags", [])),
                 1 if j.get("remote") else 0),
            )
            added += 1
            new_jobs.append(j)
        except sqlite3.IntegrityError:
            pass  # duplicate (source,url)
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    conn.close()
    return total, added, new_jobs