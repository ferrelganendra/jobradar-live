"""Arbeitnow public JSON API (legal, free)."""
from ..base import BaseScraper, fetch

API = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowScraper(BaseScraper):
    source = "arbeitnow"

    def fetch_jobs(self) -> list[dict]:
        r = fetch(API)
        data = r.json().get("data", [])
        jobs = []
        for j in data:
            jobs.append({
                "source": self.source,
                "title": j.get("title", "").strip(),
                "company": j.get("company_name", ""),
                "location": ", ".join(j.get("location", [])),
                "url": j.get("url", ""),
                "salary": j.get("salary", ""),
                "tags": j.get("tags", []),
                "description": (j.get("description") or "")[:2000],
                "remote": j.get("remote", False),
            })
        return jobs