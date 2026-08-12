# JobRadar — Indonesia Job Aggregator

Aggregator lowongan kerja **Indonesia + remote-foreign**, fokus AI Engineer / Machine Learning. Satu pipeline, tiga output: (1) web publik `jobradar-live.pages.dev` — semua job + filter + insight, (2) Telegram notif loker IT baru real-time, (3) daily AI-match digest pagi. Scrape 8 sumber → klasifikasi → SQLite → prune → auto-deploy statis. **100% gratis dijalankan** (zero paid API, zero server, Cloudflare Pages).

## Fitur

**Pipeline & data**
- **8 sumber aktif**: Remotive, Arbeitnow, RemoteOK, Jobicy, HN, Glints, JobStreet, LinkedIn
- **Auto-deploy** — cron tiap 30 menit: scrape → klasifikasi → SQLite → dump → commit → push → Cloudflare Pages
- **Prune otomatis** — lowongan foreign non-remote dihapus (ia hanya mau luar negeri kalau remote); Indonesia full
- **Soft-dedup** — `(source, title, company)` sama → simpan yang terbaru, buang yang lama (kejar re-post arbeitnow)
- **SQLite** — riwayat, dedup URL via UNIQUE constraint
- **is_foreign akurat** — by source + lokasi + legal-form PT/CV, remote ≠ lokal

**Web (static, client-side)**
- **Semantic search (TF-IDF)** — vector retrieval di browser, cosine similarity, bobot title 3×. "ml engineer" paham konteks, bukan substring. $0 runtime, tanpa index file.
- **Preset "Cari cocokku AI Engineer"** — profil vektor AI/ML/DL/DS/NLP/CV/Python, rank job + **% cocok**, bisa digabung filter lain
- **Bookmark** — simpan lowongan (localStorage), filter "Tersimpan"
- **Detail modal** — klik kartu → deskripsi penuh, gaji, tags, relatif waktu
- **Filter lengkap** — industri (14 kategori fair, bukan bias IT), tipe, lokasi (Remote/Luar/Indonesia), **kota Indonesia** (Jakarta/Bandung/Yogyakarta/dst), gaji, sumber, **freshness** (24h/7d/30d)
- **Insight pasar live** — %remote, %lokal, %ber-gaji, top industri, skill populer
- **Auto-refresh** — silent re-fetch tiap 5 menit, notif "Ada N lowongan baru"
- **RSS feed** — `data/feed.xml`, 50 item, XML valid, custom `<job:*>` namespace (remote/salary/location/company)
- **Self-host font** — Inter, Playfair, Superior Mono (semua woff2 lokal, 0 request CDN)

**Telegram**
- **Notif IT baru real-time** — grouped by role (AI/SWE/IT), remote/foreign/magang tag, gaji
- **Daily AI-match digest (07:00)** — TF-IDF rank AI/ML job vs profil user, kirim top-10 + % cocok + gaji + lokasi

## Arsitektur AI (client-side, tanpa backend)

Semuanya gratis & statis — tak ada API LLM berbayar, tak ada server:

1. **TF-IDF vectorization** — semua job di-vectorize di browser (title/company bobot 3×, desc 1×), IDF dari corpus
2. **Cosine similarity** — query dipetakan ke vector, di-rank by relevansi
3. **Preset profil** — query vektor statis AI Engineer, toggle mode
4. **Insight** — agregasi statistik distribusi (industri, remote, skill)
5. **Digest** — TF-IDF yang sama di Python (`digest.py`) untuk daily Telegram

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
├── db.py                  # SQLite + dedup + prune + backfill
├── feed.py                # RSS 2.0 generator (stdlib only)
├── digest.py              # daily AI-match digest (TF-IDF) -> Telegram
├── notifier.py            # Telegram broadcast multi-chat
├── main.py                # orchestrator + auto-commit (jobs.json + feed.xml)
├── web/                   # static frontend (index.html / app.js / style.css / fonts/)
│   ├── data/jobs.json     # full dataset (dibuat ulang tiap scrape)
│   └── data/feed.xml      # RSS feed
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
- E2E: `cd web && env -u PYTHONPATH ../.venv/bin/python3 e2e_test.py` (Playwright, 20+ checks)