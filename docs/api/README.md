# ScamShield API — contract for the UI

The API runs in **mock mode** until the real engine lands (Gate 2, 17:00). Shapes stay the same when it switches to live data, so build against this now.

- **Live server:** `docker compose up` from the repo root (or see `backend/README.md`), then open http://localhost:8000/docs for every endpoint with "Try it out".
- **No Python?** Every response is saved in [`mock/`](mock/) and the full schema in [`openapi.json`](openapi.json).
- **TypeScript types:** [`scamshield-api.d.ts`](scamshield-api.d.ts), generated from the schema. Use `components["schemas"]["Case"]` etc.
- **Mode:** every response has the header `X-ScamShield-Mode: mock | live`. Show a small "Demo data" badge when it says `mock`.

## Endpoints

| Method | Path | Screen | Sample |
| --- | --- | --- | --- |
| GET | `/api/health` | — | `health.json` |
| GET | `/api/brands` | Brand names/logos for chips and filters | `brands.json` |
| GET | `/api/radar/feed?limit=50` | Radar feed (newest first, radar sources only) + counts per source | `radar_feed.json` |
| GET | `/api/cases?verdict=&source=&brand=&status=&q=&limit=&offset=` | Cases list with filters | `cases.json` |
| GET | `/api/cases/{id}` | Case page: verdict, reasons, evidence, decisions | `case_*.json` |
| POST | `/api/cases/{id}/decision` `{action: confirm\|dismiss, reason}` | Confirm / dismiss buttons | returns the updated case |
| GET | `/api/cases/{id}/takedown` | "Takedown request" panel (EN + AR email) | `takedown_c-0001.json` |
| GET | `/api/cases/{id}/report.pdf` | "Export PDF" button — returns **501** until 19:00 | — |
| GET | `/api/graph` | Network graph: nodes = risky cases, edges = shared infrastructure | `graph.json` |
| GET | `/api/metrics` | Accuracy page | `metrics.json` |
| POST | `/api/scan` `{url}` | "Scan a URL" box. Returns `status: queued` with a quick URL-only verdict; poll `GET /api/cases/{case_id}` every 2 s until `evidence` is filled | `scan.json` |
| POST | `/api/batch` `{urls: [...]}` (`?format=csv` for a file) | Batch upload | `batch.json` |
| POST | `/api/check` `{input}` | **Public citizen checker** — link or phone number | `check_*.json` |
| POST | `/api/auth/login` `{username, password}` | Login | `login.json` |

## Conventions

- **Verdicts:** `FRAUD`, `SUSPICIOUS`, `LEGIT`. The citizen checker can also return `UNKNOWN` (an unknown phone number), with `score: null`. Until the engine is built, new URLs come back `SUSPICIOUS` 50 with reason code `engine_incomplete` — show it like any other reason.
- **Score:** 0–100, higher = riskier.
- **Bilingual text:** every user-facing string comes as a pair, `*_en` and `*_ar` (reasons, headlines, advice, takedown body). Pick by the UI language; never machine-translate in the UI.
- **Reasons:** list of `{code, weight, text_en, text_ar, evidence_ref}`. Positive weight raises risk, negative lowers it. `evidence_ref` tells you which evidence block to highlight (`screenshot`, `rdap.created`, `forms`, `redirect_chain`, `candidate.extra.phone`, ...).
- **Screenshots:** `evidence.screenshot_path` is relative; load it from `<API>/artifacts/<screenshot_path>`. Mock cases point at a grey placeholder.
- **Times:** ISO 8601 with offset. Show them in UAE time.
- **Sources:** `lookalike`, `ct` (new certificate), `search`, `search_ad`, `maps`, `manual`, `citizen`, `batch`.
- **Case status:** `new`, `confirmed`, `dismissed`.
- **Auth (mock):** log in as `admin` or `analyst` with any password; send `Authorization: Bearer <access_token>`. Real login with roles arrives at 14:00, same endpoint.

## Mock data at a glance

| Case | Domain | Source | Verdict | Why it's in the set |
| --- | --- | --- | --- | --- |
| c-0001 | tamm-fines-pay.test | lookalike | FRAUD 94, confirmed | Card + OTP form, full evidence |
| c-0002 | uaepass-login.test | ct | FRAUD 89 | New certificate, password + OTP form |
| c-0003 | emiratesnbd-support.test | maps | FRAUD 81 | Fake helpline number on a Maps listing |
| c-0004 | rta-fine-check.test | search_ad | SUSPICIOUS 58 | Paid ad for a fines query |
| c-0005 | s.test/x7Kp2 | citizen | FRAUD 90 | Short link with a redirect chain |
| c-0006 | www.tamm.abudhabi | search | LEGIT 0 | Official domain, no evidence block |
| c-0007 | www.rta.ae | search | LEGIT 0 | Official domain |
| c-0008 | uae-pass.test | lookalike | SUSPICIOUS 42, dismissed | Parked lookalike |

Scam domains use the reserved `.test` TLD and documentation IP ranges, so none of them point at a real site.
