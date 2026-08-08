"""JobStreet Indonesia (SEEK) — SPA, Playwright render. robots limits /job/ detail but listing accessible."""
from bs4 import BeautifulSoup
import re
from ..renderer import render
from ..base import BaseScraper

URL = "https://www.jobstreet.co.id/jobs?keywords=AI%20Engineer"


class JobstreetScraper(BaseScraper):
    source = "jobstreet"

    def fetch_jobs(self) -> list[dict]:
        html = render(URL, wait_for="body", wait_ms=8000)
        soup = BeautifulSoup(html, "lxml")
        jobs = []
        seen = set()
        for a in soup.select("a[href*='/job/']"):
            href = a.get("href", "")
            # strip tracking query + hash for stable dedup key
            path = href.split("?")[0]
            if path in seen:
                continue
            seen.add(path)
            # walk up ancestors until we find a container with h3 (title)
            card = a
            h3 = None
            for _ in range(6):
                card = card.parent
                if card is None:
                    break
                h3 = card.find("h3")
                if h3:
                    break
            title = h3.get_text(strip=True) if h3 else ""
            # strip leading (JKT/Kota) prefix from title if present
            title = re.sub(r"^\([^)]*\)\s*", "", title).strip()
            company = ""
            for sp in card.find_all("span"):
                t = sp.get_text(strip=True)
                if t.startswith("at") and len(t) > 4:
                    company = t[2:].strip()
                    break
            loc_span = card.find("span", string="Jakarta") if card else None
            location = loc_span.get_text(strip=True) if loc_span else ""
            url = "https://www.jobstreet.co.id" + path
            jobs.append({
                "source": self.source,
                "title": title,
                "company": company,
                "location": location,
                "url": url,
                "salary": "",
                "tags": [],
                "remote": "remote" in (title + " " + location).lower(),
            })
        return jobs