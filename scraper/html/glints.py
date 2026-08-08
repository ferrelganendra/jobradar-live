"""Glints job board (SPA, Playwright render)."""
from bs4 import BeautifulSoup
from ..renderer import render
from ..base import BaseScraper

URL = "https://glints.com/id/opportunities/jobs/explore?keyword=AI%20Engineer&countryName=INDONESIA&page=1"


class GlintsScraper(BaseScraper):
    source = "glints"

    def fetch_jobs(self) -> list[dict]:
        html = render(URL, wait_for="a[href*='/opportunities/jobs']")
        soup = BeautifulSoup(html, "lxml")
        jobs = []
        seen = set()
        for a in soup.select("a[href*='/opportunities/jobs/']"):
            href = a.get("href", "")
            if "/opportunities/jobs/" not in href or href in seen:
                continue
            seen.add(href)
            title_el = a.select_one(".job-title, [class*='title']")
            comp_el = a.select_one(".company, [class*='company']")
            loc_el = a.select_one(".job-location, [class*='location']")
            url = href if href.startswith("http") else "https://glints.com" + href
            jobs.append({
                "source": self.source,
                "title": title_el.get_text(strip=True) if title_el else "?",
                "company": comp_el.get_text(strip=True) if comp_el else "",
                "location": loc_el.get_text(strip=True) if loc_el else "",
                "url": url,
                "salary": "",
                "tags": [],
                "remote": "remote" in url.lower() or (loc_el and "remote" in loc_el.get_text().lower()),
            })
        return jobs