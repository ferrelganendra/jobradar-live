"""Glints job board (SPA, Playwright render)."""
from bs4 import BeautifulSoup
import re
from urllib.parse import quote
from ..renderer import render
from ..base import BaseScraper

SEARCH = ["AI Engineer", "Data Scientist", "Data Analyst", "Management Trainee", "Graduate Trainee"]
URL = "https://glints.com/id/opportunities/jobs/explore?keyword={}&countryName=INDONESIA&page=1"

# boilerplate to strip from detail page text
SKIP = ["Lowongan Kerja", "PERUSAHAAN", "Blog", "Unduh App Glints", "bahasa"]


def extract_company(text: str, title: str) -> str:
    """Glints detail text: 'Lowongan {title} di {COMPANY}, | Glints ...'
    Company sits between 'di ' and ', |' on the first line."""
    if not text or not title:
        return ""
    t = title.strip()
    m = re.search(re.escape(t) + r"[^\n]*?\bdi ([^,|]+)", text, re.I)
    if not m:
        m = re.search(r"\bdi\s+([A-Z0-9][^,|]{2,60})", text, re.I)
    if not m:
        return ""
    co = re.sub(r"\s+", " ", m.group(1)).strip()
    co = co.replace(" |", "").replace("|", "").strip(" ·,;:")
    return co if co else ""


class GlintsScraper(BaseScraper):
    source = "glints"

    def fetch_detail(self, url: str, title: str = "") -> dict:
        """Render job detail page, extract description/salary/location."""
        try:
            html = render(url, wait_for="body", wait_ms=6000)
        except Exception:
            return {}
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text("\n", strip=True)
        # salary: look for Rp xx or xxjt (reject foreign currency like ₫/$/€/£)
        salary = ""
        m = re.search(r"Rp\s?[\d.,]+(?:\s?-\s?[\d.,]+)?\s?(?:jt|juta|rb|ribu)?", text) or \
            re.search(r"(?<![₫$€£])\d[\d.,]+\s?-\s?\d[\d.,]+\s?jt", text)
        if m:
            salary = m.group(0)
        # location: Glints text has breadcrumb 'Lokasi / {provinsi} / {kota} / {title}'
        loc = ""
        lm = re.search(r"Lokasi\s*/\s*[^/]+/\s*([^/]+)", text, re.I)
        if lm:
            loc = lm.group(1).strip()
        # description: drop boilerplate header, keep from 'Deskripsi pekerjaan'
        desc = text
        dm = re.search(r"Deskripsi\s+pekerjaan\s*(.+)", text, re.I | re.S)
        if dm:
            desc = dm.group(1).strip()
        return {
            "description": desc[:3000],
            "salary": salary,
            "location": loc,
            "company": extract_company(text, title),
        }

    def fetch_jobs(self) -> list[dict]:
        jobs, seen = [], set()
        for query in SEARCH:
            try:
                html = render(URL.format(quote(query)), wait_for="a[href*='/opportunities/jobs']")
            except Exception:
                continue
            soup = BeautifulSoup(html, "lxml")
            for a in soup.select("a[href*='/opportunities/jobs/']"):
                href = a.get("href", "")
                if "/opportunities/jobs/" not in href or href in seen:
                    continue
                seen.add(href)
                title = a.get_text(strip=True)
                salary = ""
                h2 = a.parent
                if h2:
                    for sib in h2.find_next_siblings():
                        if sib.name == "span":
                            salary = sib.get_text(strip=True)
                            break
                url = href if href.startswith("http") else "https://glints.com" + href
                jobs.append({
                    "source": self.source, "title": title, "company": "", "location": "",
                    "url": url, "salary": salary, "tags": [],
                    "remote": "remote" in (title + " " + salary).lower(),
                })
        return jobs