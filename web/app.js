"use strict";

const state = {
  jobs: [],
  q: "",
  roles: new Set(),
  types: new Set(),
  remote: false,
  foreign: false,
  local: false,
  city: "",
  salaryOnly: false,
  freshHours: 0,
  source: "",
  sort: "recent",
  presetAI: false,
  bookmarksOnly: false,
  page: 1,
  perPage: 24,
};

const $ = (id) => document.getElementById(id);
const AI_PROFILE = "ai engineer machine learning deep learning data scientist nlp computer vision python";
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const EMOJI_RE = /[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2190}-\u{21FF}\u{FE0F}]/gu;
const deEmoji = (s) => String(s ?? "").replace(EMOJI_RE, "");

const TYPE_LABEL = { full: "Full-time", intern: "Magang", contract: "Kontrak", part: "Part-time" };

/* ---- bookmarks (localStorage, keyed by url) ---- */
const BK_KEY = "jobradar.bookmarks";
let bookmarks = new Set();
function loadBookmarks() {
  try { bookmarks = new Set(JSON.parse(localStorage.getItem(BK_KEY) || "[]")); } catch { bookmarks = new Set(); }
}
function saveBookmarks() { localStorage.setItem(BK_KEY, JSON.stringify([...bookmarks])); updateBkCount(); }
function toggleBookmark(url) {
  bookmarks.has(url) ? bookmarks.delete(url) : bookmarks.add(url);
  saveBookmarks();
  render();
}
function updateBkCount() {
  const b = $("presetBookmarks");
  if (b) b.textContent = "Tersimpan (" + bookmarks.size + ")";
}
function isRecent(j) {
  if (!state.freshHours || !j.created_at) return true;
  const t = Date.parse(String(j.created_at).replace(" ", "T") + "Z");
  if (isNaN(t)) return true;
  return (Date.now() - t) <= state.freshHours * 3600e3;
}

function stripHtml(h) {
  if (!h) return "";
  // Data arrives doubly-encoded (&lt;p&gt;); decode HTML entities first so innerHTML parses as markup.
  const d = document.createElement("div");
  const dec = document.createElement("textarea");
  dec.innerHTML = h; // textarea parse: HTML entities become their characters
  d.innerHTML = dec.value;
  return (d.textContent || "").replace(/\s+/g, " ").trim();
}

/* Cut scraped descriptions at common footer/marketing noise. */
const DESC_CUT = [
  "Tentang Perusahaan", "About the Company", "Lihat Lebih Banyak", "Lamar Sekarang",
  "Tips Aman Cari Kerja", "Loker ini dikelola", "Dapatkan notifikasi loker",
  "Lowongan Lainnya Untukmu", "Scan kode QR", "Galeri Perusahaan", "Why join us",
  "Perusahaan Premium", "Laporkan Lowongan Ini", "Apply now", "Share this job",
  "Interview process", "About Us", "About us", "Beware of scammers", "Gaji dan benefit",
];
function cleanDesc(s) {
  if (!s) return "";
  let t = s;
  for (const k of DESC_CUT) {
    const idx = t.indexOf(k);
    if (idx > 0) t = t.slice(0, idx);
  }
  t = t.replace(/—/g, " · ").replace(/\s+/g, " ").trim();
  // first 200 chars of real substance after title/company echo
  const words = t.split(" ");
  return words.slice(0, 60).join(" ");
}

async function load() {
  loadBookmarks();
  updateBkCount();
  try {
    const res = await fetch("data/jobs.json");
    if (!res.ok) throw new Error("HTTP " + res.status);
    state.jobs = await res.json();
  } catch (e) {
    $("resultText").textContent = "Gagal memuat data: " + e.message;
    return;
  }
  const sources = [...new Set(state.jobs.map((j) => j.source))].sort();
  const sel = $("fSource");
  sources.forEach((s) => {
    const o = document.createElement("option");
    o.value = s;
    o.textContent = s;
    sel.appendChild(o);
  });
  // city dropdown from id_city (present only on ID jobs; sort by count desc)
  const cityCount = {};
  state.jobs.forEach((j) => { if (j.id_city) cityCount[j.id_city] = (cityCount[j.id_city] || 0) + 1; });
  const citySel = $("fCity");
  Object.entries(cityCount).filter(([, c]) => c >= 2).sort((a, b) => b[1] - a[1])
    .forEach(([city]) => {
      const o = document.createElement("option");
      o.value = city;
      o.textContent = city.charAt(0).toUpperCase() + city.slice(1) + " (" + cityCount[city] + ")";
      citySel.appendChild(o);
    });
  $("totalCount").textContent = state.jobs.length;
  buildIndustryChips();
  updateSignals();
  buildInsight();
  render();}

