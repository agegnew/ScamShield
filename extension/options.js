const input = document.getElementById("api");
const site = document.getElementById("site");
const status = document.getElementById("status");

async function showSync() {
  const { blocklist = {}, blocklistAt, blocklistError, brands = [] } =
    await chrome.storage.local.get(["blocklist", "blocklistAt", "blocklistError", "brands"]);
  const synced = blocklistAt
    ? `${Object.keys(blocklist).length} scam domains blocked and ${brands.length} UAE brands, last synced ${new Date(blocklistAt).toLocaleString()}.`
    : `${brands.length} UAE brands loaded. The scam list has not been synced yet.`;
  const problem = blocklistError ? ` Could not reach the server just now (${blocklistError}); the last list stays active.` : "";
  document.getElementById("sync").textContent = synced + problem;
}

chrome.storage.local.get(["apiBase", "siteBase"]).then(({ apiBase, siteBase }) => {
  input.value = apiBase || "https://scamshield.42studio.fit";
  site.value = siteBase || "https://scamshield.42studio.fit";
});

document.getElementById("save").addEventListener("click", async () => {
  await chrome.storage.local.set({ apiBase: input.value.trim(), siteBase: site.value.trim() });
  status.textContent = "Syncing…";
  await chrome.runtime.sendMessage({ type: "sync" });
  status.textContent = "Saved.";
  showSync();
});

showSync();
