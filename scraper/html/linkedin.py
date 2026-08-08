"""LinkedIn jobs (guest, no login) — legal-grey, ToS-violating. Playwright render.
Guest scrape is limited (~60/page) but works without risking a personal account.
"""
from bs4 import BeautifulSoup
import re
from ..renderer import render
from ..base import BaseScraper

URL = "https://www.linkedin.com/jobs/search?keywords=AI%20Engineer&location=Indonesia"


class LinkedinScraper(BaseScraper):
    source = "linkedin"

    def fetch_jobs(self) -> list[dict]:
        html = render(URL, wait_for=".base-card__full-link", wait_ms=10000)
        soup = BeautifulSoup(html, "lxml")
        jobs = []
        seen = set()
        for a in soup.select(".base-card__full-link"):
            href = a.get("href", "")
            # canonical: strip tracking params -> /jobs/view/{id}
            m = re.search(r"/jobs/view/([^?]+)", href)
            if not m:
                continue
            canonical = f"https://www.linkedin.com/jobs/view/{m.group(1)}"
            if canonical in seen:
                continue
            seen.add(canonical)
            li = a.parent
            comp_el = li.select_one(".base-search-card__subtitle")
            meta_el = li.select_one(".base-search-card__metadata")
            meta = meta_el.get_text(" ", strip=True) if meta_el else ""
            # remove 'Be an early applicant' / 'X ago' noise from location
            loc = re.sub(r"(Be an early applicant|ago|today|week|day|hour)", "", meta, flags=re.I).strip().strip(",").strip()
            jobs.append({
                "source": self.source,
                "title": a.get_text(strip=True),
                "company": comp_el.get_text(strip=True) if comp_el else "",
                "location": loc,
                "url": canonical,
                "salary": "",
                "tags": [],
                "remote": "remote" in (a.get_text(strip=True) + " " + loc).lower(),
            })
        return jobs