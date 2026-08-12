"""Orchestrator: run all scrapers -> filter -> SQLite dedup -> JSON + report."""
import json
import os
import subprocess
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
from filter import filter_jobs, classify
from db import upsert_jobs, existing_urls, fix_placeholder_titles, all_rows, prune_jobs, count_jobs
from notifier import send
import feed

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


def auto_commit() -> None:
    """Sync web/data/{jobs.json,feed.xml} + copy to OUT, commit + push if changed."""
    root = os.path.dirname(os.path.abspath(__file__))
    web = os.path.join(root, "web", "data")
    changed = False
    for name in ("jobs.json", "feed.xml"):
        src = os.path.join(OUT, name)
        dst = os.path.join(web, name)
        try:
            with open(src) as a, open(dst) as b:
                if a.read() != b.read():
                    import shutil
                    shutil.copyfile(src, dst)
                    changed = True
        except OSError:
            continue
    if not changed:
        return
    try:
        subprocess.run(["git", "add", "web/data/jobs.json", "web/data/feed.xml"],
                       cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Auto: update jobs.json + feed.xml", "--",
                        "web/data/jobs.json", "web/data/feed.xml"],
                       cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "push"], cwd=root, check=True, capture_output=True)
        print("auto-commit: pushed web/data jobs.json + feed.xml")
    except subprocess.CalledProcessError as e:
        print(f"auto-commit skipped: {e.stderr.decode().strip() if e.stderr else e}")


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    raw_jobs, counts = run()
    raw_jobs = enrich_details(raw_jobs)
    classified = filter_jobs(raw_jobs)
    total, added, new_jobs = upsert_jobs(classified)
    fixed = fix_placeholder_titles(raw_jobs)
    pruned = prune_jobs()
    total = count_jobs()

    # dump deduplicated jobs (from DB, re-classified) — not the raw scraped list
    deduped = [classify(j) for j in all_rows()]
    for j in deduped:
        j.pop("_db_salary", None)  # internal fallback key, not for the public dump
    with open(os.path.join(OUT, "jobs.json"), "w") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)

    feed.write(deduped)

    # sync web/data + commit+push if either jobs.json or feed.xml changed (enables CF deploy)
    auto_commit()

    targets = [j for j in classified if j["is_it"]]
    print(f"per-source: {counts}")
    print(f"raw: {len(raw_jobs)} | classified: {len(classified)} | IT: {len(targets)}")
    print(f"DB total: {total} rows | new added this run: {added} | titles fixed: {fixed} | pruned: {pruned}")

    # Telegram: notify all NEW IT jobs, grouped by role, clean format
    new_it = [j for j in new_jobs if j.get("is_it")]
    if new_it:
        ai = [j for j in new_it if j.get("role") == "AI"]
        swe = [j for j in new_it if j.get("role") == "SWE"]
        it = [j for j in new_it if j.get("role") == "IT"]
        header = f"<b>Loker IT baru: {len(new_it)}</b>  (AI {len(ai)} · SWE {len(swe)} · IT {len(it)})"
        lines = [header, ""]

        def tag(j):
            t = []
            if j.get("remote_ok"):
                t.append("Remote")
            elif j.get("is_foreign"):
                t.append("Luar")
            if j.get("job_type") == "intern":
                t.append("Magang")
            elif j.get("job_type") == "contract":
                t.append("Kontrak")
            return ("[" + " · ".join(t) + "] ") if t else ""

        for group_name, group, icon in (("AI", ai, "🤖"), ("SWE", swe, "💻"), ("IT", it, "🖥")):
            if not group:
                continue
            lines.append(f"<b>{icon} {group_name}</b>")
            for j in group:
                loc = j.get("location") or "—"
                sal = f"💰 {j['salary']}  " if j.get("salary") else ""
                co = j.get("company") or j.get("title", "")
                lines.append(
                    f"• <b>{co[:25]}</b> — {j['title'][:40]}\n"
                    f"  {tag(j)}{sal}{loc[:40]} · <a href=\"{j['url']}\">buka</a>"
                )
            lines.append("")

        # Telegram ~4096 char limit; batch
        batch = []
        for l in lines:
            batch.append(l)
            if sum(len(x) for x in batch) > 3500:
                send("\n".join(batch), parse_mode="HTML")
                batch = []
        if batch:
            send("\n".join(batch), parse_mode="HTML")


if __name__ == "__main__":
    main()