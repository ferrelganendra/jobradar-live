"""We Work Remotely (HTML scrape, allowed robots)."""
from bs4 import BeautifulSoup
from ..base import BaseScraper, fetch

URL = "https://weworkremotely.com/categories/remote-programming-jobs"


class WWRScraper(BaseScraper):
    source = "wwr"

    def fetch_jobs(self) -> list[dict]:
        r = fetch(URL)
        soup = BeautifulSoup(r.text, "lxml")
        jobs = []
        for li in soup.select("li.job"):
            a = li.select_one("a[href*='/remote-jobs/'], a[href*='/listings/']") or li.select_one("a")
            span = li.select_one(".company")
            loc = li.select_one(".region")
            jobs.append({
                "source": self.source,
                "title": (li.select_one(".title") or a).get_text(strip=True) if a else "",
                "company": span.get_text(strip=True) if span else "",
                "location": loc.get_text(strip=True) if loc else "Remote",
                "url": "https://weworkremotely.com" + a["href"] if a and a.get("href", "").startswith("/") else (a["href"] if a else ""),
                "salary": "",
                "tags": [],
                "remote": True,
            })
        return jobs