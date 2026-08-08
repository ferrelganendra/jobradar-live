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
  sort: "relevance",
};

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const ROLE_LABEL = { AI: "AI", SWE: "SWE", IT: "IT", other: "Lain" };
const TYPE_LABEL = { full: "Full-time", intern: "Magang", contract: "Kontrak", part: "Part-time" };

function stripHtml(h) {
  if (!h) return "";
  const d = document.createElement("div");
  d.innerHTML = h;
  return (d.textContent || "").replace(/\s+/g, " ").trim();
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
  // populate source dropdown
  const sources = [...new Set(state.jobs.map((j) => j.source))].sort();
  const sel = $("fSource");
  sources.forEach((s) => {
    const o = document.createElement("option");
    o.value = s;
    o.textContent = s;
    sel.appendChild(o);
  });
  $("totalCount").textContent = state.jobs.length + " lowongan";
  render();
}

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

function score(j) {
  if (state.sort === "title") return 0;
  if (state.sort === "salary") return j.salary ? 1 : 0;
  // relevance: keyword hits in title/company weigh more
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
  // default: AI/SWE/IT prioritized, then salary, then foreign last
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
  list.sort((a, b) => score(b) - score(a));

  $("resultText").textContent = `Menampilkan ${list.length} dari ${state.jobs.length} lowongan`;
  const wrap = $("cards");
  const tpl = $("cardTpl");
  wrap.innerHTML = "";

  if (list.length === 0) {
    $("empty").hidden = false;
    return;
  }
  $("empty").hidden = true;

  for (const j of list) {
    const n = tpl.content.cloneNode(true);
    n.querySelector(".role-badge").textContent = ROLE_LABEL[j.role] || "Lain";
    n.querySelector(".role-badge").classList.add(j.role || "other");
    n.querySelector(".card-source").textContent = j.source;
    n.querySelector(".card-title").textContent = j.title;
    n.querySelector(".meta-company").textContent = j.company || "—";
    const loc = j.location || "Lokasi tak tercantum";
    n.querySelector(".meta-loc").textContent = loc;
    const sal = n.querySelector(".salary-row");
    if (j.salary) sal.textContent = "💰 " + j.salary; else sal.remove();

    const desc = stripHtml(j.description);
    const dEl = n.querySelector(".card-desc");
    if (desc) dEl.textContent = desc; else dEl.remove();

    const tagWrap = n.querySelector(".card-tags");
    (j.tags || []).slice(0, 5).forEach((t) => {
      const s = document.createElement("span");
      s.className = "tag";
      s.textContent = t;
      tagWrap.appendChild(s);
    });
    if (!(j.tags || []).length) tagWrap.remove();

    const btn = n.querySelector(".btn-apply");
    btn.href = j.url || "#";
    if (!j.url) btn.removeEventListener;

    const chips = n.querySelector(".card-chips");
    if (j.remote_ok) {
      const c = document.createElement("span");
      c.className = "mini-chip remote";
      c.textContent = "Remote";
      chips.appendChild(c);
    } else if (j.is_foreign) {
      const c = document.createElement("span");
      c.className = "mini-chip foreign";
      c.textContent = "Luar negeri";
      chips.appendChild(c);
    }
    if (j.job_type && j.job_type !== "full") {
      const c = document.createElement("span");
      c.className = "mini-chip";
      c.textContent = TYPE_LABEL[j.job_type] || j.job_type;
      chips.appendChild(c);
    }
    if (!chips.children.length) chips.remove();

    wrap.appendChild(n);
  }
}

// wire up controls
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

$("resetFilters").addEventListener("click", () => {
  state.q = ""; state.roles.clear(); state.types.clear();
  state.remote = state.foreign = state.local = state.salaryOnly = false;
  state.source = ""; state.sort = "relevance";
  $("q").value = "";
  document.querySelectorAll(".chip.active").forEach((c) => c.classList.remove("active"));
  ["fRemote", "fForeign", "fLocal", "fSalary"].forEach((id) => ($(id).checked = false));
  $("fSource").value = "";
  $("sort").value = "relevance";
  render();
});

// mobile drawer
$("openFilters").addEventListener("click", () => { $("sidebar").classList.add("open"); $("mask").classList.add("show"); });
$("filtersClose").addEventListener("click", closeDrawer);
$("mask").addEventListener("click", closeDrawer);
function closeDrawer() { $("sidebar").classList.remove("open"); $("mask").classList.remove("show"); }

load();