"""Orchestrator: run all scrapers -> filter -> SQLite dedup -> JSON + report."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.api.remotive import RemotiveScraper
from scraper.api.arbeitnow import ArbeitnowScraper
from scraper.api.remoteok import RemoteOKScraper
from scraper.api.jobicy import JobicyScraper
from scraper.api.hn import HNScraper
from scraper.html.wwr import WWRScraper
from scraper.html.glints import GlintsScraper
from filter import filter_jobs
from db import upsert_jobs
from notifier import send

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
# (class, enabled) — WWR disabled (selector broken), Kalibrr login-wall
ALL_SCRAPERS = [
    (RemotiveScraper, True), (ArbeitnowScraper, True), (RemoteOKScraper, True),
    (JobicyScraper, True), (HNScraper, True), (WWRScraper, False),
    (GlintsScraper, True),
]


def run() -> tuple[list[dict], dict]:
    all_jobs, counts = [], {}
    for cls, enabled in ALL_SCRAPERS:
        if not enabled:
            continue
        try:
            jobs = cls().fetch_jobs()
            counts[cls.source] = len(jobs)
            all_jobs.extend(jobs)
        except Exception as e:
            counts[cls.source] = f"FAIL: {e.__class__.__name__}"
    return all_jobs, counts


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    raw_jobs, counts = run()
    classified = filter_jobs(raw_jobs)
    total, added, new_jobs = upsert_jobs(classified)

    with open(os.path.join(OUT, "jobs.json"), "w") as f:
        json.dump(classified, f, indent=2, ensure_ascii=False)

    targets = [j for j in classified if j["is_target"]]
    print(f"per-source: {counts}")
    print(f"raw: {len(raw_jobs)} | classified: {len(classified)} | target(AI/SWE): {len(targets)}")
    print(f"DB total: {total} rows | new added this run: {added}")

    # Telegram: notify only NEW target jobs (AI/SWE) actually added this run
    new_targets = [j for j in new_jobs if j.get("is_target")]
    if new_targets:
        lines = [f"🔔 {len(new_targets)} loker target baru (AI/SWE)"] + [
            f"• {j['title'][:60]} — {j['company'][:30]}\n  {j['location'][:40]}\n  {j['url']}"
            for j in new_targets[:10]
        ]
        if len(new_targets) > 10:
            lines.append(f"…+{len(new_targets)-10} lagi")
        send("\n".join(lines))


if __name__ == "__main__":
    main()