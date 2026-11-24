# ScamShield frontend

Analyst console and public citizen checker. Next.js 16, Tailwind 4, no component library: the few primitives live in `src/components/ui/`. English and Arabic with full RTL, WCAG AA colours from the brand kit, keyboard shortcuts on the case page.

## Run

```bash
cd frontend
npm install
npm run dev          # http://localhost:3001
```

It talks to the API at `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`, see `.env.example`). Start the backend first. For the demo, run it in live mode with the real pre-scanned cases and allow the UI's origin:

```bash
cd backend
SCAMSHIELD_MODE=live SCAMSHIELD_SEED_DEMO=1 \
SCAMSHIELD_CORS="http://localhost:3000,http://localhost:3001" \
uvicorn app.main:app --port 8000
```

(Or `docker compose up`; add the same variables to `.env`.) Sign in as `admin` / `admin123` or `analyst` / `analyst123`. Admins also see the audit log and the users page.

## Screens

| Route | What it is |
| --- | --- |
| `/` | Radar feed. Sentence headline, filter by source, one row per auto-discovered URL. Refreshes every 8 s. |
| `/cases` | Every scored URL with filters (verdict, source, brand, status, search). Filters live in the URL. |
| `/cases/[id]` | Case page. Score ring, verdict, reasons that highlight their evidence when selected, screenshot in a phone frame (with a "parked / for sale / blocked" note when the page is a placeholder), redirects, WHOIS, hosting, forms, Maps listing, cloaking, fingerprints. Confirm / dismiss with a logged reason. Export PDF, export JSON evidence bundle, takedown email (EN + AR). Keys: `C` confirm, `D` dismiss, `T` takedown. Polls every 2 s until the worker attaches evidence. |
| `/audit` | Admin only. Every confirm / dismiss across all cases: when, action, domain, reason, who. |
| `/users` | Admin only. Accounts and roles, add an account. |
| `/graph` | Scam network. Click a node to see what links it to others. |
| `/accuracy` | Precision, recall, false-positive rate, F1, confusion matrix, per-dataset bars, honest limits. |
| `/scan` | Scan one URL (jumps to its case) or a batch (CSV download). |
| `/check` | Public citizen checker. Paste a link or phone number, get one big verdict and three things to do, read aloud in Arabic or English. Mobile first. |
| `/login` | Sign in. |

## Conventions

- Every string the UI owns is in `src/lib/i18n.tsx` as an `[en, ar]` pair. Content from the API arrives as `*_en` / `*_ar` fields; use `pick(obj, "text")`.
- URLs, numbers and codes get the `ltr` class so they read correctly inside Arabic text.
- Verdicts always show icon + word + colour (`VerdictChip`). Green means "official site", never "safe".
- A "Demo data" badge appears whenever the API answers with `X-ScamShield-Mode: mock`; "Live" when it is real data.
- Tokens are JWTs. Any 401 clears the session and returns to the login page. Dashboard reads work without a token for the demo; decisions, the audit log and users need one.
- Types come from `src/lib/api-types.d.ts`, a copy of `docs/api/scamshield-api.d.ts`. After an API change, regenerate the contract (`python -m scripts.export_contract` in `backend/`) and copy the file again.

## Check

```bash
npx tsc --noEmit
npx eslint src
```
