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
             "balikpapan", "makassar", "denpasar", "bali", "solo", "batam"]

REMOTE_WORDS = ["remote", "work from home", "wfh", "hybrid", "fully remote"]


def classify(job: dict) -> dict:
    """Return job with added: is_it, role (AI/SWE/IT), is_remote, id_city."""
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
    # is_foreign: no ID city mention AND not remote
    foreign = (not id_city) and "indonesia" not in text and "jakarta" not in text and "remote" not in text
    job["is_it"] = it
    job["role"] = "AI" if ai else ("SWE" if swe else ("IT" if it else "other"))
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