function matches(j) {
  const t = (j.title + " " + j.company + " " + j.location + " " + (j.description || "") + " " + (j.tags || []).join(" ")).toLowerCase();

  if (state.roles.size && !state.roles.has(j.industry)) return false;
  if (state.types.size && !state.types.has(j.job_type)) return false;
  if (state.remote && !j.remote_ok) return false;
  if (state.foreign && !j.is_foreign) return false;
  if (state.local && j.is_foreign) return false;
  if (state.city && !(j.id_city === state.city)) return false;
  if (state.salaryOnly && !j.salary) return false;
  if (!isRecent(j)) return false;
  if (state.bookmarksOnly && !bookmarks.has(j.url)) return false;
  if (state.source && j.source !== state.source) return false;
  return true;
}

function salaryNum(j) {
  // parse "Rp 6-8jt" / "USD 80k" / "$50,000" → numeric for sorting
  const s = (j.salary || "").replace(/\s/g, "").toLowerCase();
  let m = s.match(/(\d[\d.,]*)(?:jt|juta|j|m|k|rb|ribu)?/);
  if (!m) return null;
  let raw = m[1];
  // "7,2" → 7.2 (desimal koma); "50,000" → 50000 (ribuan titik/koma)
  const parts = raw.split(/[.,]/);
  let n;
  if (parts.length === 2 && parts[1].length <= 2) n = parseFloat(parts.join(".")); // 7,2 → 7.2
  else n = parseFloat(raw.replace(/[.,]/g, "")); // 50,000 → 50000
  if (!isFinite(n)) return null;
  if (s.includes("jt") || s.includes("juta") || s.includes(" j")) n *= 1e6;
  else if (s.includes("rb") || s.includes("ribu")) n *= 1e3;
  else if (s.includes("k")) n *= 1e3;
  else if (s.includes("m")) n *= 1e6;
  return n;
}

function score(j) {
  // "recent" default: newest first (created_at desc). Stable no-op for others.
  const t = Date.parse(String(j.created_at || "").replace(" ", "T") + "Z");
  return isNaN(t) ? 0 : t;
}

/* ---- TF-IDF vector search (client-side, no index file) ---- */
const _STOP = new Set("yang dan di ke dari untuk dengan pada ini itu atau tidak juga sudah the a an of to in for on and or is are be at by as it its we you our job jobs role company work team".split(" "));
let _df = null, _jobVec = null;
function _tok(s) { return (String(s || "").toLowerCase().match(/[a-z0-9]+/g) || []).filter((w) => w.length > 1 && !_STOP.has(w)); }
function buildIndex() {
  const df = {};
  const vecs = [];
  for (const jb of state.jobs) {
    const titleToks = _tok(jb.title + " " + jb.company);
    const bodyToks = _tok(jb.location + " " + (jb.description || "") + " " + (jb.tags || []).join(" "));
    // count tf with title flag
    const tf = {};
    for (const seq of [titleToks, bodyToks]) for (const w of seq) tf[w] = (tf[w] || 0) + 1;
    const seen = {};
    for (const w of titleToks) if (!seen[w]) { seen[w] = 1; df[w] = (df[w] || 0) + 1; }
    for (const w of bodyToks) if (!seen[w]) { seen[w] = 1; df[w] = (df[w] || 0) + 1; }
    const titleSet = new Set(titleToks);
    vecs.push({ tf, n: Object.keys(tf).length, title: titleSet });
  }
  const n = Math.max(1, state.jobs.length);
  const idf = {};
  for (const w in df) idf[w] = Math.log(1 + n / df[w]);
  _jobVec = vecs.map(({ tf, n: ntok, title }) => {
    const v = {};
    for (const w in tf) v[w] = (tf[w] / Math.max(1, ntok)) * idf[w] * (title.has(w) ? 3 : 1);
    let norm = 0; for (const w in v) norm += v[w] * v[w];
    norm = Math.sqrt(norm) || 1;
    for (const w in v) v[w] /= norm;
    return v;
  });
  _df = { idf, n };
}
function cosine(a, b) {
  let d = 0; for (const w in a) if (b[w]) d += a[w] * b[w]; return d;
}
let _scores = null;
function searchRank(list) {
  if (!_df) buildIndex();
  const query = state.q || AI_PROFILE;
  const qtf = {};
  for (const w of _tok(query)) qtf[w] = (qtf[w] || 0) + 1;
  const qv = {};
  for (const w in qtf) if (_df.idf[w]) qv[w] = (qtf[w] / Math.max(1, Object.keys(qtf).length)) * _df.idf[w];
  let qn = 0; for (const w in qv) qn += qv[w] * qv[w];
  qn = Math.sqrt(qn) || 1;
  for (const w in qv) qv[w] /= qn;
  if (!Object.keys(qv).length) return list;
  // map each job to its precomputed vector by reference
  const vecById = new Map();
  state.jobs.forEach((j, i) => vecById.set(j, _jobVec[i]));
  const scored = list.map((j) => ({ j, s: cosine(qv, vecById.get(j) || {}) }))
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s);
  _scores = new Map();
  scored.forEach((x) => _scores.set(x.j, x.s));
  return scored.map((x) => x.j);
}

