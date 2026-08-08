"""One-off: backfill description/salary/location for jobs missing detail."""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import connect
from scraper.html.jobstreet import JobstreetScraper
from scraper.html.glints import GlintsScraper

SCRAPERS = {"jobstreet": JobstreetScraper, "glints": GlintsScraper}


def backfill() -> None:
    conn = connect()
    for src, cls in SCRAPERS.items():
        rows = conn.execute(
            "SELECT id, url FROM jobs WHERE source=? AND description=''", (src,)
        ).fetchall()
        print(f"[{src}] {len(rows)} to backfill")
        scraper = cls()
        for jid, url in rows:
            det = scraper.fetch_detail(url)
            if det and det.get("description"):
                conn.execute(
                    "UPDATE jobs SET description=?, salary=?, location=? WHERE id=?",
                    (det["description"], det.get("salary", ""), det.get("location", ""), jid),
                )
                conn.commit()
                print(f"  ok {jid}")
            else:
                print(f"  fail {jid}")
    conn.close()


if __name__ == "__main__":
    backfill()