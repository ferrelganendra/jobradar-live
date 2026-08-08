# JOBRADAR — DESIGN SPEC (v2, FRESH — NEW IDENTITY)

Pelaksana (OpenCode) WAJIB ikut persis. Ini konsep baru, BUKAN copy portfolio, BUKAN AI-template.
Konsep: **job market sebagai laporan pasar live + radar**. Hangat, editorial, tenang, tapi teknos.

## KONSEP INTI
Bayangkan "harian pasar tenaga kerja" cetak yang modern: kertas hangat, judul serif editorial besar,
data bernada ticker mono, aksen warna sinyal oranye. New, warm, human, characteristic.
JANGAN dark, JANGAN gradient glow, JANGAN badge warna-warni mencolok, JANGAN emoji.

## 1. DESIGN TOKENS (WAJIB)
```css
:root {
  color-scheme: light;
  /* warm paper — BUKAN abu-abu porto, BUKAN putih murni */
  --paper: #F4F0E9;
  --paper-2: #ECE7DD;        /* kartu / area sidebar lebih dalam */
  --card: #FBF9F5;           /* kartu job — kekuningan hangat */
  --ink: #1A1917;            /* near-black hangat (bukan #0A0A0A dingin) */
  --muted: #6B675F;          /* abu-hangat untuk teks sekunder */
  --faint: #938E84;          /* sangat redup utk micro */
  --line: #D8D2C6;           /* hairline border (hangat) */
  --line-strong: #B9B2A4;
  --accent: #E4572E;         /* vermillion radar — AKAR, energik */
  --accent-deep: #C74622;    /* hover */
  --radius: 6px;             /* sengaja TIPIS, bukan rounded-3xl */
  --shadow: 0 1px 0 rgba(26,25,23,.04), 0 12px 30px rgba(26,25,23,.06);
}
```

Font (Google Fonts CDN — OK karena site online):
- **Display / Judul**: `Fraunces` (serif editorial, weight 500-700, opsional italic) — letter-spacing -0.02em
- **Data / Meta / Label**: `Space Mono` (mono technos) — untuk angka, source, meta, ticker
- **Body**: `Inter` (baca nyaman)

## 2. PRINSIP (NON-OPTIONAL)
- Hangat & terang. Paper bg.
- Tenang editorial: banyak whitespace, typography-led.
- Mono dipakai utk "signal" (angka, meta, ticker, source, tag, label) — bikin teknos.
- Serif dipakai utk judul/perusahaan — bikin manusiawi & berkarakter.
- Border hairline `var(--line)` sebagai pemisah (bukan shadow).
- LARANG KERAS:
  - ❌ dark bg / gelap / glow / gradient membara
  - ❌ badge pill berwarna merah/hijau/ungu mencolok
  - ❌ emoji di UI (💰🤖🔥 dll)
  - ❌ rounded-3xl / radius besar
  - ❌ shadow-2xl
  - ❌ font sans generik doang (Inter sbg body OK, TAPI judul harus Fraunces)

## 3. LAYOUT
1. **LIVE TICKER** (paling atas, satu garis, bg `--ink` teks `--paper`):
   teks mono uppercase berjalan/statis berisi sinyal agregat:
   `● LIVE • {total} LOWONGAN • {remote} REMOTE • {id} INDONESIA • {ai} AI • {sw} SWE • {gaji} DENGAN GAJI • 8 SUMBER {…ticker…}`
   Format mono, spacer `·`. (Kalau scroll animasi terlalu ribet, render statis = tetap OK; jangan paksa animasi spam.)
2. **Header kedua** (transparan di atas paper): brand kiri
   `JOBRADAR` (Fraunces 700, besar, ink) + sub-label mono kecil `LAPORAN PASAR KERJA — INDONESIA + REMOTE`.
   Chapter mono tebal accent kecil: `EDISI {tanggal} · {total} LOWONGAN`.
3. **Grid**: sidebar filter (kiri, `--paper-2`, border-right `--line`) + daftar kartu (kanan, paper).
   Sidebar sticky 280px. Responsive → drawer mobile.
