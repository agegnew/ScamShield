// Block page shown instead of a scam domain (see the redirect rules in background.js).

const target = new URLSearchParams(location.search).get("u") || "";
let domain = "";
try {
  domain = new URL(target).hostname;
} catch {
  domain = "";
}
document.getElementById("domain").textContent = domain || target;

(async () => {
  const [info, brands] = await Promise.all([
    chrome.runtime.sendMessage({ type: "blocked-info", domain }),
    chrome.runtime.sendMessage({ type: "brands" }),
  ]);
  if (info && !info.confirmed) {
    // Rated FRAUD by the engine but not yet confirmed by an analyst: say so.
    document.getElementById("title").textContent = "This website was blocked: ScamShield rates it a scam";
    document.getElementById("title-ar").textContent = "تم حظر هذا الموقع: صنّفه ScamShield موقعًا احتياليًا";
  }
  const brand = info && (brands || []).find((b) => b.id === info.brand_target);
  const score = info && info.score != null ? info.score : null;
  if (!brand) {
    if (score != null) {
      document.getElementById("detail").textContent = `Risk score ${score}/100. Nothing was loaded from it.`;
      document.getElementById("detail-ar").textContent = `درجة الخطورة ${score}/100. لم يتم تحميل أي شيء منه.`;
    }
    return;
  }
  const name = brand.name_en.split(" (")[0];
  document.getElementById("detail").textContent =
    `It imitates ${name}${score != null ? ` (risk score ${score}/100)` : ""}. Nothing was loaded from it.`;
  document.getElementById("detail-ar").textContent = `ينتحل صفة ${brand.name_ar}. لم يتم تحميل أي شيء منه.`;
  const official = document.getElementById("official");
  official.href = `https://${brand.official_domains[0]}/`;
  official.textContent = `Go to the real ${name} - الموقع الرسمي`;
  official.hidden = false;
})();

document.getElementById("back").addEventListener("click", () => {
  if (history.length > 1) history.back();
  else location.href = "about:blank";
});

document.getElementById("continue").addEventListener("click", async () => {
  if (!domain) return;
  await chrome.runtime.sendMessage({ type: "allow-once", domain });
  location.href = target;
});
