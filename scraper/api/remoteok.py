"""RemoteOK public JSON API (legal, free). Returns array of jobs."""
from ..base import BaseScraper, fetch

API = "https://remoteok.com/api"


class RemoteOKScraper(BaseScraper):
    source = "remoteok"

    def fetch_jobs(self) -> list[dict]:
        r = fetch(API)
        data = r.json()  # first element is a notice dict
        jobs = []
        for j in data:
            if not isinstance(j, dict) or "position" not in j:
                continue  # skip notice/metadata
            jobs.append({
                "source": self.source,
                "title": j.get("position", "").strip(),
                "company": j.get("company", ""),
                "location": j.get("location", ""),
                "url": j.get("url", ""),
                "salary": str(j.get("salary_min", "")) + " - " + str(j.get("salary_max", "")),
                "tags": j.get("tags", []),
                "remote": True,
            })
        return jobs