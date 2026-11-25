// ScamShield Guardian service worker.
// - Colours the toolbar badge for every page (sends only the site's origin, never the path or page content).
// - Keeps a local list of confirmed scam domains and blocks them before the page loads (declarativeNetRequest).
// - Caches the UAE brand registry for the form warning in content.js.

const DEFAULT_API = "https://scamshield.42studio.fit";
const VERDICT_TTL_MS = 30 * 60 * 1000;
const SYNC_MINUTES = 10;
const BADGE = {
  FRAUD: { text: "!", color: "#C81E1E" },
  SUSPICIOUS: { text: "?", color: "#B45309" },
  LEGIT: { text: "", color: "#15803D" },
  UNKNOWN: { text: "", color: "#57534E" },
};

async function apiBase() {
  const { apiBase } = await chrome.storage.local.get("apiBase");
  return (apiBase || DEFAULT_API).replace(/\/+$/, "");
}

async function api(path, options = {}) {
  const res = await fetch(`${await apiBase()}${path}`, {
    ...options,
    headers: { "content-type": "application/json", ...(options.headers || {}) },
  });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
}

function siteOf(url) {
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:" ? u.origin : null;
  } catch {
    return null;
  }
}

// --- Verdicts (badge, popup, content warning) ---

async function checkSite(origin) {
  const key = `verdict:${origin}`;
  const cached = (await chrome.storage.session.get(key))[key];
  if (cached && Date.now() - cached.at < VERDICT_TTL_MS) return cached.result;
  const result = await api("/api/check", { method: "POST", body: JSON.stringify({ input: origin }) });
  await chrome.storage.session.set({ [key]: { at: Date.now(), result } });
  return result;
}

// Only the address was judged and it names no brand: plenty of honest small sites have an unusual
// address, so this stays off the badge (the popup still shows it when the user asks).
const ADDRESS_ONLY = new Set(["url_model", "suspicious_tld", "free_platform", "shortener", "no_brand_claim"]);

function badgeFor(result) {
  const addressOnly = result.verdict === "SUSPICIOUS" && !result.brand_target &&
    (result.reasons || []).every((r) => r.weight <= 0 || ADDRESS_ONLY.has(r.code));
  return addressOnly ? BADGE.UNKNOWN : BADGE[result.verdict] || BADGE.UNKNOWN;
}

async function updateBadge(tabId, url) {
  const origin = siteOf(url);
  if (!origin) return chrome.action.setBadgeText({ tabId, text: "" });
  try {
    const result = await checkSite(origin);
    const badge = badgeFor(result);
    await chrome.action.setBadgeText({ tabId, text: badge.text });
    await chrome.action.setBadgeBackgroundColor({ tabId, color: badge.color });
  } catch {
    await chrome.action.setBadgeText({ tabId, text: "" });
  }
}

chrome.tabs.onUpdated.addListener((tabId, info, tab) => {
  if (info.status === "complete" && tab.url) updateBadge(tabId, tab.url);
});

// --- Brand registry (for the form warning) ---

async function syncBrands() {
  try {
    const brands = await api("/api/brands");
    await chrome.storage.local.set({ brands, brandsAt: Date.now() });
  } catch {
    // Keep the last good copy; the form warning still works offline.
  }
}

// --- Blocklist of confirmed scam domains ---

const RULE_ID_START = 1000;

function escapeRegex(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function blockRule(entry, index) {
  const domain = escapeRegex(entry.domain.toLowerCase());
  const page = chrome.runtime.getURL("blocked.html");
  return {
    id: RULE_ID_START + index,
    priority: 1,
    action: { type: "redirect", redirect: { regexSubstitution: `${page}?u=\\0` } },
    condition: {
      regexFilter: `^https?://([^/:]*\\.)?${domain}([:/?#].*)?$`,
      resourceTypes: ["main_frame"],
    },
  };
}

async function applyBlocklist(entries, source) {
  const existing = await chrome.declarativeNetRequest.getDynamicRules();
  await chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: existing.map((rule) => rule.id),
    addRules: entries.map(blockRule),
  });
  const byDomain = Object.fromEntries(entries.map((e) => [e.domain.toLowerCase(), e]));
  await chrome.storage.local.set({ blocklist: byDomain, blocklistAt: Date.now(), blocklistSource: source });
}

async function syncBlocklist() {
  try {
    const data = await api("/api/blocklist");
    await applyBlocklist(data.domains || [], "server");
    await chrome.storage.local.set({ blocklistError: null });
  } catch (error) {
    // Server unreachable: keep blocking with the last list it sent (Chrome keeps the rules) and say so in Settings.
    await chrome.storage.local.set({ blocklistError: String(error && error.message ? error.message : error) });
  }
}

// --- Messages from the popup, the content script and the block page ---

chrome.runtime.onMessage.addListener((message, sender, reply) => {
  (async () => {
    if (message.type === "verdict") return reply(await checkSite(message.origin).catch(() => null));
    if (message.type === "brands") return reply((await chrome.storage.local.get("brands")).brands || []);
    if (message.type === "blocked-info") {
      const { blocklist = {} } = await chrome.storage.local.get("blocklist");
      const host = String(message.domain || "").toLowerCase().replace(/^www\./, "");
      const entry = blocklist[host] || Object.values(blocklist).find((e) => host.endsWith(`.${e.domain}`));
      return reply(entry || null);
    }
    if (message.type === "allow-once") {
      // Let the user through to a blocked domain for this browser session only.
      const id = 1 + Math.floor(Math.random() * 900);
      await chrome.declarativeNetRequest.updateSessionRules({
        addRules: [{
          id,
          priority: 2,
          action: { type: "allow" },
          condition: { requestDomains: [message.domain], resourceTypes: ["main_frame"] },
        }],
      });
      return reply(true);
    }
    if (message.type === "sync") {
      await Promise.all([syncBrands(), syncBlocklist()]);
      return reply(true);
    }
    reply(null);
  })();
  return true;
});

function syncAll() {
  syncBrands();
  syncBlocklist();
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create("sync", { periodInMinutes: SYNC_MINUTES });
  syncAll();
});
chrome.runtime.onStartup.addListener(syncAll);
chrome.alarms.onAlarm.addListener((alarm) => alarm.name === "sync" && syncAll());
