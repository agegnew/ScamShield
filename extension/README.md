# ScamShield Guardian (Chrome extension)

Brings ScamShield into the browser. Works in Chrome, Edge and Brave on desktop (Manifest V3, plain JavaScript, no build step).

## What it does

| Part | When | What the user sees |
| --- | --- | --- |
| Block known scams | Opening a domain ScamShield confirmed as FRAUD | A full-page warning instead of the site, with the brand it imitates, a link to the real site, *Go back* and *Continue anyway* |
| Check this site | Clicking the toolbar icon | Verdict, risk score, reasons and what to do, in English or Arabic. The icon badge turns red (`!`) or amber (`?`) on its own while browsing |
| Form warning | A page asks for a card, OTP, password or Emirates ID | A red bar above the page when the page names a UAE brand on a domain the brand doesn't own, or ScamShield already flags the site. Works on brand-new scams nobody has reported yet |

## Install (developer mode)

1. Start the backend (see the main README).
2. Open `chrome://extensions`, turn on **Developer mode**, click **Load unpacked** and choose this `extension/` folder.
3. In the extension's **Settings**, set the ScamShield server (default `http://localhost:8000`) and click **Save and sync**.

## How it talks to the backend

| Call | Used for |
| --- | --- |
| `POST /api/check` | Popup (full address of the current tab, started by the user) and badge (site origin only, cached 30 min) |
| `GET /api/brands` | Brand names and official domains for the form warning (cached; works offline) |
| `GET /api/blocklist` | Confirmed scam domains, synced every 10 minutes into Chrome's blocking rules. Expected shape: `{"domains": [{"domain": "moi-portal.com", "brand_target": "moi", "score": 75}]}`. Until the endpoint exists, the extension uses the demo list in `mock-blocklist.json` (Settings says so); the first answer from the server replaces it for good |

## Privacy

- Sends the server only addresses: the site's origin while browsing, the full address when the user clicks the icon.
- Never reads what is typed into a form: only each field's type, name, placeholder and label.
- Blocking happens inside Chrome (declarativeNetRequest) from the synced list, so blocked sites are never contacted.

## Limits

- Desktop browsers only. Mobile Chrome has no extensions; on phones the public citizen checker covers the same check.
- A scam domain is blocked only after it is confirmed and synced; until then the badge and the form warning are the protection.
- Host access to all `http`/`https` sites is needed to show the block page and the form warning.
