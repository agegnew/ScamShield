// Popup: the verdict for the current tab, in the card layout (banner, risk score, domain, View details).
// - On a normal page it asks ScamShield (POST /api/check) with the full address: the user started this check.
// - On the block page it shows the blocked site straight from the synced blocklist, then adds the reasons.

const TEXT = {
  en: {
    checking: "Checking…", nothing: "Nothing to check on this page.", offline: "Can't reach the ScamShield server. Open Settings.",
    score: "Risk score", domain: "Domain", why: "Why ScamShield says this", todo: "What to do", details: "View details",
    lang: "العربية", recheck: "Check again", report: "Report a scam: Aman 8002626", settings: "Settings",
    FRAUD: "Scam detected", SUSPICIOUS: "Looks suspicious", LEGIT: "No warning signs", UNKNOWN: "Not enough information",
    impersonates: (n) => `Impersonates ${n}`, mayImitate: (n) => `May imitate ${n}: don't enter your details`, official: (n) => `Official ${n} website`,
    confirmed: "confirmed scam", flagged: "flagged by ScamShield", blockedNote: "Blocked before it loaded: nothing reached your browser.",
    protecting: (n) => `Guarding against ${n} known scam sites`,
  },
  ar: {
    checking: "جارٍ الفحص…", nothing: "لا يوجد ما يُفحص في هذه الصفحة.", offline: "تعذّر الوصول إلى خادم ScamShield. افتح الإعدادات.",
    score: "درجة الخطورة", domain: "النطاق", why: "لماذا هذا الحكم", todo: "ماذا تفعل", details: "عرض التفاصيل",
    lang: "English", recheck: "افحص مجددًا", report: "بلّغ عن احتيال: أمان 8002626", settings: "الإعدادات",
    FRAUD: "تم اكتشاف احتيال", SUSPICIOUS: "يبدو مشبوهًا", LEGIT: "لا توجد مؤشرات خطر", UNKNOWN: "معلومات غير كافية",
    impersonates: (n) => `ينتحل صفة ${n}`, mayImitate: (n) => `قد ينتحل صفة ${n}: لا تُدخل بياناتك`, official: (n) => `الموقع الرسمي لـ ${n}`,
    confirmed: "احتيال مؤكد", flagged: "صنّفه ScamShield", blockedNote: "تم الحظر قبل التحميل: لم يصل شيء إلى متصفحك.",
    protecting: (n) => `حماية من ${n} موقعًا احتياليًا معروفًا`,
  },
};

// Lucide icons, constant markup only (never API text).
const SVG = (d, w = 2) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const ICON = {
  FRAUD: `<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M10.3 3.4a2 2 0 0 1 3.4 0l8.6 14.9A2 2 0 0 1 20.6 21H3.4a2 2 0 0 1-1.7-2.7z"/><path d="M12 9v4.5M12 17h.01" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/></svg>`,
  SUSPICIOUS: SVG('<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/>', 2.5),
  LEGIT: SVG('<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>', 2.5),
  UNKNOWN: SVG('<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>', 2.5),
  shield: SVG('<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>'),
  link: SVG('<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'),
  arrow: SVG('<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>', 2.5),
};

const DEFAULT_API = "http://localhost:8000";
const DEFAULT_SITE = "http://localhost:3001";

let lang = chrome.i18n.getUILanguage().startsWith("ar") ? "ar" : "en";
let target = null; // the address being judged
let host = "";
let blocked = null; // blocklist entry when the tab is our block page
let result = null; // /api/check answer, null while loading, Error when offline
let brands = [];
let listed = 0;

const $ = (id) => document.getElementById(id);

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => (k === "class" ? (node.className = v) : node.setAttribute(k, v)));
  children.flat().forEach((c) => c != null && c !== "" && node.append(c));
  return node;
}

function icon(name, cls) {
  const span = el("span", cls ? { class: cls } : {});
  span.innerHTML = ICON[name]; // constant markup
  return span.firstElementChild;
}

const brandById = (id) => brands.find((b) => b.id === id);
const shortName = (b) => (lang === "ar" ? b.name_ar : b.name_en.split(" (")[0]);
const ownedBy = (b) => b.official_domains.some((d) => host === d || host.endsWith(`.${d}`));

function verdictNow() {
  if (blocked) return { verdict: "FRAUD", score: blocked.score, brand_target: blocked.brand_target };
  return result && !(result instanceof Error) ? result : null;
}

function brandLine(v, t) {
  const official = brands.find(ownedBy);
  if (official && v.verdict === "LEGIT") return t.official(shortName(official));
  const brand = v.brand_target && brandById(v.brand_target);
  if (!brand) return lang === "ar" ? v.headline_ar : v.headline_en;
  if (v.verdict === "FRAUD") {
    const how = blocked ? (blocked.confirmed ? t.confirmed : t.flagged) : t.flagged;
    return `${t.impersonates(shortName(brand))} (${how})`;
  }
  if (v.verdict === "SUSPICIOUS") return t.mayImitate(shortName(brand));
  return lang === "ar" ? v.headline_ar : v.headline_en;
}

