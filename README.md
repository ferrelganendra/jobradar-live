# JobRadar — Indonesia Job Aggregator

Aggregator lowongan kerja Indonesia + remote, fokus **AI Engineer / Machine Learning / Software Engineer**. Pipelines: (1) web publik `jobradar-live.pages.dev` tampil semua job + filter/insight, (2) Telegram notif loker IT baru. Scrape 8 sumber → klasifikasi → SQLite → auto-deploy statis.

## Fitur

- **8 sumber** aktif: Remotive, Arbeitnow, RemoteOK, Jobicy, HN, Glints, JobStreet, LinkedIn
- **Auto-deploy** — cron tiap 30 menit scrape → dump → commit → push → Cloudflare Pages
- **Semantic search (TF-IDF)** — vector retrieval client-side, cosine similarity, bobot title 3×. Cari "ml engineer" paham konteks, bukan substring.
- **Preset "Cari cocokku AI Engineer"** — profil vektor AI/ML/DL/DS/NLP/CV/Python, rank job paling cocok, bisa digabung filter lain
- **Insight pasar live** — %remote, %lokal, %ber-gaji, top industri, skill populer
- **Fair industri** — 14 kategori (Teknologi/Marketing/Sales/dll), bukan bias IT; web netral, Telegram cuma IT
- **is_foreign akurat** — by source + lokasi + legal-form PT/CV, remote ≠ lokal
- **Dedup anti-spam** — normalisasi URL + UNIQUE constraint, 0 duplikat
- **SQLite** — riwayat job, ga dobel

## Arsitektur AI (client-side, tanpa backend)

Semuanya gratis & statis — tak ada API LLM berbayar, tak ada server:

1. **TF-IDF vectorization** — semua job di-vectorize di browser (title/company bobot 3×, desc bobot 1×), IDF dari corpus 1800+ job
2. **Cosine similarity** — query dipetakan ke vector, di-rank by relevansi
3. **Preset profil** — query vektor statis AI Engineer, toggle mode
4. **Insight** — agregasi statistik distribusi (industri, remote, skill)

Kenapa client-side: runtime gratis, tanpa biaya API berulang, tanpa index file (jobs.json tak membengkak), reproducable.

## Struktur

```
loker-agg/
├── scraper/
│   ├── base.py            # fetch + retry + UA rotation
│   ├── renderer.py        # Playwright SPA renderer (Glints)
│   ├── api/               # remotive, arbeitnow, remoteok, jobicy, hn
│   └── html/              # glints, jobstreet, linkedin (playwright)
├── filter.py              # klasifikasi role/industri/foreign/remote/salary
├── db.py                  # SQLite + dedup + backfill
├── notifier.py            # Telegram broadcast multi-chat
├── main.py                # orchestrator + auto-commit
├── web/                   # static frontend (index.html / app.js / style.css)
│   └── data/jobs.json     # full dataset (dibuat ulang tiap scrape)
└── out/jobs.json          # latest dump
```

## Setup

```bash
cd loker-agg
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install playwright && playwright install chromium
cp .env.example .env   # isi TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
python main.py
```

## Catatan sumber

- **API legal**: Remotive, Arbeitnow, RemoteOK, Jobicy, HN — 0 risiko
- **Scrape abu-abu**: Glints, JobStreet, LinkedIn (listing accessible, playwright)
- **Skip**: Kalibrr (login-wall), WWR (selector rusak), Indeed (Cloudflare anti-bot)

## Catatan teknis

- Python 3.9.6 — pakai `Optional`, bukan `X | None`
- Semua command wajib `env -u PYTHONPATH` (Hermes injek PYTHONPATH → rusak urllib3)
- Push via SSH (9router MITM block git HTTPS)