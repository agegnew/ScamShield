# ScamShield — MVP Plan & Team Assignments

**Updated:** 24 Nov 2026 (kickoff day). **Code freeze:** 00:00. **Submit by:** 06:00 Wed 25 Nov (hard deadline 08:00).

We win with a working engine that finds UAE-brand scams on its own (Search, Maps, new lookalike domains), scores every URL with reasons in Arabic and English, and exports police-ready evidence.

> The design docs in `ScamShield-AI-Documentation/` were written before the kickoff. Where they conflict with this file, this file wins.

## Getting started

```bash
git clone https://github.com/agegnew/ScamShield.git
cd ScamShield
cp .env.example .env
docker compose up --build        # Postgres + API + page worker + radar
```

API docs at http://localhost:8000/docs. No Docker? See [`backend/README.md`](backend/README.md) (runs on SQLite).

| Person | Work in | Start with |
| --- | --- | --- |
| Nati | `frontend/` — create the Next.js app there | [`docs/api/README.md`](docs/api/README.md), TypeScript types in [`docs/api/scamshield-api.d.ts`](docs/api/scamshield-api.d.ts), sample JSON in `docs/api/mock/` |
| Agegnew | `backend/app/` (API, DB, engine) | [`backend/app/engine/core.py`](backend/app/engine/core.py) |
| Simon | `backend/app/workers/` | [`fetcher.py`](backend/app/workers/fetcher.py), [`enrich.py`](backend/app/workers/enrich.py), [`radar/`](backend/app/workers/radar/) (lookalikes, ct, nrd, search, maps) |
| Samri | `data/scam_themes.json`, `data/brands.json`, `data/logos/` | Run `python -m scripts.validate_data` (from `backend/`) before committing |

