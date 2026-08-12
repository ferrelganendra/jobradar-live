"""Daily AI-match digest -> Telegram. Reads web/data/jobs.json, picks AI/ML roles
best matching the user's AI-Engineer profile (TF-IDF cosine), sends a compact
top-N list. Idempotent, safe to run on a cron."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notifier import send

ROOT = os.path.dirname(os.path.abspath(__file__))
JOBS = os.path.join(ROOT, "web", "data", "jobs.json")
PROFILE = ("ai engineer machine learning deep learning data scientist nlp computer vision "
           "python pytorch tensorflow llm rag vector database fine-tuning mlops")
TOP_N = 10

_STOP = set("yang dan di ke dari untuk dengan pada ini itu atau tidak juga sudah the a an of to in for on and or is are be at by as it its we you our job jobs role company work team".split())


def _tok(s):
    return [w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 1 and w not in _STOP]


def _clean(h):
    # strip HTML tags + JS whitespace
    t = re.sub(r"<[^>]+>", " ", h or "")
    return " ".join(t.split())


def rank(jobs):
    """TF-IDF cosine of each job's text vs PROFILE. Returns list of (score, job)."""
    docs = []
    for j in jobs:
        text = " ".join([
            (j.get("title") or "") + " " + (j.get("company") or ""),
            _clean(j.get("description") or ""),
            (j.get("location") or ""), " ".join(j.get("tags") or []),
        ])
        docs.append(_tok(text))
    # df
    df = {}
    for toks in docs:
        for w in set(toks):
            df[w] = df.get(w, 0) + 1
    n = max(1, len(docs))
    idf = {w: __import__("math").log(1 + n / c) for w, c in df.items()}
    # query vector
    qt = _tok(PROFILE)
    qf = {}
    for w in qt:
        qf[w] = qf.get(w, 0) + 1
    qv = {w: (c / max(1, len(qf))) * idf.get(w, 0) for w, c in qf.items()}
    qn = __import__("math").sqrt(sum(v * v for v in qv.values())) or 1
    qv = {w: v / qn for w, v in qv.items()}
    # job vectors + cosine
    scored = []
    for j, toks in zip(jobs, docs):
        tf = {}
        for w in toks:
            tf[w] = tf.get(w, 0) + 1
        v = {w: (c / max(1, len(toks))) * idf.get(w, 0) for w, c in tf.items()}
        norm = __import__("math").sqrt(sum(x * x for x in v.values())) or 1
        cos = sum(qv.get(w, 0) * (val / norm) for w, val in v.items())
        # title boost
        title_toks = _tok(j.get("title") or "")
        for w in title_toks:
            if w in qv:
                cos += qv[w] * 0.5
        scored.append((cos, j))
    scored.sort(key=lambda x: -x[0])
    return scored


def build_digest():
    jobs = json.load(open(JOBS))
    # candidate pool: AI-role OR it, prefer remote/ID, with salary
    def is_ai(j):
        return (j.get("role") == "AI" or
                any(k in (j.get("title") or "").lower() for k in
                    ["ai ", "machine learning", "ml ", "data scientist", "deep learning",
                     "nlp", "computer vision", "llm", "prompt", "mlops"]))

    candidates = [j for j in jobs if is_ai(j)]
    if not candidates:
        return "Tidak ada lowongan AI cocok hari ini."

    scored = rank(candidates)
    top = scored[:TOP_N]

    lines = ["<b>🎯 Radar AI · {}</b>".format(__import__("datetime").date.today().strftime("%a, %d %b")), ""]
    for i, (s, j) in enumerate(top, 1):
        tags = []
        if j.get("remote_ok"):
            tags.append("Remote")
        elif j.get("is_foreign"):
            tags.append("Luar")
        if j.get("job_type") == "intern":
            tags.append("Magang")
        elif j.get("job_type") == "contract":
            tags.append("Kontrak")
        loc = (j.get("location") or "").strip()
        sal = (j.get("salary") or "").strip()
        co = (j.get("company") or "").strip() or (j.get("title") or "").strip()
        pct = min(99, round(s * 100))
        tag_s = (" [" + " · ".join(tags) + "]") if tags else ""
        sal_s = f" · {sal}" if sal else ""
        loc_s = f" · {loc}" if loc else ""
        lines.append(
            f"{i}. <b>{co[:30]}</b> — {j['title'][:42]}\n"
            f"   {pct}% cocok{tag_s}{sal_s}{loc_s} · <a href=\"{j['url']}\">buka</a>"
        )
    # footer: market snapshot
    total_new = len(jobs)
    ai_n = len(candidates)
    remote = sum(1 for j in jobs if j.get("remote_ok"))
    lines += ["", f"<i>Pasar: {total_new} loker · {ai_n} AI · {remote} remote</i>"]
    return "\n".join(lines)


if __name__ == "__main__":
    text = build_digest()
    ok = send(text, parse_mode="HTML")
    print("digest sent:", ok)
    print(text[:1200])