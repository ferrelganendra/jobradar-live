"""Remotive public JSON API (legal, free)."""
from ..base import BaseScraper, fetch

API = "https://remotive.com/api/remote-jobs"
SEARCH = ["AI", "Machine Learning", "Software Engineer", "Data"]


class RemotiveScraper(BaseScraper):
    source = "remotive"

    def fetch_jobs(self) -> list[dict]:
        jobs = []
        for q in SEARCH:
            r = fetch(API, params={"search": q, "limit": 50})
            for j in r.json().get("jobs", []):
                jobs.append({
                    "source": self.source,
                    "title": j.get("title", "").strip(),
                    "company": j.get("company_name", ""),
                    "location": j.get("candidate_required_location", ""),
                    "url": j.get("url", ""),
                    "salary": j.get("salary", ""),
                    "tags": j.get("tags", []),
                    "description": (j.get("description") or "")[:2000],
                    "remote": "remote" in (j.get("job_type") or "").lower(),
                })
        return jobs