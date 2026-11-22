# Stack, technologies, deployment decisions

## 1. Recommended architecture style

**Modular monolith for the API + separately isolated worker/sandbox + one extension**. The API owns authentication, cases and orchestration. It does not execute adversarial browser content. Worker concurrency is bounded. Avoid introducing Kubernetes, Neo4j, Kafka, or separate microservices during a 24-hour contest.

## 2. Stack choices

| Area | Primary choice | Reason | Alternative / fallback |
|---|---|---|---|
| Frontend | Next.js + TypeScript + React | Fast UI and routing; typed contracts | Vite + React if team faster |
| UI | Tailwind CSS + shadcn/ui + Lucide | Accessible patterns and responsive layout | Plain Tailwind |
| Data visualization | Recharts for charts, React Flow for optional link graph | Fast to build | SVG diagram or table in P0 |
| Backend | FastAPI + Pydantic | Python-native asynchronous workflows and typed OpenAPI | Flask or NestJS if team already built it |
| ORM / migrations | SQLAlchemy 2 + Alembic | Explicit Postgres schema | SQLModel or raw SQL for narrow scope |
| DB | PostgreSQL | Structured cases and queryable relationships | SQLite local-only emergency demo |
| Queue | Redis + RQ | Simple worker/job separation | FastAPI BackgroundTasks **only** for tiny controlled tests |
| Website inspection | Playwright Python + Chromium | Screenshots, browser contexts, redirects | urlscan private scan with key; limited fallback |
| URL / domain | `urllib.parse`, `idna`, DNS resolver, RDAP client | Normalization and domain metadata | Skip RDAP if quota/failures |
| Visual/content AI | Gemini or OpenAI vision-capable model | Screenshot and page-analysis explanations | Deterministic heuristics only |
| Threat feed | Google Web Risk or urlscan.io | Known-bad match / evidence enrichment | Local seeded confirmed indicators |
| Search results | SerpApi `engine=google` | Structured organic results and location/language | Controlled SERP fixture, clearly labeled |
| Maps/Places | Google Places API (New) | Place lookup and `websiteUri` | Controlled Places fixture, clearly labeled |
| Actual geographic map UI | Google Maps JS API if truly needed | Place display | Skip map UI in P0; use list/case table |
| Chrome extension | WXT + React + TypeScript, Manifest V3 | Good dev DX and extension packaging | Plain MV3 TS |
| Block engine | `chrome.declarativeNetRequest` | Browser-managed pre-request block on known rules | Warning-only if permissions constrained |
| Realtime UI | SSE (simple server push) | Minimal state overhead for dashboard | 2-5 sec polling; WebSocket optional |
| Artifact store | Private local volume, then S3-compatible object store | Screenshots and report artifacts | PostgreSQL metadata + local files |
| PDF | WeasyPrint or Playwright PDF render | HTML-to-PDF consistent reports | ReportLab for safer pure Python templates |
| Containers | Docker Compose | Reproducible hackathon environment | `make` scripts if Docker fails |
| CI | GitHub Actions | Lint, test, build | Local smoke script |

**Versioning policy:** Resolve actual latest compatible versions during implementation; lock dependency versions and commit lockfiles. These docs intentionally do not invent specific release numbers.

## 3. Browser extension decision

WXT supports React/TypeScript and builds MV3. Use:

- Background service worker for alarms, approved rule sync and state changes.
- `declarativeNetRequest` dynamic rules for approved/confirmed indicators only.
- Popup for manual scan, rule sync state, protection status and report action.
- Optional content script for Tripwire on explicitly permitted hosts; inspect **field type and form action**, not typed values.
- `chrome.storage.local` for durable rule version and state; **do not assume service worker stays alive**.
- Avoid `<all_urls>` permissions during MVP unless explicitly necessary. Explain prompts honestly.

**Important:** DNR is synchronous for rules already installed in Chrome. A newly encountered unknown URL that requires remote AI analysis cannot be guaranteed blocked before its initial network request. Instead display warning/interstitial when supported, or analyze after navigation. Never claim an impossible universal pre-request verdict.

Official references: https://wxt.dev/ ; https://developer.chrome.com/docs/extensions/reference/api/declarativeNetRequest ; https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle

## 4. Google Search and Maps differentiation

- **SERP:** SerpApi's Google engine returns structured `organic_results` (title, link, rank and related fields) and supports UAE localization (`gl=ae`, `hl=en` or `ar`, location parameter). Ensure plan/quota/usage terms permit your intended use.
- **Places:** Google Places API (New) can retrieve `websiteUri` with a `FieldMask` such as `id,displayName,websiteUri` (exact fields vary by API method). `websiteUri` is an **Enterprise SKU**, not a free field. Avoid blanket `*` requests.
- **Google Maps visualization:** Optional. The challenge includes Maps discovery; a fancy map UI is not a substitute for examining listing websites.
- **Caching/licensing:** Follow Maps Platform service terms. Place IDs have a documented retention exception, but unrestricted long-term caching of Google Maps content, scraping, or export is not allowed. Consult official policy before indexing or building derived datasets.

Official references: https://serpapi.com/search-api ; https://developers.google.com/maps/documentation/places/web-service/place-details ; https://developers.google.com/maps/documentation/places/web-service/policies

## 5. AI role split

**Deterministic:** Hostname similarity/IDN, redirect counts/destinations, threat-list match, field presence, TLS/hostname metadata, page content features.

**LLM-assisted:** Explain deceptive claims, compare screenshots with consented references, suggest likely brand intent and narrative, summarize indicators in EN/AR. Require JSON schema, evidence citations, no autonomous approval.

**Never feed:** Passwords, OTP values, raw payment card details, sensitive screenshots without redaction and consent. Prompt injection from page text is untrusted; AI must never control admin tools or scan policy.

## 6. Developer requirements

- Node.js LTS, pnpm or npm; Python 3.12+ if compatible; Docker Engine/Compose; Chrome dev mode; Git.
- All keys in `.env` / secrets manager, no secrets in JavaScript bundles.
- Local smoke test should run without paid services using controlled fixtures; UI must display mode.
- CI runs lint/typecheck, unit, integration and extension build. Container images pinned to digest before final demo if time allows.

## 7. A minimal infrastructure footprint

- `postgres` 1 instance
- `redis` 1 instance
- `api` 1 instance
- `worker` 1 instance with browser-inspection jobs isolated by stronger sandbox policy
- `web` 1 instance
- optional `reverse-proxy` 1 instance

Do **not** expose Postgres/Redis ports publicly. Do not let the worker inspect internal services. Limit CPU/memory for browser jobs and stop after timeouts.

## 8. Decision summary

| Decision | Position |
|---|---|
| Development topology | Modular monolith plus isolated worker |
| UI | Next.js + TS |
| API | FastAPI |
| Background jobs | Redis + RQ |
| Browser | Playwright Chromium in restricted sandbox |
| Search | SerpApi (pending quota/key) |
| Maps | Places API (New), websiteUri (Enterprise billed) |
| Threat list | Web Risk or curated fixtures; no unlicensed redistribution |
| Main hero candidate | Guardian OR Ghost Agent/TrustChain after P0 |
| Mobile platform | Future native companion, not generic website phone scan |
