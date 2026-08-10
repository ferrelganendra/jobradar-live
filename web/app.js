"use strict";

const state = {
  jobs: [],
  q: "",
  roles: new Set(),
  types: new Set(),
  remote: false,
  foreign: false,
  local: false,
  salaryOnly: false,
  source: "",
  sort: "recent",
  page: 1,
  perPage: 24,
};

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const EMOJI_RE = /[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2190}-\u{21FF}\u{FE0F}]/gu;
const deEmoji = (s) => String(s ?? "").replace(EMOJI_RE, "");

const TYPE_LABEL = { full: "Full-time", intern: "Magang", contract: "Kontrak", part: "Part-time" };

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
  $("totalCount").textContent = state.jobs.length;
  buildIndustryChips();
  updateSignals();
  render();}

function matches(j) {
  const t = (j.title + " " + j.company + " " + j.location + " " + (j.description || "") + " " + (j.tags || []).join(" ")).toLowerCase();

  if (state.q) {
    const q = state.q.toLowerCase();
    if (!t.includes(q)) return false;
  }
  if (state.roles.size && !state.roles.has(j.industry)) return false;
  if (state.types.size && !state.types.has(j.job_type)) return false;
  if (state.remote && !j.remote_ok) return false;
  if (state.foreign && !j.is_foreign) return false;
  if (state.local && j.is_foreign) return false;
  if (state.salaryOnly && !j.salary) return false;
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
  if (state.sort === "recent") return 0; // stable insertion order — netral, tanpa bias industri
  if (state.sort === "title") return 0; // title sorted separately in render()
  if (state.sort === "salary") return j.salary ? 1 : 0;
  if (state.q) {
    const q = state.q.toLowerCase();
    const title = j.title.toLowerCase();
    const comp = (j.company || "").toLowerCase();
    let s = 0;
    if (title.includes(q)) s += 3;
    if (comp.includes(q)) s += 2;
    if ((j.description || "").toLowerCase().includes(q)) s += 1;
    return s;
  }
  let s = 0;
  if (j.role === "AI") s += 3;
  else if (j.role === "SWE") s += 2;
  else if (j.role === "IT") s += 1;
  if (j.salary) s += 0.5;
  if (j.is_foreign) s -= 0.5;
  return s;
}

function render() {
  const list = state.jobs.filter(matches);
  if (state.sort === "title") {
    list.sort((a, b) => (a.title || "").localeCompare(b.title || "", "id"));
  } else if (state.sort === "salary") {
    list.sort((a, b) => (salaryNum(b) || 0) - (salaryNum(a) || 0));
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
$("fSalary").addEventListener("change", (e) => { state.salaryOnly = e.target.checked; state.page = 1; render(); });
$("fSource").addEventListener("change", (e) => { state.source = e.target.value; state.page = 1; render(); });
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
  state.source = ""; state.sort = "recent"; state.page = 1;
  $("q").value = "";
  document.querySelectorAll(".chip.active").forEach((c) => c.classList.remove("active"));
  ["fRemote", "fForeign", "fLocal", "fSalary"].forEach((id) => ($(id).checked = false));
  $("fSource").value = "";
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

load();