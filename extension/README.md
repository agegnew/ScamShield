# ScamShield Guardian (Chrome extension)

Brings ScamShield into the browser. Works in Chrome, Edge and Brave on desktop (Manifest V3, plain JavaScript, no build step).

## What it does

| Part | When | What the user sees |
| --- | --- | --- |
| Block scam sites | Opening a domain ScamShield rated FRAUD or an analyst confirmed | A full-page warning instead of the site (English and Arabic): the domain, the brand it imitates and its risk score, *Go to the real {brand}*, *Go back* and *Continue anyway (not recommended)*. Says "confirmed scam" only when an analyst confirmed it |
| Check this site | Clicking the toolbar icon | A card: *Scam detected* / *Looks suspicious* / *No warning signs*, the risk score, the domain and the brand it impersonates (or "Official Emirates NBD website"), the reasons on demand, and *View details* (opens the citizen checker with the address filled in). Menu: Arabic/English, check again, report (Aman 8002626), settings. The icon badge turns red (`!`) or amber (`?`) on its own while browsing |
| Form warning | A page asks for a card, OTP, password or Emirates ID | A red bar above the page when the page names a UAE brand on a domain the brand doesn't own, or ScamShield already flags the site. Works on brand-new scams nobody has reported yet |

## Install (developer mode)

1. Start the backend (see the main README).
2. Open `chrome://extensions`, turn on **Developer mode**, click **Load unpacked** and choose this `extension/` folder.
3. In the extension's **Settings**, the ScamShield server and the website for *View details* both default to the live instance, `https://scamshield.42studio.fit`. For a local run set them to `http://localhost:8000` and `http://localhost:3001`, then click **Save and sync**.

## How it talks to the backend

| Call | Used for |
| --- | --- |
| `POST /api/check` | Popup (full address of the current tab, started by the user) and badge (site origin only, cached 30 min) |
| `GET /api/brands` | Brand names and official domains for the form warning (cached; works offline) |
| `GET /api/blocklist` | Scam domains, synced every 10 minutes into Chrome's blocking rules: `{"generated_at": ..., "count": 25, "domains": [{"domain": "aramexdelivery.live", "brand_target": "aramex", "score": 100, "confirmed": false, "case_id": "c-0b8e1a9f"}]}`. Lists analyst-confirmed cases and FRAUD cases nobody dismissed, never official, government or popular sites or shared hosts like `sites.google.com` (a scam *on* a platform, `tamm-pay.pages.dev`, is listed), at most 1,000 (Chrome's limit for these rules). If the server can't be reached on the first run, the demo list in `mock-blocklist.json` is used; the first answer from the server replaces it for good |

## Rebuild the download

The website offers this folder as `frontend/public/scamshield-guardian.zip`. After changing a file here, rebuild it from the repository root:

```bash
python -c "import pathlib,zipfile; z=zipfile.ZipFile('frontend/public/scamshield-guardian.zip','w',zipfile.ZIP_DEFLATED); [z.write(p, 'scamshield-guardian/'+p.relative_to('extension').as_posix()) for p in sorted(pathlib.Path('extension').rglob('*')) if p.is_file()]"
```

## Privacy

- Sends the server only addresses: the site's origin while browsing, the full address when the user clicks the icon.
- Never reads what is typed into a form: only each field's type, name, placeholder and label.
- Blocking happens inside Chrome (declarativeNetRequest) from the synced list, so blocked sites are never contacted.

## Limits

- Desktop browsers only. Mobile Chrome has no extensions; on phones the public citizen checker covers the same check.
- A scam domain is blocked only after it is confirmed and synced; until then the badge and the form warning are the protection.
- Host access to all `http`/`https` sites is needed to show the block page and the form warning.
