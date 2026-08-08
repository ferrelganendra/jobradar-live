"""HN Who's Hiring via Algolia public API (legal, free)."""
from ..base import BaseScraper, fetch

API = "https://hn.algolia.com/api/v1/search_by_date"

# Story titles that open the monthly thread
TITLE = "who is hiring"


class HNScraper(BaseScraper):
    source = "hn"

    def fetch_jobs(self) -> list[dict]:
        r = fetch(API, params={"tags": "story", "query": TITLE, "hitsPerPage": 30})
        jobs = []
        for hit in r.json().get("hits", []):
            title = hit.get("title") or ""
            if TITLE not in title.lower():
                continue
            jobs.append({
                "source": self.source,
                "title": f"Who's Hiring thread ({hit.get('created_at', '')[:10]})",
                "company": "Hacker News",
                "location": "Remote/US/EU",
                "url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                "salary": "",
                "tags": [],
                "remote": True,
            })
        return jobs