"""Arbeitnow public JSON API (legal, free)."""
from ..base import BaseScraper, fetch

API = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowScraper(BaseScraper):
    source = "arbeitnow"

    def fetch_jobs(self) -> list[dict]:
        r = fetch(API)
        data = r.json().get("data", [])
        jobs = []
        seen = set()
        for j in data:
            url = j.get("url", "") or f"{j.get('title','')}-{jobs}"
            if url in seen:
                continue
            seen.add(url)
            jobs.append({
                "source": self.source,
                "title": j.get("title", "").strip(),
                "company": j.get("company_name", ""),
                "location": j.get("location", "") if isinstance(j.get("location"), str) else ", ".join(j.get("location", [])),
                "url": j.get("url", ""),
                "salary": j.get("salary", ""),
                "tags": j.get("tags", []),
                "description": (j.get("description") or "")[:2000],
                "remote": j.get("remote", False),
            })
        return jobs