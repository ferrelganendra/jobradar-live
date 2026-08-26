import sys
from collections import Counter

sys.path.insert(0, ".")

from digest import pick_digest_jobs
from filter import classify


def job(title):
    return {
        "title": title,
        "company": "PT Contoh",
        "location": "Jakarta",
        "source": "glints",
        "url": "https://example.com/" + title.lower().replace(" ", "-"),
    }


mt = classify(job("Management Trainee Program"))
assert mt["role"] == "MT"
assert mt["job_type"] == "full"
assert classify(job("Data Scientist"))["role"] == "DS"
assert classify(job("Data Analyst"))["role"] == "DA"
assert classify(job("Store Manager Mt Barker"))["role"] != "MT"

picked = pick_digest_jobs([
    job("AI Engineer") for _ in range(8)
] + [job("Data Scientist") for _ in range(4)] + [job("Data Analyst") for _ in range(4)] + [job("Management Trainee") for _ in range(4)])
counts = Counter(j["role"] for j in picked)
assert counts["AI"] <= 4
assert counts["DS"] >= 1
assert counts["DA"] >= 1
assert counts["MT"] >= 1
print("PASS telegram role coverage", dict(counts))
