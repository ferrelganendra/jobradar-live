# JobRadar — Design Specification (AUTHORITATIVE)

Pelaksana (OpenCode) WAJIB mengikuti spec ini persis. Desainer (agent utama) sudah menetapkan palet dari portfolio milik user. Jangan "memperbaiki" atau "menambah" gaya sendiri.

## 1. Source of truth (baca dulu)
Palet diambil dari `/Users/ferrelganendra/Portfolio/styles/global.css:root`. Ikuti nilai persis.

## 2. Design tokens (WAJIB dipakai, bukan nekat)

```css
:root {
  color-scheme: light;
  --bg: #E5E4E2;            /* abu-abu hangat, TERANG — bukan dark */
  --bg-soft: #F1F0EE;
  --ink: #0A0A0A;           /* hampir hitam */
  --muted: rgba(10, 10, 10, 0.72);
  --faint: rgba(10, 10, 10, 0.65);
  --line: rgba(10, 10, 10, 0.12);        /* border tipis */
  --line-strong: rgba(10, 10, 10, 0.22); /* border tegas */
  --surface: rgba(255, 255, 255, 0.75);  /* kartu semi-transparan */
  --surface-strong: #ffffff;
  --accent: #3f5666;        /* biru-abu kalem — AKAR DESAIN */
  --accent-bright: #8ca3b5;
  --radius: 12px;
  --shadow: 0 24px 60px rgba(10, 10, 10, 0.08);
}
```

Font:
- **Heading**: `Clash Display` (font-weight 500-700, `letter-spacing: -0.04em`). Local `@font-face` dari `/fonts/clash-display-*.woff2` — SALIN file font-nya ke `web/fonts/`.
- **Body**: `Inter`, system-ui, sans-serif.

## 3. Prinsip (NON-NEGOTIABLE)
- **TERANG**. `--bg: #E5E4E2` di latar. JANGAN dark, JANGAN gelap, JANGAN glow.
- **FLAT**. No gradient membara, no backdrop-blur yang mencolok, no shadow drama. Shadow cuma `--shadow` sekali di kartu.
- **TENANG / RESTRAINED**. Ini anti-AI-slop. Tidak ada:
  - ❌ emoji di UI (💰, 🤖, dll) — HAPUS
  - ❌ badge/pill warna-warni mencolok (hijau/ungu/merah) — role jadi teks
  - ❌ gradient button
  - ❌ rounded-3xl / radius besar
  - ❌ blur panel
  - ❌ shadow-2xl
  - ❌ trust bar / "kebanggaan" / hero overlay
- **TIPOGRAFIS / EDITORIAL**. Micro-label uppercase (`font-size: .62-.74rem; letter-spacing: .16em; font-weight: 700; text-transform: uppercase; color: var(--muted)`). Judul Clash Display besar italic-free, letter-spacing -0.04em.
- **Border tipis** `var(--line)` / `var(--line-strong)` sebagai pemisah, bukan shadow.

## 4. Layout
- **Header top**: brand "JobRadar" (Clash Display, weight 700) kiri; kanan micro-label "LIVE · 499 lowongan" (uppercase, tabular-nums). Border-bottom 1px `var(--line)`.
- **Grid 2 kolom**: sidebar filter (left, `--bg-soft`, border-right `--line`) + daftar kartu (right, bg `--bg`).
  Sidebar sticky, `width: 280px`.
- **Responsive**: mobile → sidebar jadi drawer (slide-in, fixed), header menu button.
- **Footer**: sekali, micro-label, perihal data & sumber.

## 5. Kartu job
- `background: var(--surface)`; `border: 1px solid var(--line)`; `border-radius: var(--radius)`; transition border-color/background.
- **ℹ️ Role BUKAN badge warna.** Role (AI/SWE/IT/other) tampil sebagai **micro-label** di atas judul: `font-size: .68rem; letter-spacing: .12em; text-transform: uppercase; color: var(--accent);`. Emoji dilarang.
- **Judul**: Clash Display, weight 600, `font-size: 1.05rem`, `letter-spacing: -0.02em`, `color: var(--ink)`. Max 2 baris.
- **Baris meta** (perusahaan · lokasi): `color: var(--muted)`, body font, `font-size: .88rem`. Pemisah `·`.
- **Gaji**: body font, `font-weight: 600`, `color: var(--ink)`, `font-variant-numeric: tabular-nums`. TANPA emoji 💰. Kalau kosong → SISIPKAN label "gaji tak dicantumkan" `color: var(--faint)` italic.
- **Deskripsi**: `color: var(--muted)`, `font-size: .85rem`, clamp 2 baris.
- **Tags**: chip border `var(--line-strong)`, `background: transparent`, `font-size: .68rem`, `letter-spacing: .06em`, uppercase. Tanpa emoji.
- **Tombol**: "Lihat & Lamar" → pill `border-radius: 999px`, `background: var(--ink)`, `color: var(--bg)`, `font-weight: 700`, `font-size: .86rem`, hover `background: #fff` + border ink. (sama dgn `.button-primary` di porto)
- **Meta footer kartu**: remote/foreign/tipe → micro-label uppercase `var(--muted)`, dipisah `·`. No colored chip.

## 6. Filter sidebar
- **Judul grup**: micro-label uppercase `var(--faint)`.
- Input search: `background: var(--surface)`, `border: 1px solid var(--line-strong)`, radius 8px, focus border `--accent`.
- Role chips: pill `border: 1px solid var(--line-strong)`, `background: transparent`, uppercase micro (*bukan* pill berwarna). Active: `background: var(--ink)`, `color: var(--bg)`.
- Checkbox: native, `accent-color: var(--accent)`.
- Select: sama dgn input.
- Reset: link/button teks `var(--muted)`, hover `var(--ink)`, underline.

## 7. Empty state
- Tengah, micro-label "TIDAK ADA HASIL" `var(--faint)` + satu kalimat `var(--muted)` + link reset `var(--accent)` underline.

## 8. Fitur (dari app.js yang sudah ada)
- Load `data/jobs.json` via fetch.
- Filter: keyword (title/company/desc/location/tags), role (AI/SWE/IT/other multi), tipe (full/intern/contract/part), remote-only, foreign-only, local-Indonesia, salary-only, source (dropdown), sort (relevance/salary/title).
- Result count live di header.
- Empty state.
- Reset filter.
- Mobile drawer.
- **HAPUS semua emoji** dari tampilan (termasuk 💰 di gaji).

## 9. File
Ganti isi: `web/index.html`, `web/style.css`, `web/app.js`. Data `web/data/jobs.json` JANGAN diubah.

## 10. Verifikasi lu (OpenCode)
Setelah selesai, buka `web/index.html` via `python3 -m http.server` dan pastikan:
- Latar `#E5E4E2` terang
- Tidak ada emoji, tidak ada badge warna mencolok, tidak ada dark
- Role = micro-label accent, bukan badge
- Gaji tanpa 💰
- Filter jalan
Laporkan apa yang kamu test.