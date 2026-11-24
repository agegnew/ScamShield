# ScamShield API — contract for the UI

The engine, radar and worker are real. The API still starts in **mock mode** by default (8 demo cases on `.test` domains); set `SCAMSHIELD_MODE=live` (and `SCAMSHIELD_SEED_DEMO=1` for the real pre-scanned demo cases). Shapes are the same in both modes.

- **Live server:** `docker compose up` from the repo root (or see `backend/README.md`), then open http://localhost:8000/docs for every endpoint with "Try it out".
- **No Python?** Every response is saved in [`mock/`](mock/) and the full schema in [`openapi.json`](openapi.json).
- **TypeScript types:** [`scamshield-api.d.ts`](scamshield-api.d.ts), generated from the schema. Use `components["schemas"]["Case"]` etc.
- **Mode:** every response has the header `X-ScamShield-Mode: mock | live`. Show a small "Demo data" badge when it says `mock`.

## Endpoints

| Method | Path | Screen | Sample |
| --- | --- | --- | --- |
| GET | `/api/health` | — | `health.json` |
| GET | `/api/brands` | Brand names/logos for chips and filters | `brands.json` |
| GET | `/api/radar/feed?limit=&source=&category=&verdict=&brand=&q=` | Radar feed (newest first, radar sources only). Each item has `brand_category` and `source_details`; `counts_by_source` and `counts_by_category` ignore the filters. `source=search` includes ads, `category=none` = no brand named. See [radar-ui.md](../radar-ui.md) | `radar_feed.json` |
| GET | `/api/radar/status` | Radar page: current or last run with per-source progress, page checks and verdicts; daily schedule; each source's state; `searches_left` (SerpApi). Poll every 2 s while `running` | `radar_status.json` |
| POST | `/api/radar/run` `{sources?, brands?}` | **Logged in.** "Run radar now" → **202** `{run}`; **409** `{detail: "radar_already_running", run}`; **400** unknown brand | `radar_run.json` |
| GET | `/api/radar/runs?limit=10` | Last runs, newest first | `radar_runs.json` |
| GET | `/api/cases?verdict=&source=&brand=&status=&q=&limit=&offset=` | Cases list with filters | `cases.json` |
| GET | `/api/cases/{id}` | Case page: verdict, reasons, evidence, decisions | `case_*.json` |
| POST | `/api/cases/{id}/decision` `{action: confirm\|dismiss, reason}` | Confirm / dismiss buttons | returns the updated case |
| GET | `/api/cases/{id}/takedown` | "Takedown request" panel (EN + AR email). `recipients` = registrar + host abuse emails (deduplicated); `mailto` = ready `mailto:` link with subject and English body (null when no contact) | `takedown_c-0001.json` |
| GET | `/api/cases/{id}/report.pdf` | "Export PDF" button: police-ready evidence report (A4, English + Arabic): verdict, reasons, screenshot + SHA-256, redirects, WHOIS/hosting, page findings, related domains, decisions, takedown contacts. Downloads as `scamshield-<id>.pdf` | — |
| GET | `/api/cases/{id}/export.json` | "Export evidence (JSON)" button: `{generated_at, scamshield_version, model_version, case, takedown, related}`. `related` = other cases sharing infrastructure `{case_id, domain, verdict, score, type, detail}`. Downloads as `scamshield-<id>.json` | — |
| GET | `/api/graph` | Network graph: nodes = risky cases, edges = shared infrastructure | `graph.json` |
| GET | `/api/metrics` | Accuracy page | `metrics.json` |
| POST | `/api/scan` `{url}` | "Scan a URL" box. Returns `status: queued` with a quick URL-only verdict; poll `GET /api/cases/{case_id}` every 2 s until `evidence` is filled | `scan.json` |
| POST | `/api/batch` `{urls: [...]}` (`?format=csv` for a file) | Batch upload | `batch.json` |
| POST | `/api/check` `{input}` | **Public citizen checker** — link or phone number | `check_*.json` |
| POST | `/api/auth/login` `{username, password}` | Login. Returns `{access_token, token_type: "bearer", user: {username, role}}`; **401** "Wrong username or password" | `login.json` |
| GET | `/api/auth/me` | Who is logged in (restore the session on page load); **401** if the token is missing, invalid or expired | `auth_me.json` |
| GET | `/api/users` | **Admin only.** Accounts: `username, role, disabled, created_at` (never passwords) | `users.json` |
| POST | `/api/users` `{username, password (min 8), role: admin\|analyst}` | **Admin only.** Create an account → **201**; **409** if the username exists | returns the user |
| GET | `/api/decisions?limit=100` | **Admin only.** Audit log of every confirm/dismiss: `case_id, domain, action, reason, by, at`, newest first | `decisions.json` |

## Conventions

- **Verdicts:** `FRAUD` (score ≥ 70), `SUSPICIOUS` (30–69), `LEGIT` (< 30). The citizen checker can also return `UNKNOWN` (an unknown phone number), with `score: null`.
- **Score:** 0–100, higher = riskier.
- **Bilingual text:** every user-facing string comes as a pair, `*_en` and `*_ar` (reasons, headlines, advice, takedown body). Pick by the UI language; never machine-translate in the UI.
- **AI review:** `evidence.ai_review` = `{model, verdict: scam|legit|unsure, confidence, impersonates, asks_for, explanation_en, explanation_ar, reviewed_at}` when Claude looked at a borderline page (null otherwise). It also appears as a reason: `ai_flagged` (+15/+30) or `ai_cleared` (−15/−30). Show it like any other reason; an "AI review" badge on the case page is optional.
- **Reasons:** list of `{code, weight, text_en, text_ar, evidence_ref}`. Positive weight raises risk, negative lowers it. `evidence_ref` tells you which evidence block to highlight (`screenshot`, `rdap.created`, `forms`, `redirect_chain`, `candidate.extra.phone`, ...).
- **Screenshots:** `evidence.screenshot_path` is relative; load it from `<API>/artifacts/<screenshot_path>`. Mock cases point at a grey placeholder.
- **Times:** ISO 8601 with offset. Show them in UAE time.
- **Sources:** `lookalike`, `ct` (new certificate), `nrd` (newly registered domain), `search`, `search_ad`, `maps`, `manual`, `citizen`, `batch`.
- **Case status:** `new`, `confirmed`, `dismissed`.
- **Auth:** log in with `POST /api/auth/login` and send `Authorization: Bearer <access_token>` on every request. Tokens are JWTs that expire after 12 hours; on any **401** (it carries `WWW-Authenticate: Bearer`) clear the token and show the login page. Demo accounts: `admin` / `admin123` (role `admin`) and `analyst` / `analyst123` (role `analyst`).
  - **Public, no login:** `/api/health`, `/api/brands`, `/api/metrics`, `/api/check`, `/api/auth/login`.
  - **Logged in (analyst or admin):** `POST /api/radar/run`, `POST /api/cases/{id}/decision`. The decision is stored with the token's username as `by`, the server time as `at`, and your `reason`.
  - **Admin only:** `/api/users`, `/api/decisions`. Analysts get **403**; hide these screens for them.
  - **Dashboard reads** (radar, cases, case page, graph, takedown, report.pdf, scan, batch) are open for the demo, so a stale token there is ignored. With `SCAMSHIELD_REQUIRE_LOGIN=1` they need a token too, so always send it if you have one.
  - Tokens beginning `mock-` are no longer accepted.

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