4. **Footer**: hairline top, mono micro, credit data + sumber + "diperbarui otomatis".

## 4. KARTU JOB
- bg `--card`, border 1px `--line`, radius 6px, padding 18-20px. Hover: border `--accent`/`--line-strong`, shadow halus.
- **Perusahaan** = mono micro-label uppercase accent `JOBRADAR`-esque? NO — perusahaan pakai **Fraunces**, ukuran ~1.1rem, ink, kiri atas. Bukan badge.
- **Judul** = Fraunces 600/700, `font-size 1.15rem`, letter-spacing -0.02em, ink, max 2 baris.
- **Role** = mono micro-label UPUPPERCASE, `color: var(--accent)`, `letter-spacing .08em`, `font-size .68rem` — TANPA bg warna, TANPA pill. (AI/SWE/IT/LAIN)
- **Meta baris** = mono, `font-size .72rem`, `color: var(--muted)`, dipisah ` · `: `PERUSAHAAN·LOKASI`. Kalau kosong → `TAK TERCANTUM` faint.
- **Gaji** = mono, weight 700, `color: var(--ink)`, `font-variant-numeric: tabular-nums`. Jika kosong → `gaji tak dicantumkan` italic faint mono .72rem.
- **Deskripsi** = body Inter, `.85rem`, `color: var(--muted)`, clamp 2 baris.
- **Tag** = mono micro `.66rem` `letter-spacing .04em`, border `--line`, bg transparent, uppercase. Tanpa emoji.
- **Footer kartu** = kiri: label mono `.68rem` `--muted` utk remote/tipe (`REMOTE · MAGANG · KONTRAK · LUAR NEGERI`), dipisah `·`. Kanan: tombol.
- **Tombol** "Lihat & Lamar" = bg `--accent`, teks `--paper`, mono? NO — body Inter 700 `.86rem`, radius 6px, padding .7rem 1.1rem. Hover bg `--accent-deep`. Garis oranye, bukan pill ramai.

## 5. SIDEBAR FILTER
- Judul grup: mono micro `.66rem`, `letter-spacing .12em`, uppercase, `--faint`.
- Search: bg `--card`, border `--line-strong`, radius 6px, font Inter .88rem, focus border `--accent`.
- Role chips: mono micro uppercase, border `--line-strong`, bg transparent, radius 999px (pill OK utk chip filter — ini kontrol, bukan kartu). Active → bg `--ink`, teks `--paper`.
- Checkbox: `accent-color: var(--accent)`.
- Select: bg card, border line-strong, Inter.
- Reset: link teks `--muted` hover `--ink`, underline.
- Sidebar heading atas: `FILTER` (Fraunces 600), sub mono `PILIH SINYAL`.

## 6. EMPTY STATE
- Tengah: `TIDAK ADA SINYAL` (Fraunces 600, ink, besar) + satu baris mono faint + link reset accent underline. Jangan genit.

## 7. FITUR (pertahankan dari app.js lama)
Load `data/jobs.json` via fetch. Filter: keyword (title/company/desc/loc/tags), role multiselect (AI/SWE/IT/LAIN), tipe (full/intern/contract/part), remote, foreign, indonesia, salary-only, source dropdown, sort (relevance/salary/title). Result count live. Empty state. Reset. Mobile drawer.
**Hapus SEMUA emoji** dari tampilan (termasuk 💰 di gaji — dihapus; gaji jadi teks biasa).

## 8. FILE
Overwrite `web/index.html`, `web/style.css`, `web/app.js`. JANGAN ubah `web/data/jobs.json`.
Font via Google Fonts CDN `@import` di CSS: Fraunces 500;600;700 + Space Mono 400;700 + Inter 400;600;700.

## 9. VERIFIKASI (OpenCode)
Buka lewat `python3 -m http.server` dari `web/`:
- bg `#F4F0E9` hangat, bukan dark, bukan abu porto
- judul kartu = Fraunces; meta/gaji/tag = Space Mono
- role = mono accent uppercase, tanpa bg/pill
- gaji tanpa emoji
- filter & sort jalan, count live
Laporkan file + hasil.