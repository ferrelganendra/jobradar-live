"""Keyword filter: AI/ML/SWE target + location + remote + salary mention."""
import re

# Primary target roles (case-insensitive)
AI_KEYWORDS = ["ai engineer", "machine learning", "ml engineer", "deep learning",
               "artificial intelligence", "data scientist", "nlp", "computer vision",
               "llm", "genai", "prompt engineer", "mlops", "ai/ml", "data engineer",
               "ai developer", "ai research", "ai specialist", "ai product"]
SOFTWARE_KEYWORDS = ["software engineer", "software developer", "backend engineer",
                     "frontend engineer", "full stack", "fullstack", "devops",
                     "sre", "data engineer", "programmer", "app developer",
                     "web developer", "mobile developer", "android", "ios developer",
                     "react", "node.js", "python developer", "java developer",
                     "golang", "typescript", ".net developer", "php developer"]
# Other IT roles (non AI/SWE but still IT)
OTHER_IT_KEYWORDS = ["qa", "quality assurance", "tester", "software tester",
                     "data analyst", "business analyst", "it support", "network engineer",
                     "cyber security", "security engineer", "cloud engineer", "cloud architect",
                     "devops engineer", "database administrator", "dba", "sql developer",
                     "system administrator", "sysadmin", "ux", "ui designer", "product manager",
                     "scrum master", "project manager", "technical writer", "erp", "sap"]
# Indonesia cities (any mention => keep)
ID_CITIES = ["jakarta", "tangsel", "tangerang", "bekasi", "depok", "bandung",
             "surabaya", "yogyakarta", "jogja", "semarang", "malang", "medan",
             "balikpapan", "makassar", "denpasar", "bali", "solo", "batam",
             "surakarta", "pekanbaru", "padang", "palembang", "manado",
             "pontianak", "samarinda", "cilegon", "sidoarjo", "bogor",
             "sleman", "bantul", "klaten", "karawang", "cilacap", "jambi",
             "aceh", "lampung", "banten", "jatim", "jabar", "jawa barat",
             "jawa timur", "jawa tengah", "sulawesi", "sumatera", "kalimantan", "riau"]

REMOTE_WORDS = ["remote", "work from home", "wfh", "hybrid", "fully remote"]

# Industry detection (title/desc keyword -> industry bucket). Ordered: first match wins.
# "other" = teknologi/IT yang tak masuk industry umum, biar fair netral.
INDUSTRY_KEYWORDS = [
    # Non-tech industries (representative, not IT-centric)
    ("Sales", ["sales", "account executive", "business development", "bd ", "closing", "quota", "revenue", "account manager", "sdr", "bdr", "pre-sales"]),
    ("Marketing", ["marketing", "seo", "sem", "content", "copywriter", "social media", "brand", "growth", "advertising", "campaign", "pr ", "public relation"]),
    ("Finance", ["finance", "accounting", "accountant", "audit", "payable", "receivable", "financial", "tax", "bookkeeping", "treasury", "banking", "investment"]),
    ("HR", ["hr ", "human resource", "recruiter", "talent", "people ops", "payroll", "hiring", "staffing"]),
    ("Support", ["support", "customer service", "customer care", "helpdesk", "service desk", "receptionist", "call center", "client success"]),
    ("Healthcare", ["healthcare", "medical", "nurse", "nursing", "patient", "clinical", "pharma", "pharmacist", "doctor", "therapy", "care specialist"]),
    ("Design", ["design", "graphic designer", "ui designer", "ux designer", "illustrator", "creative", "art director", "visual"]),
    ("Legal", ["legal", "lawyer", "attorney", "paralegal", "compliance officer", "contract manager"]),
    ("Operations", ["operations", "supply chain", "logistics", "procurement", "inventory", "warehouse", "facility"]),
    ("Education", ["education", "teacher", "tutor", "instructor", "lecturer", "professor", "academic", "curriculum"]),
    ("Data", ["data analyst", "data scientist", "data engineer", "data entry", "data labeling", "data annotation", "analyst"]),
    ("Engineering", ["mechanical engineer", "electrical", "civil engineer", "elektro", "elektrotechnik", "chemical engineer", "industrial engineer", "process engineer", "senior design engineer"]),
    # Tech umbrella (default IT-ish)
    ("Teknologi", ["software", "developer", "engineer", "frontend", "backend", "fullstack", "devops", "sre", "infrastructure", "cloud", "programmer", "it ", "tech", "data engineer", "qa", "quality", "security", "cyber", "ml", "ai ", "machine learning", "artificial"]),
]


