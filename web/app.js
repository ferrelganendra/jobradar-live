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
};

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const EMOJI_RE = /[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2190}-\u{21FF}\u{FE0F}]/gu;
const deEmoji = (s) => String(s ?? "").replace(EMOJI_RE, "");

const ROLE_LABEL = { AI: "AI", SWE: "SWE", IT: "IT", other: "Lain" };
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
  t = t.replace(/\s+/g, " ").trim();
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
  updateSignals();
  render();}

function matches(j) {
  const t = (j.title + " " + j.company + " " + j.location + " " + (j.description || "") + " " + (j.tags || []).join(" ")).toLowerCase();

  if (state.q) {
    const q = state.q.toLowerCase();
    if (!t.includes(q)) return false;
  }
  if (state.roles.size && !state.roles.has(j.role)) return false;
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
  let n = parseFloat(m[1].replace(/,/g, ""));
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

  $("resultText").textContent = `Menampilkan ${list.length} dari ${state.jobs.length} lowongan`;
  const wrap = $("cards");
  const tpl = $("cardTpl");
  wrap.innerHTML = "";

  if (list.length === 0) {
    $("empty").hidden = false;
    return;
  }
  $("empty").hidden = true;

  for (const [i, j] of list.entries()) {
    const n = tpl.content.cloneNode(true);
    const card = n.firstElementChild;
    card.style.animationDelay = Math.min(i * 18, 350) + "ms";
    n.querySelector(".role-label").textContent = ROLE_LABEL[j.role] || "Lain";
    n.querySelector(".card-source").textContent = j.source;
    n.querySelector(".card-title").textContent = deEmoji(j.title);
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
}

$("q").addEventListener("input", (e) => { state.q = e.target.value.trim(); render(); });

document.querySelectorAll("#roleChips .chip").forEach((c) => {
  c.addEventListener("click", () => {
    c.classList.toggle("active");
    const r = c.dataset.role;
    state.roles.has(r) ? state.roles.delete(r) : state.roles.add(r);
    render();
  });
});
document.querySelectorAll("#typeChips .chip").forEach((c) => {
  c.addEventListener("click", () => {
    c.classList.toggle("active");
    const r = c.dataset.type;
    state.types.has(r) ? state.types.delete(r) : state.types.add(r);
    render();
  });
});
$("fRemote").addEventListener("change", (e) => { state.remote = e.target.checked; render(); });
$("fForeign").addEventListener("change", (e) => { state.foreign = e.target.checked; render(); });
$("fLocal").addEventListener("change", (e) => { state.local = e.target.checked; render(); });
$("fSalary").addEventListener("change", (e) => { state.salaryOnly = e.target.checked; render(); });
$("fSource").addEventListener("change", (e) => { state.source = e.target.value; render(); });
$("sort").addEventListener("change", (e) => { state.sort = e.target.value; render(); });

// ── LIVE TICKER + CHAPTER ─────────────────────────────
function updateSignals() {
  const J = state.jobs;
  const num = (n) => n.toLocaleString("id-ID");
  const set = (id, v) => { const el = $(id); if (el) el.textContent = v; };
  countUp("totalCount", J.length);
  countUp("tRemote", J.filter((j) => j.remote_ok).length);
  countUp("tLocal", J.filter((j) => !j.is_foreign).length);
  countUp("tAI", J.filter((j) => j.role === "AI").length);
  countUp("tSW", J.filter((j) => j.role === "SWE").length);
  countUp("tSalary", J.filter((j) => j.salary).length);
  set("tSource", num(new Set(J.map((j) => j.source)).size));
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
  state.source = ""; state.sort = "recent";
  $("q").value = "";
  document.querySelectorAll(".chip.active").forEach((c) => c.classList.remove("active"));
  ["fRemote", "fForeign", "fLocal", "fSalary"].forEach((id) => ($(id).checked = false));
  $("fSource").value = "";
  $("sort").value = "recent";
  render();
}
$("resetFilters").addEventListener("click", resetFilters);
$("emptyReset").addEventListener("click", resetFilters);

$("openFilters").addEventListener("click", () => { $("sidebar").classList.add("open"); $("mask").classList.add("show"); });
$("filtersClose").addEventListener("click", closeDrawer);
$("mask").addEventListener("click", closeDrawer);
function closeDrawer() { $("sidebar").classList.remove("open"); $("mask").classList.remove("show"); }

load();