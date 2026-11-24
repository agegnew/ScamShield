const input = document.getElementById("api");
const status = document.getElementById("status");

async function showSync() {
  const { blocklist = {}, blocklistAt, brands = [] } = await chrome.storage.local.get(["blocklist", "blocklistAt", "brands"]);
  document.getElementById("sync").textContent = blocklistAt
    ? `${Object.keys(blocklist).length} blocked scam domains and ${brands.length} UAE brands, synced ${new Date(blocklistAt).toLocaleString()}.`
    : `${brands.length} UAE brands loaded. Blocklist not synced yet.`;
}

chrome.storage.local.get("apiBase").then(({ apiBase }) => {
  input.value = apiBase || "http://localhost:8000";
});

document.getElementById("save").addEventListener("click", async () => {
  await chrome.storage.local.set({ apiBase: input.value.trim() });
  status.textContent = "Syncing…";
  await chrome.runtime.sendMessage({ type: "sync" });
  status.textContent = "Saved.";
  showSync();
});

showSync();
