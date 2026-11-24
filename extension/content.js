// ScamShield Guardian form warning.
// When a page asks for a card, OTP, password or Emirates ID and either names a UAE brand on a domain the brand
// does not own, or is already flagged by ScamShield, a warning bar appears above the page.
// Typed values are never read: only the type, name, placeholder and label of each field are looked at.

(() => {
  if (window.top !== window || window.__scamshieldGuardian) return;
  window.__scamshieldGuardian = true;

  const SENSITIVE = [
    ["card", /cc-number|cc-csc|cc-exp|card|cvv|cvc|expiry|البطاقة/i],
    ["otp", /one-time-code|\botp\b|verification code|sms code|رمز التحقق|الرمز/i],
    ["emirates_id", /emirates ?id|\beid\b|784-|الهوية/i],
    ["password", /password|كلمة المرور|كلمة السر/i],
  ];
  const LABELS = {
    card: ["card details", "بيانات البطاقة"],
    otp: ["a one-time code (OTP)", "رمز التحقق"],
    emirates_id: ["your Emirates ID", "رقم الهوية الإماراتية"],
    password: ["a password", "كلمة المرور"],
  };

  const host = location.hostname.toLowerCase();
  const owns = (domain) => host === domain || host.endsWith(`.${domain}`);

  function fieldText(el) {
    const label = (el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`)) || el.closest("label");
    return [el.type, el.name, el.id, el.autocomplete, el.placeholder, el.getAttribute("aria-label"),
      label ? label.innerText : ""].join(" ");
  }

  function sensitiveKinds() {
    const kinds = new Set();
    for (const el of document.querySelectorAll("input, select, textarea")) {
      if (["hidden", "submit", "button", "image", "reset", "checkbox", "radio"].includes(el.type)) continue;
      if (el.type === "password") kinds.add("password");
      const text = fieldText(el);
      for (const [kind, pattern] of SENSITIVE) if (pattern.test(text)) kinds.add(kind);
    }
    return [...kinds];
  }

  function brandNamedHere(brands) {
    const page = `${document.title} ${(document.body?.innerText || "").slice(0, 4000)}`.toLowerCase();
    for (const brand of brands) {
      if (brand.official_domains.some(owns)) return null;  // the brand's own site: never warn
      const names = [brand.name_en.split(" (")[0], brand.name_ar, ...(brand.domain_tokens || [])]
        .map((n) => n.replace(/^-|-$/g, "").toLowerCase())
        .filter((n) => n.length >= 4);
      const inHost = (brand.domain_tokens || []).some((t) => t.replace(/^-|-$/g, "").length >= 4 && host.includes(t.replace(/^-|-$/g, "")));
      if (inHost || names.some((n) => page.includes(n))) return brand;
    }
    return null;
  }

  const esc = (text) => String(text).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

  function showBanner({ brand, kinds, verdict }) {
    if (document.getElementById("scamshield-guardian")) return;
    const what = kinds.map((k) => LABELS[k]);
    const whatEn = what.map((w) => w[0]).join(", ");
    const whatAr = what.map((w) => w[1]).join("، ");
    const official = brand ? esc(brand.official_domains[0]) : null;
    const titleEn = brand
      ? `This is not the official ${esc(brand.name_en.split(" (")[0])} website`
      : "ScamShield flagged this website as a likely scam";
    const titleAr = brand ? `هذا ليس الموقع الرسمي لـ ${esc(brand.name_ar)}` : "صنّف ScamShield هذا الموقع كاحتيال محتمل";
    const scoreNote = verdict && verdict.score != null ? ` · ScamShield ${esc(verdict.verdict)} ${esc(verdict.score)}/100` : "";

    const container = document.createElement("div");
    container.id = "scamshield-guardian";
    container.style.cssText = "all:initial;position:fixed;top:0;left:0;right:0;z-index:2147483647";
    const root = container.attachShadow({ mode: "closed" });
    root.innerHTML = `
      <style>
        .bar { font: 15px/1.45 system-ui, -apple-system, "Segoe UI", Tahoma, sans-serif; background: #C81E1E;
               color: #fff; padding: 14px 18px; display: flex; gap: 16px; align-items: center; flex-wrap: wrap;
               box-shadow: 0 6px 24px rgba(0,0,0,.25); }
        .text { flex: 1 1 420px; }
        strong { font-size: 16px; display: block; }
        .ar { direction: rtl; text-align: right; margin-top: 6px; }
        button { font: 600 14px system-ui, sans-serif; border: 0; border-radius: 999px; padding: 9px 16px;
                 cursor: pointer; }
        .leave { background: #fff; color: #C81E1E; }
        .dismiss { background: transparent; color: #fff; border: 1px solid rgba(255,255,255,.7); }
        button:focus-visible { outline: 3px solid #FBBF24; outline-offset: 2px; }
      </style>
      <div class="bar" role="alert">
        <div class="text">
          <strong>${titleEn}</strong>
          It asks for ${whatEn}. Do not enter your details${official ? `; the real site is ${official}` : ""}.${scoreNote}
          <div class="ar"><strong>${titleAr}</strong>
          يطلب ${whatAr}. لا تُدخل بياناتك${official ? `؛ الموقع الرسمي هو ${official}` : ""}.</div>
        </div>
        <button class="leave">${official ? `Go to ${official}` : "Leave this site"} · غادر</button>
        <button class="dismiss">Dismiss · إغلاق</button>
      </div>`;
    root.querySelector(".leave").addEventListener("click", () => {
      if (official) location.href = `https://${official}/`;
      else history.length > 1 ? history.back() : (location.href = "about:blank");
    });
    root.querySelector(".dismiss").addEventListener("click", () => container.remove());
    document.documentElement.appendChild(container);
  }

  let checking = false;
  async function inspect() {
    if (checking || document.getElementById("scamshield-guardian")) return;
    const kinds = sensitiveKinds();
    if (!kinds.length) return;
    checking = true;
    try {
      const [brands, verdict] = await Promise.all([
        chrome.runtime.sendMessage({ type: "brands" }),
        chrome.runtime.sendMessage({ type: "verdict", origin: location.origin }),
      ]);
      const brand = brandNamedHere(brands || []);
      const ownedByBrand = (brands || []).some((b) => b.official_domains.some(owns));
      const flagged = verdict && (verdict.verdict === "FRAUD" || verdict.verdict === "SUSPICIOUS");
      if (!ownedByBrand && (brand || flagged)) showBanner({ brand, kinds, verdict: flagged ? verdict : null });
    } finally {
      checking = false;
    }
  }

  inspect();
  // Single-page apps and multi-step scam flows add their forms later.
  let timer;
  new MutationObserver(() => {
    clearTimeout(timer);
    timer = setTimeout(inspect, 800);
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
