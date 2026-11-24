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
  if (!tabUrl) return box.append(el("p", { class: "muted" }, t.nothing));
  if (result === null) return box.append(el("p", { class: "muted" }, t.checking));
  if (result instanceof Error) return box.append(el("p", { class: "muted" }, t.offline));

  const reasons = (result.reasons || []).filter((r) => r.weight > 0);
  box.append(
    el("div", { class: "verdict" },
      el("span", { class: `chip ${result.verdict}` }, t[result.verdict] || result.verdict),
      result.score != null ? el("span", { class: "score muted" }, `${t.score}: ${result.score}/100`) : ""),
    el("h1", {}, lang === "ar" ? result.headline_ar : result.headline_en),
  );
  if (reasons.length) {
    box.append(el("section", {}, el("strong", {}, t.why),
      el("ul", { class: "reasons" }, reasons.map((r) => el("li", {}, lang === "ar" ? r.text_ar : r.text_en)))));
  }
  const advice = lang === "ar" ? result.advice_ar : result.advice_en;
  if (advice && advice.length) {
    box.append(el("section", {}, el("strong", {}, t.todo), el("ul", {}, advice.map((a) => el("li", {}, a)))));
  }
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
