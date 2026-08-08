"""Jobicy public JSON API (legal, free)."""
from ..base import BaseScraper, fetch

API = "https://jobicy.com/api/v2/remote-jobs"


class JobicyScraper(BaseScraper):
    source = "jobicy"

    def fetch_jobs(self) -> list[dict]:
        r = fetch(API, params={"count": 50})
        jobs = []
        for j in r.json().get("jobs", []):
            loc = j.get("jobLocation", [])
            jobs.append({
                "source": self.source,
                "title": j.get("jobTitle", "").strip(),
                "company": j.get("companyName", ""),
                "location": ", ".join(loc) if isinstance(loc, list) else str(loc),
                "url": j.get("url", ""),
                "salary": j.get("salary", ""),
                "tags": [],  # jobicy doesn't expose tags
                "remote": True,
            })
        return jobs