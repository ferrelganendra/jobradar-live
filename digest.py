"""Daily target-role digest -> Telegram. Reads web/data/jobs.json, picks AI/DS/DA/MT roles
best matching the user's profile (TF-IDF cosine), sends a compact
top-N list. Idempotent, safe to run on a cron."""
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notifier import send
from filter import classify

ROOT = os.path.dirname(os.path.abspath(__file__))
JOBS = os.path.join(ROOT, "web", "data", "jobs.json")
PROFILE = ("ai engineer machine learning deep learning data scientist data science "
           "data analyst data analytics management trainee graduate trainee nlp "
           "computer vision python pytorch tensorflow llm rag vector database fine-tuning mlops")
TOP_N = 10
DIGEST_ROLES = ("AI", "DS", "DA", "MT")
ROLE_QUOTA = {"AI": 4, "DS": 2, "DA": 2, "MT": 2}

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
            (j.get("location") or ""),
            j.get("tags") if isinstance(j.get("tags"), str) else " ".join(j.get("tags") or []),
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


def pick_digest_jobs(jobs, limit=TOP_N):
    """Pick ranked target jobs while reserving slots for DS, DA, and MT."""
    classified = [classify(dict(j)) for j in jobs]
    candidates = [j for j in classified if j.get("role") in DIGEST_ROLES]
    ranked = rank(candidates)
    by_role = {role: [j for _, j in ranked if j.get("role") == role]
               for role in DIGEST_ROLES}

    picked = []
    for role in DIGEST_ROLES:
        picked.extend(by_role[role][:ROLE_QUOTA[role]])
    if len(picked) < limit:
        picked_ids = {id(j) for j in picked}
        picked.extend(j for _, j in ranked if id(j) not in picked_ids)
    return picked[:limit]


def build_digest():
    jobs = json.load(open(JOBS))
    classified = [classify(dict(j)) for j in jobs]
    candidates = [j for j in classified if j.get("role") in DIGEST_ROLES]
    top = pick_digest_jobs(classified)
    if not top:
        return "Tidak ada lowongan AI/DS/DA/MT cocok hari ini."

    scores = {id(j): score for score, j in rank(top)}
    lines = ["<b>🎯 Radar kerja · {}</b>".format(__import__("datetime").date.today().strftime("%a, %d %b")), ""]
    labels = {"AI": "🤖 AI", "DS": "📊 Data Scientist", "DA": "📈 Data Analyst", "MT": "🎓 Management Trainee"}
    i = 0
    for role in DIGEST_ROLES:
        group = [j for j in top if j.get("role") == role]
        if not group:
            continue
        lines.append(f"<b>{labels[role]}</b>")
        for j in group:
            i += 1
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
            pct = min(99, round(scores.get(id(j), 0) * 100))
            tag_s = (" [" + " · ".join(tags) + "]") if tags else ""
            sal_s = f" · {html.escape(sal, quote=False)}" if sal else ""
            loc_s = f" · {html.escape(loc, quote=False)}" if loc else ""
            lines.append(
                f"{i}. <b>{html.escape(co[:30], quote=False)}</b> — {html.escape(j['title'][:42], quote=False)}\n"
                f"   {pct}% cocok{tag_s}{sal_s}{loc_s} · <a href=\"{html.escape(j['url'], quote=True)}\">buka</a>"
            )
        lines.append("")
    total_new = len(jobs)
    remote = sum(1 for j in classified if j.get("remote_ok"))
    counts = {role: sum(1 for j in candidates if j.get("role") == role) for role in DIGEST_ROLES}
    lines.append(f"<i>Pasar: {total_new} loker · AI {counts['AI']} · DS {counts['DS']} · DA {counts['DA']} · MT {counts['MT']} · {remote} remote</i>")
    return "\n".join(lines)


if __name__ == "__main__":
    text = build_digest()
    ok = send(text, parse_mode="HTML")
    print("digest sent:", ok)
    print(text[:1200])