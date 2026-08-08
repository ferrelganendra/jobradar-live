# Loker Scraper — Indonesia Job Aggregator

Aggregator lowongan kerja Indonesia + remote, fokus **AI Engineer / Machine Learning / Software Engineer**. Scrape dari 6 sumber, filter keyword, dedup, simpan ke SQLite, notif job baru ke Telegram.

## Fitur

- **8 sumber** aktif: Remotive, Arbeitnow, RemoteOK, Jobicy, HN Who's Hiring, Glints, JobStreet, LinkedIn (playwright)
- **Detail lengkap** — deskripsi penuh, gaji (Rp regex), lokasi utk job baru (backfill utk backlog)
- **Filter target** — klasifikasi otomatis per job: `role` (AI / SWE / IT / other), `remote_ok`, `id_city`
- **Notif semua IT** — Telegram kirim semua loker IT baru, ditanda role (🤖 AI / 💻 SWE / 🖥 IT)
- **Dedup anti-spam** — normalisasi URL (strip query param) + UNIQUE constraint
- **SQLite** — riwayat job, ga dobel
- **Scheduling** — cron Hermes tiap 30 menit

## Struktur

```
loker-agg/
├── scraper/
│   ├── base.py            # fetch + UA rotation + retry/backoff
│   ├── renderer.py        # Playwright SPA renderer (Glints)
│   ├── api/               # API legal: remotive, arbeitnow, remoteok, jobicy, hn
│   └── html/              # HTML: glints, jobstreet, linkedin (playwright), wwr (broken)
├── filter.py              # keyword classifier AI/SWE/remote/kota
├── db.py                  # SQLite + dedup
├── notifier.py            # Telegram send
├── backfill.py            # one-off: isi detail utk job backlog
├── main.py                # orchestrator
├── run.sh                 # clean-PYTHONPATH wrapper (cron)
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
- **Scrape abu-abu**: Glints, JobStreet, LinkedIn (listing accessible, butuh playwright; LinkedIn = guest, tanpa login)
- **Skip**: Kalibrr (login-wall), WWR (selector rusak), Indeed (Cloudflare anti-bot, butuh CF-solver)

## Roadmap

- [x] M0–M3: API legal + Glints + filter + SQLite + dedup
- [x] M4: notif Telegram + cron
- [x] M5: JobStreet + detail lengkap (deskripsi/gaji/lokasi)
- [x] M6: LinkedIn (guest) + filter IT broad (semua loker IT, role AI/SWE/IT)
- [ ] Layer AI: LLM extract gaji/lokasi + job match ke profil
- [ ] Indeed via Cloudflare-solver (flaky, maintenance tinggi)