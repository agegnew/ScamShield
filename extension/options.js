const input = document.getElementById("api");
const site = document.getElementById("site");
const status = document.getElementById("status");

async function showSync() {
  const { blocklist = {}, blocklistAt, blocklistSource, brands = [] } =
    await chrome.storage.local.get(["blocklist", "blocklistAt", "blocklistSource", "brands"]);
  const source = blocklistSource === "demo" ? " (demo list: the server could not be reached)" : "";
  document.getElementById("sync").textContent = blocklistAt
    ? `${Object.keys(blocklist).length} blocked scam domains${source} and ${brands.length} UAE brands, synced ${new Date(blocklistAt).toLocaleString()}.`
    : `${brands.length} UAE brands loaded. Blocklist not synced yet.`;
}

chrome.storage.local.get(["apiBase", "siteBase"]).then(({ apiBase, siteBase }) => {
  input.value = apiBase || "http://localhost:8000";
  site.value = siteBase || "http://localhost:3001";
});

document.getElementById("save").addEventListener("click", async () => {
  await chrome.storage.local.set({ apiBase: input.value.trim(), siteBase: site.value.trim() });
  status.textContent = "Syncing…";
  await chrome.runtime.sendMessage({ type: "sync" });
  status.textContent = "Saved.";
  showSync();
});

showSync();
