// Popup: check the current tab with ScamShield (POST /api/check) and explain the verdict in English or Arabic.
// This check is started by the user, so the full address is sent: the path helps the URL model.

const TEXT = {
  en: { checking: "Checking…", nothing: "Nothing to check on this page.", offline: "Can't reach the ScamShield server. Check Settings.", score: "Risk score", why: "Why", todo: "What to do", lang: "العربية", recheck: "Check again", report: "Report: Aman 8002626", settings: "Settings",
        FRAUD: "Scam", SUSPICIOUS: "Suspicious", LEGIT: "No warning signs", UNKNOWN: "Unknown" },
  ar: { checking: "جارٍ الفحص…", nothing: "لا يوجد ما يُفحص في هذه الصفحة.", offline: "تعذّر الوصول إلى خادم ScamShield. راجع الإعدادات.", score: "درجة الخطورة", why: "الأسباب", todo: "ماذا تفعل", lang: "English", recheck: "افحص مجددًا", report: "بلّغ: أمان 8002626", settings: "الإعدادات",
        FRAUD: "احتيال", SUSPICIOUS: "مشبوه", LEGIT: "لا توجد مؤشرات خطر", UNKNOWN: "غير معروف" },
};

let lang = chrome.i18n.getUILanguage().startsWith("ar") ? "ar" : "en";
let result = null;
let tabUrl = null;

const $ = (id) => document.getElementById(id);

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => (k === "class" ? (node.className = v) : node.setAttribute(k, v)));
  children.flat().forEach((c) => node.append(c));
  return node;
}

function render() {
  const t = TEXT[lang];
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  $("lang").textContent = t.lang;
  $("recheck").textContent = t.recheck;
  $("report").textContent = t.report;
  document.querySelector('a[href="options.html"]').textContent = t.settings;

  const box = $("result");
  box.replaceChildren();
  const state = (text, spinning) => el("div", { class: "panel state" }, spinning ? el("div", { class: "scan" }) : "", text);
  if (!tabUrl) return box.append(state(t.nothing, false));
  if (result === null) return box.append(state(t.checking, true));
  if (result instanceof Error) return box.append(state(t.offline, false));

  const v = result.verdict;
  const reasons = (result.reasons || []).filter((r) => r.weight > 0).sort((a, b) => b.weight - a.weight);
  const chip = el("span", { class: `chip ${v}` });
  chip.innerHTML = ICONS[v] || ICONS.UNKNOWN; // constant markup, never API text
  chip.append(t[v] || v);

  const hero = el("div", { class: `panel hero ${v}-bg` },
    el("div", {}, chip, el("h1", {}, lang === "ar" ? result.headline_ar : result.headline_en)),
    result.score != null ? ring(result.score, v, t.score) : "");
  box.append(hero);

  if (reasons.length) {
    box.append(el("section", { class: "panel block" }, el("strong", {}, t.why),
      el("ul", { class: "reasons" }, reasons.map((r) =>
        el("li", {}, el("span", { class: "w" }, `+${r.weight}`), el("span", {}, lang === "ar" ? r.text_ar : r.text_en))))));
  }
  const advice = lang === "ar" ? result.advice_ar : result.advice_en;
  if (advice && advice.length) {
    box.append(el("section", { class: "panel block" }, el("strong", {}, t.todo), el("ol", { class: "todo" }, advice.map((a) => el("li", {}, el("span", {}, a))))));
  }
}

// Verdict icons (lucide: ban, triangle-alert, shield-check, circle-help). Constant strings only.
const SVG = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const ICONS = {
  FRAUD: SVG('<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>'),
  SUSPICIOUS: SVG('<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>'),
  LEGIT: SVG('<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>'),
  UNKNOWN: SVG('<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>'),
};
const RING_COLOR = { FRAUD: "#ff7a7a", SUSPICIOUS: "#fbbf24", LEGIT: "#86efac", UNKNOWN: "#b7b2ad" };

function ring(score, verdict, label) {
  const r = 26, c = 2 * Math.PI * r, s = Math.max(0, Math.min(100, score));
  const wrap = el("div", { class: "ring", role: "img", "aria-label": `${label}: ${score}/100` });
  const color = RING_COLOR[verdict] || RING_COLOR.UNKNOWN;
  wrap.innerHTML = `<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="${r}" fill="none" stroke="#26402f" stroke-width="6"/>` +
    `<circle cx="32" cy="32" r="${r}" fill="none" stroke="${color}" stroke-width="6" stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - s / 100)}" style="filter:drop-shadow(0 0 6px ${color})"/></svg>`;
  wrap.append(el("span", { style: `color:${color}` }, String(score)), el("small", {}, label));
  return wrap;
}

async function check() {
  result = null;
  render();
  const { apiBase } = await chrome.storage.local.get("apiBase");
  try {
    const res = await fetch(`${(apiBase || "http://localhost:8000").replace(/\/+$/, "")}/api/check`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ input: tabUrl }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    result = await res.json();
  } catch (error) {
    result = error;
  }
  render();
}

$("lang").addEventListener("click", () => {
  lang = lang === "ar" ? "en" : "ar";
  render();
});
$("recheck").addEventListener("click", check);

chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  const url = tab && tab.url;
  tabUrl = url && /^https?:/.test(url) ? url : null;
  $("site").textContent = tabUrl ? new URL(tabUrl).hostname : "";
  if (tabUrl) check();
  else render();
});
