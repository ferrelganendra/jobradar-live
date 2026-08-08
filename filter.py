"""Keyword filter: AI/ML/SWE target + location + remote + salary mention."""
import re

# Primary target roles (case-insensitive)
AI_KEYWORDS = ["ai engineer", "machine learning", "ml engineer", "deep learning",
               "artificial intelligence", "data scientist", "nlp", "computer vision",
               "llm", "genai", "prompt engineer", "mlops", "ai/ml", "data engineer"]
SOFTWARE_KEYWORDS = ["software engineer", "software developer", "backend engineer",
                     "frontend engineer", "full stack", "fullstack", "devops",
                     "sre", "data engineer", "programmer", "app developer"]
# Indonesia cities (any mention => keep)
ID_CITIES = ["jakarta", "tangsel", "tangerang", "bekasi", "depok", "bandung",
             "surabaya", "yogyakarta", "jogja", "semarang", "malang", "medan",
             "balikpapan", "makassar", "denpasar", "bali", "solo", "batam"]

REMOTE_WORDS = ["remote", "work from home", "wfh", "hybrid", "fully remote"]


def classify(job: dict) -> dict:
    """Return job with added: matched_role, is_target, is_remote, location_hit."""
    tags = job.get("tags", [])
    if isinstance(tags, list):
        tags = " ".join(tags)
    text = " ".join([
        job.get("title", ""), job.get("company", ""),
        job.get("location", ""), str(tags),
    ]).lower()
    ai = any(k in text for k in AI_KEYWORDS)
    swe = any(k in text for k in SOFTWARE_KEYWORDS)
    remote = any(k in text for k in REMOTE_WORDS) or bool(job.get("remote"))
    id_city = next((c for c in ID_CITIES if c in text), None)
    job["is_target"] = ai or swe
    job["role"] = "AI" if ai else ("SWE" if swe else "other")
    job["remote_ok"] = remote
    job["id_city"] = id_city
    return job


def filter_jobs(jobs: list[dict], keep_target_only: bool = False) -> list[dict]:
    out = [classify(j) for j in jobs]
    if keep_target_only:
        out = [j for j in out if j["is_target"]]
    return out