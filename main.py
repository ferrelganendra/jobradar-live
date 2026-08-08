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
from scraper.html.jobstreet import JobstreetScraper
from scraper.html.linkedin import LinkedinScraper
from filter import filter_jobs
from db import upsert_jobs, existing_urls, fix_placeholder_titles
from notifier import send

# scrapers that can fetch rich detail from a per-job page
DETAIL_SOURCES = {"glints": None, "jobstreet": None}  # filled after import

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
# (class, enabled) — WWR disabled (selector broken), Kalibrr login-wall
ALL_SCRAPERS = [
    (RemotiveScraper, True), (ArbeitnowScraper, True), (RemoteOKScraper, True),
    (JobicyScraper, True), (HNScraper, True), (WWRScraper, False),
    (GlintsScraper, True), (JobstreetScraper, True), (LinkedinScraper, True),
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


def enrich_details(jobs: list[dict]) -> list[dict]:
    """For new jobs from detail-capable sources, fetch description/salary/location."""
    for cls, enabled in ALL_SCRAPERS:
        if not enabled or not hasattr(cls, "fetch_detail"):
            continue
        scraper = cls()
        known = existing_urls(cls.source)
        for j in jobs:
            if j["source"] != cls.source:
                continue
            path = j["url"].split("?")[0]
            if path in known:
                continue  # already scraped detail before
            det = scraper.fetch_detail(j["url"])
            if det:
                j.update(det)
    return jobs


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    raw_jobs, counts = run()
    raw_jobs = enrich_details(raw_jobs)
    classified = filter_jobs(raw_jobs)
    total, added, new_jobs = upsert_jobs(classified)
    fixed = fix_placeholder_titles(raw_jobs)

    with open(os.path.join(OUT, "jobs.json"), "w") as f:
        json.dump(classified, f, indent=2, ensure_ascii=False)

    targets = [j for j in classified if j["is_it"]]
    print(f"per-source: {counts}")
    print(f"raw: {len(raw_jobs)} | classified: {len(classified)} | IT: {len(targets)}")
    print(f"DB total: {total} rows | new added this run: {added} | titles fixed: {fixed}")

    # Telegram: notify ALL new IT jobs, tagged role + remote/type/foreign labels
    new_it = [j for j in new_jobs if j.get("is_it")]
    if new_it:
        role_icon = {"AI": "🤖", "SWE": "💻", "IT": "🖥"}
        ai_n = sum(1 for j in new_it if j.get("role") == "AI")
        swe_n = sum(1 for j in new_it if j.get("role") == "SWE")
        type_icon = {"intern": "🎓", "contract": "📄", "part": "⏱", "full": "🕐"}
        lines = [f"🔔 {len(new_it)} loker IT baru (AI {ai_n} / SWE {swe_n} / IT {len(new_it)-ai_n-swe_n})"]
        for j in new_it:
            t = j.get("job_type", "full")
            tag = type_icon.get(t, "🕐")
            if j.get("remote_ok"):
                tag += "🌍"
            elif j.get("is_foreign"):
                tag += "🌐"
            title = j["title"][:55]
            lines.append(
                f"{role_icon.get(j.get('role'),'•')} {tag} {title}\n"
                f"  {j['company'][:25]} • {j['location'][:35]}\n"
                f"  {j['url']}"
            )
        # Telegram hard limit ~4096 chars; batch ~12 jobs per message
        batch = []
        for l in lines:
            batch.append(l)
            if sum(len(x) for x in batch) > 3500:
                send("\n".join(batch))
                batch = []
        if batch:
            send("\n".join(batch))


if __name__ == "__main__":
    main()