function render() {
  const list = state.jobs.filter(matches);
  if (state.presetAI) searchRank(list); // populate _scores for match badges
  if (state.sort === "title") {
    list.sort((a, b) => (a.title || "").localeCompare(b.title || "", "id"));
  } else if (state.sort === "salary") {
    list.sort((a, b) => (salaryNum(b) || 0) - (salaryNum(a) || 0));
  } else if (state.q || state.presetAI) {
    // semantic relevance ranking (free query or AI profile preset)
    const ranked = searchRank(list);
    list.length = 0; list.push(...ranked);
  } else {
    list.sort((a, b) => score(b) - score(a));
  }

  const total = list.length;
  const pages = Math.max(1, Math.ceil(total / state.perPage));
  if (state.page > pages) state.page = pages;
  if (state.page < 1) state.page = 1;
  const slice = list.slice((state.page - 1) * state.perPage, state.page * state.perPage);

  $("resultText").textContent = `Menampilkan ${slice.length} dari ${total} lowongan`;
  const wrap = $("cards");
  const tpl = $("cardTpl");
  wrap.innerHTML = "";

  if (total === 0) {
    $("empty").hidden = false;
    $("pager").hidden = true;
    return;
  }
  $("empty").hidden = true;

  for (const [i, j] of slice.entries()) {
    const n = tpl.content.cloneNode(true);
    const card = n.firstElementChild;
    card.style.animationDelay = Math.min(i * 18, 350) + "ms";
    n.querySelector(".role-label").textContent = j.industry || "Lainnya";
    n.querySelector(".card-source").textContent = j.source;
    n.querySelector(".card-title").textContent = deEmoji(j.title).replace(/—/g, " · ");
    const coEl = n.querySelector(".meta-company");
    const co = j.company?.trim();
    if (co) {
      coEl.textContent = deEmoji(co).replace(/\bPt\.?\s/g, "PT ").replace(/\bpt\.?\s/g, "PT ");
    } else {
      coEl.remove(); /* no company → skip the line, title stands alone */
    }
    const locRaw = deEmoji(j.location || "");
    const locEl = n.querySelector(".meta-loc");
    if (locRaw.trim()) {
      locEl.textContent = locRaw.trim();
    } else {
      locEl.remove(); /* no location → skip the line */
    }

    const sal = n.querySelector(".salary-row");
    if (j.salary) {
      sal.textContent = deEmoji(j.salary);
    } else {
      sal.classList.add("none");
      sal.textContent = "gaji tak dicantumkan";
    }

    const matchEl = n.querySelector(".match-row");
    if (state.presetAI && _scores && _scores.has(j)) {
      const s = _scores.get(j);
      const pct = Math.min(99, Math.round(s * 100));
      matchEl.hidden = false;
      matchEl.textContent = "Cocok " + pct + "% profil AI Engineer";
    } else {
      matchEl.remove();
    }

    const desc = cleanDesc(deEmoji(stripHtml(j.description)));
    const dEl = n.querySelector(".card-desc");
    if (desc) dEl.textContent = desc; else dEl.remove();

    const tagWrap = n.querySelector(".card-tags");
    (j.tags || []).slice(0, 5).forEach((t) => {
      const s = document.createElement("span");
      s.className = "tag";
      s.textContent = deEmoji(t);
      tagWrap.appendChild(s);
    });
    if (!(j.tags || []).length) tagWrap.remove();

    const btn = n.querySelector(".btn-apply");
    btn.href = j.url || "#";
    btn.textContent = "Buka lowongan";

    const bk = n.querySelector(".btn-bookmark");
    const saved = bookmarks.has(j.url);
    bk.setAttribute("aria-pressed", String(saved));
    bk.textContent = saved ? "Tersimpan" : "Simpan";
    bk.addEventListener("click", () => toggleBookmark(j.url));
    card.addEventListener("click", (e) => {
      if (e.target.closest("a") || e.target.closest("button")) return;
      openModal(j);
    });

    const chips = n.querySelector(".card-meta-chip");
    if (j.remote_ok) {
      chips.appendChild(Object.assign(document.createElement("span"), { textContent: "Remote" }));
    } else if (j.is_foreign) {
      chips.appendChild(Object.assign(document.createElement("span"), { textContent: "Luar negeri" }));
    }
    if (j.job_type && j.job_type !== "full") {
      chips.appendChild(Object.assign(document.createElement("span"), { textContent: TYPE_LABEL[j.job_type] || j.job_type }));
    }
    if (!chips.children.length) chips.remove();

    wrap.appendChild(n);
  }
  renderPager(total, pages);
}