function render() {
  const t = TEXT[lang];
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  $("lang").textContent = t.lang;
  $("recheck").textContent = t.recheck;
  $("report").textContent = t.report;
  $("settings").textContent = t.settings;
  $("foot").textContent = blocked ? t.blockedNote : listed ? t.protecting(listed) : "";

  const box = $("result");
  box.replaceChildren();
  const details = $("details");
  const state = (text, spinning) => el("div", { class: "state" }, spinning ? el("div", { class: "scan" }) : null, el("span", {}, text));

  if (!target) {
    details.hidden = true;
    return box.append(state(t.nothing, false));
  }
  const v = verdictNow();
  if (!v) {
    details.hidden = true;
    return box.append(state(result instanceof Error ? t.offline : t.checking, !(result instanceof Error)));
  }

  const banner = el("div", { class: `banner ${v.verdict}`, role: "status" }, icon(v.verdict), el("span", {}, t[v.verdict] || v.verdict));
  const scoreText = v.score != null ? `${v.score}/100` : "–";
  const rows = el("div", { class: "rows" },
    el("div", { class: "row" }, icon("shield"), el("span", {}, `${t.score}: `, el("b", { class: `score ${v.verdict}`, style: "background:none" }, scoreText))),
    el("div", { class: "row" }, icon("link"), el("span", {},
      `${t.domain}: `, el("b", { class: "ltr" }, host),
      el("span", { class: "sub" }, brandLine(v, t) || ""))));
  box.append(banner, rows);

  const full = result && !(result instanceof Error) ? result : null;
  const reasons = (full?.reasons || []).filter((r) => r.weight !== 0).sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight)).slice(0, 5);
  const advice = full ? (lang === "ar" ? full.advice_ar : full.advice_en) || [] : [];
  if (reasons.length || advice.length) {
    const more = el("details", {}, el("summary", {}, reasons.length ? t.why : t.todo));
    if (reasons.length) {
      more.append(el("ul", { class: "reasons" }, reasons.map((r) =>
        el("li", {}, el("span", { class: r.weight > 0 ? "w" : "w neg" }, `${r.weight > 0 ? "+" : ""}${r.weight}`),
          el("span", {}, lang === "ar" ? r.text_ar : r.text_en)))));
    }
    if (advice.length) {
      more.append(el("p", { style: "margin:10px 0 2px;font-weight:700;font-size:13px" }, t.todo),
        el("ol", { class: "reasons", style: "list-style:decimal;padding-inline-start:18px" }, advice.slice(0, 3).map((a) => el("li", { style: "display:list-item" }, a))));
    }
    box.append(more);
  }

  details.hidden = false;
  details.replaceChildren(el("span", {}, t.details), icon("arrow"));
}

async function settings() {
  const { apiBase, siteBase } = await chrome.storage.local.get(["apiBase", "siteBase"]);
  return {
    api: (apiBase || DEFAULT_API).replace(/\/+$/, ""),
    site: (siteBase || DEFAULT_SITE).replace(/\/+$/, ""),
  };
}

async function check() {
  if (!target) return render();
  result = null;
  render();
  try {
    const { api } = await settings();
    const res = await fetch(`${api}/api/check`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ input: target }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    result = await res.json();
  } catch (error) {
    result = error;
  }
  render();
}

function toggleMenu(open) {
  const menu = $("menu");
  const show = open ?? menu.hidden;
  menu.hidden = !show;
  $("menu-btn").setAttribute("aria-expanded", String(show));
}

$("menu-btn").addEventListener("click", (e) => {
  e.stopPropagation();
  toggleMenu();
});
document.addEventListener("click", (e) => {
  if (!$("menu").contains(e.target)) toggleMenu(false);
});
document.addEventListener("keydown", (e) => e.key === "Escape" && toggleMenu(false));
$("lang").addEventListener("click", () => {
  lang = lang === "ar" ? "en" : "ar";
  toggleMenu(false);
  render();
});
$("recheck").addEventListener("click", () => {
  toggleMenu(false);
  check();
});
$("details").addEventListener("click", async () => {
  const { site } = await settings();
  chrome.tabs.create({ url: `${site}/check?q=${encodeURIComponent(target)}&lang=${lang}` });
});

(async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = (tab && tab.url) || "";
  const blockPage = chrome.runtime.getURL("blocked.html");
  const stored = await chrome.storage.local.get(["brands", "blocklist", "blocklistAt"]);
  brands = stored.brands || [];
  listed = Object.keys(stored.blocklist || {}).length;
  // Opening the popup refreshes a list older than a minute, so an analyst's new confirm blocks right away.
  if (!stored.blocklistAt || Date.now() - stored.blocklistAt > 60 * 1000) chrome.runtime.sendMessage({ type: "sync" });

  if (url.startsWith(blockPage)) {
    target = new URL(url).searchParams.get("u");
  } else if (/^https?:/.test(url)) {
    target = url;
  }
  if (target) {
    try {
      host = new URL(target).hostname.toLowerCase();
    } catch {
      target = null;
    }
  }
  if (target && url.startsWith(blockPage)) {
    const bare = host.replace(/^www\./, "");
    blocked = (stored.blocklist || {})[bare] || (stored.blocklist || {})[host] ||
      Object.values(stored.blocklist || {}).find((e) => host.endsWith(`.${e.domain}`)) || { score: 100, brand_target: null, confirmed: false };
  }
  check();
})();