def _clean_location(loc) -> str:
    """Strip trailing time-ago / applicant / hiring noise from a location string."""
    if not loc:
        return ""
    s = str(loc)
    s = re.sub(r"\s*\b\d+\s?[smhdwy]\b\s*", " ", s, flags=re.I)
    s = re.sub(r"(Be an early applicant|Actively Hiring|\b\d+\s?(years?|weeks?|months?|days?|hours?|minutes?|seconds?)\s?ago)", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip().strip(",").strip()
    return s


def _extract_salary(job: dict) -> str:
    """Pull salary from description/requirements if not already populated. Returns formatted string."""
    if job.get("salary"):
        return str(job["salary"])
    text = " ".join([
        job.get("description", ""), job.get("requirements", ""),
        job.get("title", ""), job.get("location", ""), str(job.get("tags", "")),
    ])
    if not text:
        return ""
    # Rp 5-8 juta / Rp5.000.000 - Rp8.000.000 / Rp 12 jt
    m = re.search(r"Rp\s?([\d.,]+[\s\-to–]+[\d.,]+\s?(juta|jt|j|rb|ribu|k)?|[\d.,]+\s?(juta|jt|j)\b)", text, re.I)
    if m:
        return "Rp " + re.sub(r"\s+", " ", m.group(1)).strip()
    # USD/EUR/GBP: $120k / $80k-$120k / €70k / £50k / $30,000 / €60,000-€90,000
    # only accept ranges, 'k'/'K', or comma-separated amounts (>=1000) — avoids grabbing stray years/IDs
    m = re.search(r"([$€£])\s?(\d[\d,.]*(?:k|K)?)(?![MBb]|\d)(?:\s?[-–]\s?([$€£]?\s?\d[\d,.]*(?:k|K)?)(?![MBb]|\d))?\s?(/yr|/year|per year|per annum)?", text)
    if m and (m.group(3) or "k" in m.group(2).lower() or "," in m.group(2)):
        cur = {"$": "USD", "€": "EUR", "£": "GBP"}[m.group(1)]
        amt = re.sub(r"\s+", "", m.group(2))
        if m.group(3):
            amt += "-" + re.sub(r"\s+", "", m.group(3))
        return f"{cur} {amt} {m.group(4) or ''}".rstrip()
    return ""


def classify(job: dict) -> dict:
    """Return job with added: is_it, role (AI/SWE/IT), is_remote, id_city."""
    job["location"] = _clean_location(job.get("location", ""))
    if not job.get("salary"):
        job["salary"] = _extract_salary(job)
    if not job.get("salary") and job.get("_db_salary"):
        # fallback to stored salary only if it looks like a real salary (has currency symbol, range, or k)
        s = job["_db_salary"]
        if any(c in s for c in "$€£Rp") and ("-" in s or "k" in s.lower() or "Rp" in s):
            job["salary"] = s
    tags = job.get("tags", [])
    if isinstance(tags, list):
        tags = " ".join(tags)
    text = " ".join([
        job.get("title", ""), job.get("company", ""),
        job.get("location", ""), str(tags),
    ]).lower()
    ai = any(k in text for k in AI_KEYWORDS)
    swe = any(k in text for k in SOFTWARE_KEYWORDS)
    it = ai or swe or any(k in text for k in OTHER_IT_KEYWORDS)
    remote = any(k in text for k in REMOTE_WORDS) or bool(job.get("remote"))
    id_city = next((c for c in ID_CITIES if c in text), None)
    # job type: intern / contract / part-time / full-time (default)
    jt = ("intern" if any(k in text for k in ["intern", "magang", "trainee", "internship"])
          else "contract" if any(k in text for k in ["contract", "kontrak", "freelance", "project-based"])
          else "part" if any(k in text for k in ["part-time", "paruh waktu"])
          else "full")
    # is_foreign: by source + location. Foreign sources (arbeitnow/remotive/etc)
    # are foreign unless an ID city is mentioned. Remote doesn't make it local.
    foreign = (not id_city) and "indonesia" not in text and "jakarta" not in text
    # Glints only lists Indonesia jobs; a blank location there is real Indonesian, not foreign
    if job.get("source") == "glints" and not id_city:
        foreign = False
    job["is_it"] = it
    job["role"] = "AI" if ai else ("SWE" if swe else ("IT" if it else "other"))
    # industry detection: TITLE has priority. If title clearly says tech,
    # it's Teknologi regardless of desc keywords (fixes "AI Engineer" tagged Marketing).
    title_l = (job.get("title") or "").lower()
    TECH_TITLE = ["software engineer", "software", "developer", "programmer", "data engineer", "data scientist",
                  "data analyst", "data entry", "data", "ai ", "artificial intelligence", "machine learning", "ml ",
                  "devops", "backend", "frontend", "fullstack", "full-stack", "sre", "platform engineer",
                  "infrastructure", "cloud engineer", "cloud", "network engineer", "sysadmin", "system administrator",
                  "qa engineer", "qa ", "test engineer", "automation engineer", "automation",
                  "security engineer", "cybersecurity", "it support", "it specialist", "it ", "helpdesk",
                  "software architect", "tech lead", "technical", "product engineer", "site reliability"]
    industry = "Teknologi" if any(k in title_l for k in TECH_TITLE) else None
    # else: match from title+desc (non-tech industries)
    if industry is None:
        ind_text = " ".join([title_l, (job.get("description") or "").lower(), (job.get("company") or "").lower()])
        for ind_name, kws in INDUSTRY_KEYWORDS:
            if any(k in ind_text for k in kws):
                industry = ind_name
                break
        industry = industry or "Lainnya"
    job["industry"] = industry
    job["remote_ok"] = remote
    job["id_city"] = id_city
    job["job_type"] = jt
    job["is_foreign"] = foreign
    return job


def filter_jobs(jobs: list[dict], keep_it_only: bool = False) -> list[dict]:
    out = [classify(j) for j in jobs]
    if keep_it_only:
        out = [j for j in out if j["is_it"]]
    return out