function renderPager(total, pages) {
  const el = $("pager");
  if (!el) return;
  el.hidden = total === 0;
  const info = el.querySelector(".pager-info");
  if (info) info.textContent = `Halaman ${state.page} dari ${pages}`;
  const prev = el.querySelector(".pg-prev");
  const next = el.querySelector(".pg-next");
  if (prev) prev.disabled = state.page <= 1;
  if (next) next.disabled = state.page >= pages;
  // number buttons
  let nums = el.querySelector(".pg-nums");
  if (!nums) { nums = document.createElement("div"); nums.className = "pg-nums"; el.querySelector(".pg-nav") ? el.querySelector(".pg-nav").after(nums) : el.appendChild(nums); }
  nums.innerHTML = "";
  if (pages <= 1) return;
  const win = 2;
  const lo = Math.max(1, state.page - win), hi = Math.min(pages, state.page + win);
  const add = (p, label) => {
    const b = document.createElement("button"); b.type = "button"; b.className = "pg-num" + (p === state.page ? " active" : "");
    b.textContent = label; b.addEventListener("click", () => goPage(p)); nums.appendChild(b);
  };
  if (lo > 1) add(1, "1");
  if (lo > 2) { const e = document.createElement("span"); e.className = "pg-ell"; e.textContent = "…"; nums.appendChild(e); }
  for (let p = lo; p <= hi; p++) add(p, String(p));
  if (hi < pages - 1) { const e = document.createElement("span"); e.className = "pg-ell"; e.textContent = "…"; nums.appendChild(e); }
  if (hi < pages) add(pages, String(pages));
}

function goPage(p) {
  state.page = p;
  render();
  window.scrollTo({ top: 0, behavior: "smooth" });
}
document.querySelectorAll(".pg-prev").forEach((b) => b.addEventListener("click", () => goPage(state.page - 1)));
document.querySelectorAll(".pg-next").forEach((b) => b.addEventListener("click", () => goPage(state.page + 1)));
$("perPage").addEventListener("change", (e) => { state.perPage = parseInt(e.target.value, 10) || 24; state.page = 1; render(); });

$("q").addEventListener("input", (e) => { state.q = e.target.value.trim(); state.page = 1; render(); });

function buildIndustryChips() {
  const wrap = $("roleChips");
  if (!wrap) return;
  const counts = {};
  state.jobs.forEach((j) => { const i = j.industry || "Lainnya"; counts[i] = (counts[i] || 0) + 1; });
  const order = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
  wrap.innerHTML = "";
  order.forEach((ind) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "chip"; b.dataset.role = ind;
    b.textContent = ind;
    b.title = counts[ind] + " lowongan";
    b.addEventListener("click", () => {
      b.classList.toggle("active");
      state.roles.has(ind) ? state.roles.delete(ind) : state.roles.add(ind);
      state.page = 1; render();
    });
    wrap.appendChild(b);
  });
}
document.querySelectorAll("#typeChips .chip").forEach((c) => {
  c.addEventListener("click", () => {
    c.classList.toggle("active");
    const r = c.dataset.type;
    state.types.has(r) ? state.types.delete(r) : state.types.add(r);
    state.page = 1; render();
  });
});
$("fRemote").addEventListener("change", (e) => { state.remote = e.target.checked; state.page = 1; render(); });
$("fForeign").addEventListener("change", (e) => { state.foreign = e.target.checked; state.page = 1; render(); });
$("fLocal").addEventListener("change", (e) => { state.local = e.target.checked; state.page = 1; render(); });
$("fCity").addEventListener("change", (e) => { state.city = e.target.value; state.page = 1; render(); });
$("fSalary").addEventListener("change", (e) => { state.salaryOnly = e.target.checked; state.page = 1; render(); });
$("fSource").addEventListener("change", (e) => { state.source = e.target.value; state.page = 1; render(); });
$("fFresh").addEventListener("change", (e) => { state.freshHours = parseInt(e.target.value, 10) || 0; state.page = 1; render(); });
$("sort").addEventListener("change", (e) => { state.sort = e.target.value; state.page = 1; render(); });

