# Deployment, operations and reproducibility plan

## 1. Deployment targets

**Primary target:** A team laptop or a trusted local host with Docker Compose, Chrome and a stable network. **Secondary target:** A small publicly accessible demo server **only if** TLS, auth, egress restrictions, storage controls, and secrets review are complete. Avoid exposing a raw malicious-site inspection service to the public for hackathon convenience.

This documentation is design, **not** a claim that deployable compose files have been built.

## 2. Proposed Compose services

```text
web        Next.js -> API through reverse proxy
api        FastAPI /api/v1, auth, jobs, evidence endpoints
postgres   cases, findings, decisions, audit
redis      bounded queue / task state
worker     analysis orchestration (no broad internal network access)
sandbox    isolated Chromium/Playwright inspection process
proxy      optional HTTPS route for public demo
artifacts  private mounted volume, never a public static web directory
```

**Critical issue:** Docker Compose `internal` networks alone do not implement all desired internet egress controls. Use a separate enforced network policy, proxy, VM or cloud firewall for untrusted website inspection. Never mount Docker socket or team home directory into the sandbox.

## 3. Environment setup workflow (proposed)

1. Install Docker Compose, Git, browser, Node LTS (for extension development) and Python toolchain.
2. Copy `.env.example` to `.env`, fill secret values locally. Do not commit `.env`.
3. Build containers; run migrations; seed controlled fixtures and one test analyst user.
4. Start services and check `/api/v1/health/live` and `/api/v1/health/ready`.
5. Start local fixture server in an isolated allowed demo network and run end-to-end fixture scan.
6. Load WXT extension unpacked into Chrome profile for optional Guardian demo.
7. Perform cold-restart test, verify case/artefact persistence and rule sync.

**Commands below are illustrative targets; they require an actual application repository:**

```bash
cp .env.example .env
# Edit local secrets in .env (never commit)
docker compose up --build -d
docker compose ps
docker compose logs --tail=100 api worker
# Planned migrations command, once API exists:
docker compose exec api alembic upgrade head
# Planned application test command, once tests exist:
docker compose exec api pytest -q
```

## 4. Configuration table

| Variable | Meaning | Needed for |
|---|---|---|
| `DATABASE_URL` | Postgres connection, private network | P0 |
| `REDIS_URL` | Queue transport | P0 |
| `API_AUTH_SECRET` | Demo/session signing (never browser) | P0 |
| `EVIDENCE_STORAGE_PATH` | Private volume | P0 |
| `SCAN_MODE` | `fixture`, `live`, `mixed` | P0 |
| `SCAN_MAX_REDIRECTS` | Limit redirect hops | P0 |
| `SCAN_TIMEOUT_SECONDS` | Hard browser wall-time bound | P0 |
| `SERPAPI_API_KEY` | Google result discovery | One P0 adapter if selected |
| `GOOGLE_PLACES_API_KEY` | Places lookups | Optional |
| `GOOGLE_WEB_RISK_API_KEY` | URL threat lookup | Optional |
| `URLSCAN_API_KEY` | urlscan.io enrichment | Optional |
| `AI_PROVIDER` | `none`, `gemini`, `openai` | Optional |
| `AI_API_KEY` | Backend-only model access | Optional |
| `ALLOWED_WEB_ORIGINS` | CORS | Public demo |
| `RULESET_SIGNING_KEY` | Optional signed Guardian feed | P1 |

See actual placeholder names in [`.env.example`](../.env.example).

## 5. Health and monitoring

- **Liveness:** process responds, no deep DB queries.
- **Readiness:** checks database and queue; protected endpoint gives sanitized connectivity state.
- **Worker:** jobs completed/failed/retried, queue depth, mean task duration, active browser jobs, quota errors.
- **Providers:** SerpApi, Places, Web Risk and model call failure/latency by provider, no raw secret-bearing URLs in logs.
- **Cases:** status counts and review latency computed from DB, separated by live vs fixture mode.
- **Extension:** last rule version, last successful sync, number of installed active rules (no user browsing history required).

Use structured logs with `request_id`, `scan_id`, `job_id`, `case_id`, state and safe error code. Avoid storing full URL query strings or screenshot content in logs.

## 6. Reproducibility and offline mode

- Version-controlled controlled website fixtures and expected findings.
- `SCAN_MODE=fixture` never contacts unapproved public URLs.
- Provider adapters accept recorded responses in tests; live responses are not silently replayed.
- Every case shows `LIVE` or `SIMULATED` label, including PDF reports.
- Keep seed script idempotent, so a cold demo can start clean.

## 7. Backups and migration policy

- Before migration: `pg_dump` to protected path and artifact volume snapshot; log schema revision.
- Do not commit backup with personal info to Git.
- If migration fails on stage: restore DB+artifact matching snapshot; avoid changing schema under live demo.
- Keep one latest-known-good container/revision and printed rollback steps.

## 8. Incident and rollback response

| Symptom | Action |
|---|---|
| Worker exhausted | Stop intake, cap concurrency, inspect timeouts, clear only safe queued jobs |
| Unexpected network request | Stop sandbox immediately, audit, fix egress policy |
| Provider quota depleted | Switch UI to degraded mode, disable live adapter, run fixtures |
| Incorrect extension block | Revoke rule, republish ruleset, verify removal in Chrome |
| Compromised API key | Rotate key, remove from logs/repos, revoke provider credential |
| Report content mismatch | Freeze demo case, regenerate from authoritative DB, show errors honestly |

## 9. Deployment done means

Cold-start from documented commands, migration succeeds, two controlled scans persist, case PDF renders, no internal network access from sandbox, and a second operator can reproduce without hidden manual steps. Public exposure requires a separate security decision.
