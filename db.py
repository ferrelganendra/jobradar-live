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
    description TEXT DEFAULT '',
    requirements TEXT DEFAULT '',
    benefits TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    return conn


def existing_urls(source: str) -> set:
    """Return set of canonical URLs already in DB for a source."""
    conn = connect()
    rows = conn.execute("SELECT url FROM jobs WHERE source=?", (source,)).fetchall()
    conn.close()
    return {r[0] for r in rows}


def fix_placeholder_titles(jobs: list[dict]) -> int:
    """Update rows whose title is '?' with the fresh scraped title. Returns updated."""
    conn = connect()
    updated = 0
    for j in jobs:
        if j.get("title") and j["title"] != "?":
            url = j["url"].split("?")[0]
            cur = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE url=? AND title='?'", (url,)
            ).fetchone()[0]
            if cur:
                conn.execute(
                    "UPDATE jobs SET title=? WHERE url=?", (j["title"], url)
                )
                updated += 1
    conn.commit()
    conn.close()
    return updated


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
                """INSERT INTO jobs (source, title, company, location, url, salary, tags, remote, description, requirements, benefits)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (j["source"], j["title"], j["company"], j["location"],
                 url, j.get("salary", ""), ",".join(j.get("tags", [])),
                 1 if j.get("remote") else 0,
                 j.get("description", ""), j.get("requirements", ""),
                 j.get("benefits", "")),
            )
            added += 1
            new_jobs.append(j)
        except sqlite3.IntegrityError:
            # duplicate (source,url): refresh location/salary only if the fresh value is non-empty
            if j.get("location"):
                conn.execute("UPDATE jobs SET location=? WHERE url=?", (j["location"], url))
            if j.get("salary"):
                conn.execute("UPDATE jobs SET salary=? WHERE url=?", (j["salary"], url))
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    conn.close()
    return total, added, new_jobs


def all_rows() -> list[dict]:
    """Read all deduplicated jobs from DB, each as a dict keyed like a scraped job."""
    conn = connect()
    rows = conn.execute(
        "SELECT source,title,company,location,url,salary,tags,remote,description,requirements,benefits FROM jobs"
    ).fetchall()
    conn.close()
    out = []
    for src, title, co, loc, url, sal, tags, remote, desc, req, ben in rows:
        out.append({
            "source": src, "title": title, "company": co, "location": loc,
            "url": url, "salary": "",  # re-extracted by classify() from current desc (regex refreshed); DB fallback below
            "tags": [t for t in (tags or "").split(",") if t],
            "remote": bool(remote), "description": desc or "",
            "requirements": req or "", "benefits": ben or "",
            "_db_salary": sal or "",
        })
    return out


def backfill_glints_from_desc() -> int:
    """Strip Glints boilerplate desc + extract location from stored description."""
    import re
    conn = connect()
    rows = conn.execute(
        "SELECT id, location, description, company FROM jobs WHERE source='glints'"
    ).fetchall()
    rows_company = {r[0]: (r[3] or "") for r in rows}
    n = 0
    for rid, loc, desc, _co in rows:
        if not desc:
            continue
        changed = False
        new_loc = loc
        new_desc = desc
        # company from 'Jobs at {Company}' when stored empty (offshore listings)
        co = rows_company.get(rid, "")
        if not co:
            cm = re.search(r"Jobs?\s+at\s+([^,]+)", desc, re.I)
            if cm:
                co = cm.group(1).strip().strip(".,")
                conn.execute("UPDATE jobs SET company=? WHERE id=?", (co, rid))
                changed = True
        # location from breadcrumb 'Lokasi / {prov} / {kota}'
        if not (loc or "").strip():
            lm = re.search(r"Lokasi\s*:\s*[^/]+/\s*([^/]+)", desc, re.I) or \
                 re.search(r"Lokasi\s*/\s*[^/]+/\s*([^/]+)", desc, re.I)
            if lm:
                new_loc = lm.group(1).strip()
                changed = True
        # strip boilerplate: drop everything up to 'Deskripsi pekerjaan'
        dm = re.search(r"Deskripsi\s+pekerjaan\s*(.+)", desc, re.I | re.S)
        if dm:
            stripped = dm.group(1).strip()
            if stripped and stripped != new_desc:
                new_desc = stripped
                changed = True
        if changed:
            conn.execute(
                "UPDATE jobs SET location=?, description=? WHERE id=?",
                (new_loc, new_desc[:3000], rid),
            )
            n += 1
    conn.commit()
    conn.close()
    return n