// ── LIVE TICKER + CHAPTER ─────────────────────────────
function updateSignals() {
  const J = state.jobs;
  const num = (n) => n.toLocaleString("id-ID");
  const set = (id, v) => { const el = $(id); if (el) el.textContent = v; };
  countUp("totalCount", J.length);
  countUp("tRemote", J.filter((j) => j.remote_ok).length);
  countUp("tLocal", J.filter((j) => !j.is_foreign).length);
  countUp("tSalary", J.filter((j) => j.salary).length);
  const now = new Date();
  const date = now
    .toLocaleDateString("id-ID", { weekday: "short", day: "2-digit", month: "short", year: "numeric" })
    .toUpperCase();
  const ch = $("chapter");
  if (ch) ch.textContent = "Edisi " + date + " · " + num(J.length) + " lowongan";
}

function countUp(id, target) {
  const el = $(id);
  if (!el) return;
  const fmt = (n) => n.toLocaleString("id-ID");
  const dur = 500, t0 = performance.now();
  const from = parseInt(el.textContent.replace(/[^\d]/g, "") || "0", 10);
  function tick(t) {
    const p = Math.min((t - t0) / dur, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = fmt(Math.round(from + (target - from) * eased));
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function resetFilters() {
  state.q = ""; state.roles.clear(); state.types.clear();
  state.remote = state.foreign = state.local = state.salaryOnly = false;
  state.city = "";
  state.freshHours = 0;
  state.source = ""; state.sort = "recent"; state.page = 1;
  state.presetAI = false; state.bookmarksOnly = false;
  $("q").value = "";
  document.querySelectorAll(".chip.active").forEach((c) => c.classList.remove("active"));
  $("presetAI").classList.remove("on");
  $("presetBookmarks").classList.remove("on");
  ["fRemote", "fForeign", "fLocal", "fSalary"].forEach((id) => ($(id).checked = false));
  $("fSource").value = ""; $("fFresh").value = ""; $("fCity").value = "";
  $("sort").value = "recent";
  $("perPage").value = state.perPage;
  render();
}
$("resetFilters").addEventListener("click", resetFilters);
$("emptyReset").addEventListener("click", resetFilters);

$("openFilters").addEventListener("click", () => { $("sidebar").classList.add("open"); $("mask").classList.add("show"); });
$("filtersClose").addEventListener("click", closeDrawer);
$("mask").addEventListener("click", closeDrawer);
function closeDrawer() { $("sidebar").classList.remove("open"); $("mask").classList.remove("show"); }

/* ---- AI preset + insight ---- */
$("presetAI").addEventListener("click", (e) => {
  const btn = e.currentTarget;
  const on = btn.classList.toggle("on");
  btn.setAttribute("aria-pressed", String(on));
  state.presetAI = on;
  state.page = 1;
  render();
});
function buildInsight() {
  const el = $("insight");
  if (!el) return;
  const J = state.jobs;
  const total = J.length;
  // top industries
  const ind = {};
  J.forEach((x) => { const i = x.industry || "Lainnya"; ind[i] = (ind[i] || 0) + 1; });
  const topInd = Object.entries(ind).sort((a, b) => b[1] - a[1]).slice(0, 3);
  // top skills from tags
  const tag = {};
  J.forEach((x) => (x.tags || []).forEach((t) => { tag[t] = (tag[t] || 0) + 1; }));
  const topTags = Object.entries(tag).sort((a, b) => b[1] - a[1]).slice(0, 3);
  // remote/local split
  const remote = J.filter((x) => x.remote_ok).length;
  const local = J.filter((x) => !x.is_foreign).length;
  const salary = J.filter((x) => x.salary).length;
  const pct = (n) => Math.round((n / total) * 100);
  el.innerHTML =
    `<div class="insight-head"><h2>Insight pasar</h2><button type="button" class="close" id="insightClose" aria-label="Tutup">tutup</button></div>` +
    `<div class="insight-grid">` +
    `<div class="insight-cell"><div class="k">Total</div><div class="v">${total.toLocaleString("id-ID")}</div></div>` +
    `<div class="insight-cell"><div class="k">Remote</div><div class="v">${pct(remote)}%</div></div>` +
    `<div class="insight-cell"><div class="k">Indonesia</div><div class="v">${pct(local)}%</div></div>` +
    `<div class="insight-cell"><div class="k">Ber-gaji</div><div class="v">${pct(salary)}%</div></div>` +
    `<div class="insight-cell"><div class="k">Top industri</div><div class="v">${topInd.map(([k]) => k).join(" · ")}</div></div>` +
    `<div class="insight-cell"><div class="k">Skill populer</div><div class="v">${topTags.map(([k]) => k).join(" · ")}</div></div>` +
    `</div>`;
  el.hidden = false;
}
$("insight").addEventListener("click", (e) => {
  if (e.target && e.target.id === "insightClose") $("insight").hidden = true;
});

/* ---- bookmark preset toggle ---- */
$("presetBookmarks").addEventListener("click", (e) => {
  const btn = e.currentTarget;
  const on = btn.classList.toggle("on");
  btn.setAttribute("aria-pressed", String(on));
  state.bookmarksOnly = on;
  state.page = 1;
  render();
});

/* ---- detail modal ---- */
function openModal(j) {
  const m = $("modal");
  $("modalRole").textContent = (j.industry || "Lainnya") + " · " + (j.source || "");
  $("modalTitle").textContent = deEmoji(j.title).replace(/—/g, " · ");
  $("modalMeta").textContent = [j.company, j.location].filter(Boolean).join(" · ") || "—";
  const sal = $("modalSalary");
  if (j.salary) { sal.textContent = "Gaji " + deEmoji(j.salary); sal.classList.remove("none"); }
  else { sal.textContent = "gaji tak dicantumkan"; sal.classList.add("none"); }
  const desc = cleanDesc(deEmoji(stripHtml(j.description)));
  $("modalDesc").textContent = desc || "Deskripsi tidak tersedia.";
  const tags = $("modalTags");
  tags.innerHTML = "";
  (j.tags || []).slice(0, 12).forEach((t) => {
    const s = document.createElement("span"); s.className = "tag"; s.textContent = deEmoji(t); tags.appendChild(s);
  });
  if (!(j.tags || []).length) tags.innerHTML = "";
  $("modalNew").textContent = isRecent(j) ? "Baru" : (relativeTime(j.created_at) || "");
  $("modalApply").href = j.url || "#";
  m.hidden = false;
  document.body.classList.add("modal-open");
}
function closeModal() { $("modal").hidden = true; document.body.classList.remove("modal-open"); }
function relativeTime(ts) {
  if (!ts) return "";
  const t = Date.parse(String(ts).replace(" ", "T") + "Z");
  if (isNaN(t)) return "";
  const d = Math.round((Date.now() - t) / 86400e3);
  if (d <= 0) return "hari ini";
  if (d === 1) return "kemarin";
  if (d < 30) return d + " hari lalu";
  const mo = Math.round(d / 30); return mo + (mo === 1 ? " bulan lalu" : " bulan lalu");
}
$("modalClose").addEventListener("click", closeModal);
$("modalX").addEventListener("click", closeModal);
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("modal").hidden) closeModal(); });

/* ---- auto-refresh: silent re-fetch new jobs.json every 5 min ---- */
async function autoRefresh() {
  try {
    const res = await fetch("data/jobs.json?" + Date.now());
    if (!res.ok) return;
    const fresh = await res.json();
    if (fresh.length === state.jobs.length) return;
    if (fresh.length > state.jobs.length) {
      const seen = new Set(state.jobs.map((j) => j.url));
      const added = fresh.filter((j) => !seen.has(j.url)).length;
      if (added) { $("resultText").textContent = "Ada " + added + " lowongan baru · muat ulang atau klik untuk lihat"; }
    }
    state.jobs = fresh;
    _df = null; _jobVec = null; /* invalidate TF-IDF cache — jobs changed */
    buildIndustryChips();
    updateSignals();
    if (!$("insight").hidden) buildInsight(); /* don't reopen if user closed it */
    render();
  } catch { /* silent */ }
}
setInterval(autoRefresh, 5 * 60 * 1000);

load();