Pull before you push, keep commits small, and edit only files your lane owns ([ownership table](backend/README.md#who-owns-what)).

## How we are judged

| Weight | Criterion | What judges check |
| --- | --- | --- |
| 30% | Detection accuracy | Precision and recall on a **hidden test set** of fraud and legit URLs. Few false positives on real banks and government sites. Handles redirects, URL shorteners and cloaking |
| 25% | Early detection and coverage | Newly registered domains, lookalike domains, fresh ads. **Both** Search and Maps, including fake business pages and fake helpline numbers |
| 20% | Explainability and actionability | Risk score with clear reasons. Evidence: screenshots, WHOIS, hosting data, timestamps. Exportable for takedown |
| 15% | UAE relevance and innovation | Arabic/bilingual. UAE banks, TAMM, UAE PASS, traffic fines. Visual similarity, LLM analysis, scam-domain network |
| 10% | Feasibility and presentation | Live demo, scalable design, route to a police pilot, honest about limits |

## MVP scope

At code freeze all seven P0 items run end to end on a laptop, on live data or on clearly labelled fixtures.

**P0 — must ship**

1. **Auto-discovery radar:** lookalike domains of UAE brands, new TLS certificates (crt.sh), Google Search results and ads, Google Maps listings. Nobody pastes anything.
2. **Detection engine:** every URL gets FRAUD / SUSPICIOUS / LEGIT, a 0–100 score and reasons in English and Arabic, even when the site is already offline.
3. **Evidence:** screenshot, redirect chain, WHOIS/RDAP, IP and hosting provider, timestamps. Shown on the case page, exported as PDF plus a takedown request.
4. **Dashboard (EN/AR, full RTL, accessible):** radar feed, cases list, case page, accuracy page.
5. **Citizen checker:** public page. Paste a link or a phone number, get a plain-language verdict in Arabic or English.
6. **Users:** admin and analyst roles; analysts confirm or dismiss a case, logged with who, when and why.
7. **Batch mode + accuracy report:** a list of URLs in, a CSV of verdicts out; our measured precision and recall.

**P1 — only after Gate 3 (21:00), in this order**

1. Scam network graph: domains linked by shared IP, registrar, registration day, favicon or redirect target.
2. Cloaking check: compare a mobile and a desktop fetch.
3. LLM vision check: does the page imitate a brand's look on the wrong domain.
4. Read-aloud verdict on the citizen page, Arabic and English.

**Cut — roadmap slide only:** Chrome extension, phone companion, AR/QR camera, Rescue, SafePay, Redis queues, live push updates.

## Accuracy (measured)

Full engine on a held-out test set of **11,134 URLs** whose sites never appear in training: 3,000 phishing (PhishTank, OpenPhish, Phishing.Database, PhiUSIIL) and 8,134 legit (deep pages of 4,000 popular sites + 230 UAE official pages). URL only, no page fetch, phishing-feed lookups **off** so the number reflects detection, not lookup.

| Precision | Recall | False-positive rate | F1 | UAE official pages flagged |
| --- | --- | --- | --- | --- |
| 0.942 | 0.778 | 1.8% | 0.852 | 0 of 230 |

With feed lookups on, recall is 0.824 at the same false-positive rate. The misses are mostly phishing homepages with ordinary names (`http://www.jolifm.com`), which a URL alone cannot reveal; the page fetch (screenshot, forms, brand text, domain age) catches those. Reproduce: `python -m scripts.build_dataset`, `python -m scripts.train_url_model`, `python -m scripts.evaluate` (from `backend/`).

## How it fits together

```mermaid
flowchart TD
  subgraph RADAR["Auto-discovery radar · Simon"]
    L[Lookalikes<br/>typo variants]
    C[New certs<br/>crt.sh]
    N[New domains<br/>daily list]
    S[Search<br/>organic + ads]
    M[Maps<br/>phone check]
  end
  D[Direct input · API<br/>paste URL, citizen check, batch CSV]
  B[Brand registry · Samri<br/>domains, helplines, EN/AR keywords]
  F[Fetch + enrich · Simon<br/>shorteners, redirects, screenshot, forms,<br/>WHOIS/RDAP, DNS, IP, ASN, hosting]
  E[Detection engine · Agegnew + Claude Code<br/>allowlist → threat feeds → URL model → brand lookalike<br/>→ AR/EN scam words → helpline check<br/>→ verdict, score, reasons EN/AR]
  DB[Database + API · Agegnew<br/>cases, verdicts, evidence, users, graph links]
  X[Exports · Agegnew<br/>PDF report, takedown email + JSON]
  subgraph UI["Screens · Nati · EN/AR, accessible"]
    U1[Radar feed]
    U2[Case page]
    U3[Citizen checker]
    U4[Accuracy page]
  end
  B --> RADAR
  B --> E
  RADAR --> F
  D --> F
  F --> E
  E --> DB
  DB --> X
  DB --> UI
```

The brand registry feeds both the radar and the engine; every screen reads from one API.

## Who owns what

| Person | Role | Owns | First handoff |
| --- | --- | --- | --- |
| Nati | UI/UX and accessibility | Dashboard, citizen checker, EN/AR RTL, design system | UI shell on mock data — 13:00 |
| Agegnew (+ Claude Code) | Backend, DB, users, engine | API, database, roles, detection engine, URL model, accuracy eval, PDF/takedown | API contract + mock JSON — 11:45 |
| Simon | Workers and discovery | Job runner, fetcher, enrichment, radar (lookalikes, crt.sh, Search, Maps) | First real URL fetched + screenshot — 13:00 |
| Samri | Research, creative, pitch | Scam themes + UAE brand registry, branding, demo pages, deck, video, demo script | scam_themes.json + brands.json v1 — 15:00 |

Everyone works on mock data until 17:00 so nobody waits on anyone.

## Task lists

### Nati — UI/UX and accessibility

- [ ] **11:45** — Agree screens and API shapes with Agegnew (see Shared contracts)
- [ ] **13:00** — App shell: Next.js + Tailwind + shadcn/ui, EN/AR switch with full RTL, navigation, login page
- [ ] **15:00** — Radar feed: live list of auto-discovered URLs, source badge (Lookalike / New cert / New domain / Search / Ad / Maps), verdict chip, brand targeted
- [ ] **17:00** — Case page: verdict + score, reasons in EN/AR, screenshot, redirect timeline, WHOIS + hosting, confirm/dismiss, Export PDF and takedown
- [ ] **19:00** — Citizen checker (public, mobile-first): paste a link or phone number → big plain-language verdict + what to do next
- [ ] **20:00** — Cases list (filter by verdict, source, brand) + accuracy page (precision, recall, confusion matrix)
- [ ] **21:00** — Accessibility pass: WCAG AA contrast, keyboard-only run, visible focus, screen-reader labels, verdict shown by icon + text not colour alone, text-size toggle
- [ ] **P1** — Network graph view; read-aloud verdict (browser speech, Arabic + English)
- [ ] **00:00–02:00** — Polish for the video; operate the laptop during the demo

### Agegnew (+ Claude Code) — backend, DB, users, engine

- [x] **11:45** — Repo + FastAPI skeleton; publish the API contract and mock JSON for Nati
- [x] **13:00** — Database (SQLite through SQLAlchemy, Postgres in Docker): users, brands, candidates, scans, verdicts, cases, decisions, domain links
- [ ] **14:00** — Users: admin and analyst roles, login (JWT), seeded accounts; every confirm/dismiss logged with who, when, why
- [x] **15:00** — Datasets: phishing from PhishTank, OpenPhish, Phishing.Database, PhiUSIIL; legit *deep pages* crawled from 4,000 popular sites + UAE official sites; test sites never appear in training
- [x] **17:00** — Engine v1, cheapest layer first: allowlist → threat feeds → URL model → brand impersonation → Arabic/English scam keywords → helpline check → score + reasons EN/AR. `POST /api/batch`. First precision/recall on the held-out set (see Accuracy)
- [ ] **19:00** — PDF evidence report + takedown export (JSON + prefilled abuse email to registrar and host)
- [ ] **21:00** — Graph edges (shared IP, registrar, registration day, favicon, redirect target); thresholds tuned on the held-out set toward low false positives
- [ ] **P1** — LLM vision check for borderline cases
- [ ] **00:00** — Freeze; seed demo data; final accuracy numbers to Samri for the deck

### Simon — workers and discovery

Merged into `main` and wired to the database, engine and API (`backend/app/workers/`). All five radars write cases that appear in the radar feed.

- [x] Job runner + SSRF guard (every request and redirect hop checked)
- [x] Fetcher (Playwright, UAE phone profile `ar-AE`): shorteners, HTTP/JS redirects, screenshot + SHA-256, page text, form field kinds (password, card, OTP, Emirates ID), remote-access / APK links
- [x] Enrichment: RDAP, `.ae` WHOIS (aeDA), DNS, IP → ASN + hosting + abuse contact; `shared_hosting` for free platforms
- [x] Radar 1, lookalikes: typo, ASCII-homoglyph and brand+bait-word domains that exist in DNS
- [x] Radar 2, new certificates (crt.sh), cached when crt.sh is down
- [x] Radar 3, newly registered domains (whoisds daily list) naming a brand
- [x] Radar 4, Search: SerpApi organic results and ads, brand + generic service queries (EN/AR)
- [x] Radar 5, Maps: listings with an unofficial website or a fake helpline number
- [x] Scheduler: runs each radar on its interval, de-duplicates, queues fetches
- [ ] Get a SerpApi key into `.env` (without one, Search/Maps replay saved answers, marked `replayed`)
- [ ] **P1** — Cloaking check: mobile vs desktop fetch, flag differences
- [ ] **00:00** — Freeze; keep `data/cache/` (radar caches) as the demo fallback

### Samri — research, creative, pitch

Your two data files are the first thing everyone else needs: the engine, the lookalike radar, the search radar and the helpline check all read them. Edit them directly on GitHub or locally, then run `python -m scripts.validate_data` from `backend/` (it also runs in the tests).

- [ ] **15:00 — FIRST: `data/scam_themes.json` v1.** Scams that don't copy one brand, so the brand list can't catch them. A starter file with 10 themes is already there; expand each one from real ADP / police / TDRA warnings in the news:
    - Themes: traffic fines and "90% discount" offers, parcel delivery and customs fees ("Dh3 delivery"), visa / residency / domestic workers, fake job offers, property listings, investment and salary-day offers, event tickets and shop deals, fake consumer protection and refunds, account verification / OTP requests, remote-access app installs (AnyDesk, TeamViewer, APK)
    - For each theme: 5–15 English and Arabic **keywords** that appear on scam pages (the engine flags them), 3–5 **search queries** in English and Arabic (Simon's search radar runs them), and the **source links** you used
- [ ] **15:00** — `data/brands.json` v1, about 23 UAE brands: TAMM, UAE PASS, ICP, MOI, RTA fines, Dubai Police, **Abu Dhabi Police** (`adpolice.gov.ae`; Aman 8002626, SMS 2828, 999), **Darb**, **Consumer Protection**, Salik, Emirates Post, Aramex, DEWA, e&, du, Emirates NBD, ADCB, FAB, DIB, Mashreq, ADIB, RAKBANK. For each: official domains, official helplines (copied from the official site), EN/AR names and keywords, logo file in `data/logos/`
- [ ] **15:30** — Branding: confirm product and team name, logo, colours, icon → Nati
- [ ] **16:00** — Ask organizers the open questions at the end of this file; collect 5–10 real UAE scam news stories with links for the deck
- [ ] **16:00** — Two local demo scam pages (fake traffic-fine payment, fake bank login) + one legit control, made with AI tools; Simon serves them locally, never online
- [ ] **20:00** — Deck draft: problem, solution, live demo, architecture, accuracy, UAE focus, police pilot route, honest limitations, team
- [ ] **22:00** — Demo script (3 min) + Q&A cheat sheet
- [ ] **00:00–03:00** — Record and edit the 1-minute demo video
- [ ] **05:00** — Final deck with real accuracy numbers; rehearse the 5-minute version

## Shared contracts (agree by 11:45)

Fixed in the first hour so all four lanes build in parallel. Change one only after telling the whole team.

**Source of truth is code:** [`backend/app/contracts.py`](backend/app/contracts.py) for the shared formats, [`docs/api/README.md`](docs/api/README.md) for the API (with sample JSON for every endpoint).

| Contract | From → to | Fields |
| --- | --- | --- |
| `brands.json` | Samri → everyone | id, name_en, name_ar, category, official_domains[], helplines[], keywords_en[], keywords_ar[], logo |
| `scam_themes.json` | Samri → engine, search radar | id, name_en, name_ar, keywords_en[], keywords_ar[], search_queries_en[], search_queries_ar[], sources[] |
| Candidate | Simon → DB | url, source (lookalike, ct, nrd, search, search_ad, maps, manual, citizen, batch), query, discovered_at, extra {listing_name, phone, address, brand, details} |
| Evidence | Simon → engine | url, final_url, redirect_chain[{url, status}], http_status, screenshot_path, screenshot_sha256, title, text_excerpt, forms[{action, input_types[], field_hints[], sensitive[]}], download_signals[{kind, href, text}], rdap {created, registrar, abuse_email}, ip, asn, hosting_org, hosting_abuse_email, shared_hosting, fetched_at, fetch_error |
| Verdict | Engine → API/UI | url, verdict, score, brand_target, reasons[{code, weight, text_en, text_ar, evidence_ref}], model_version, scored_at |
| API | Agegnew → Nati | See [`docs/api/README.md`](docs/api/README.md) — 14 endpoints, mock data live now |

## Timeline and gates

| Time (UAE) | Milestone | Done means |
| --- | --- | --- |
| 11:00–11:45 | Sync | Contracts, repo and brand list agreed |
| 13:00 | **Gate 1 — foundations** | API and DB serve mock data; brands.json v1 exists; fetcher screenshots one URL; UI shell runs in English and Arabic |
| 17:00 | **Gate 2 — first slice** | One discovered URL flows radar → fetch → engine → UI; first precision/recall number |
| 21:00 | **Gate 3 — P0 complete** | All seven P0 items work end to end |
| 00:00 | **Code freeze** | Bug fixes only after this |
| 00:00–02:00 | Rehearse | Cold-start demo run; record video footage |
| 02:00–05:00 | Package | README, deck, 1-minute video edit |
| 06:00 | **Submit** on Podium+ | Repo link, deck, video |
| 08:00 | Hard deadline | Late submissions are not pre-screened |

## Kill rules

A missed gate cuts scope; it never moves the freeze.

- **13:00, SerpApi key not working:** Search and Maps run on recorded results, labelled as such; the radar leans on lookalikes and crt.sh, which are free.
- **17:00, no end-to-end slice:** everyone stops new work and fixes the slice; all P1 cancelled.
- **17:00, URL model not beating the rules on the held-out set:** drop the model, keep rules + threat feeds.
- **crt.sh slow or down:** use the results cached from the last good pull.
- **LLM slow or expensive:** switch it off; templated EN/AR reasons stay.
- **21:00, P0 not complete:** no P1 starts.
- **00:00:** freeze, whatever state we are in.

## Demo story (3 minutes)

1. **Problem and solution, under 1 minute:** UAE residents meet fake fine-payment and UAE PASS pages through search and Maps; ScamShield finds them first.
2. **Radar feed:** UAE PASS and TAMM lookalike domains registered this week, found with no human input.
3. **Case page:** FRAUD, its score, reasons in Arabic and English, screenshot, WHOIS, hosting, timestamps.
4. **Maps:** a "bank customer care" listing whose phone is not the official helpline.
5. **Action:** export the PDF and takedown email; show the network graph of sibling domains (if P1 shipped).
6. **Citizen checker:** on a phone, in Arabic, paste a link, get a plain verdict read aloud.
7. **Close:** precision and recall on our held-out set, one honest limitation, the route to a police pilot.

## Open questions

- [ ] Organizers: how is the hidden test set run — do judges call our API or CLI, or hand us a list? Do we need a hosted URL?
- [ ] Organizers: is the pitch slot 5 or 10 minutes? (Kickoff slides 16 and 17 disagree.)
- [ ] Team: do we have a SerpApi key with credits, and an LLM API key?
- [ ] Team: final team name and member names for the submission
