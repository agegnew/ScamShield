# Proposed FastAPI API specification

**Base URL:** `/api/v1`. **Contract status:** Design proposal, not an implemented endpoint list. Use generated OpenAPI from the running service as source of truth once built.

## 1. General conventions

- JSON UTF-8; timestamps ISO 8601 UTC; IDs UUID strings; `request_id` included in errors and logs.
- Use `Authorization: Bearer <token>` for investigator endpoints. Extension feed uses scoped read-only token or signed public distribution with strong integrity and expiry.
- Long operations return **202 Accepted** and a job ID; do not hold HTTP connections for an entire browser scan.
- Pagination: `limit` max 100 + opaque cursor; stable sort by `(created_at,id)`.
- Idempotency for submitting scans via `Idempotency-Key` request header.
- Audit all analyst mutations and rule publishing.

## 2. Endpoint matrix

| Method | Route | Role | Purpose |
|---|---|---|---|
| GET | `/health/live` | public local | Process liveness (no secrets) |
| GET | `/health/ready` | ops | DB/Redis status, sanitized |
| POST | `/scans` | user/analyst | Submit URL for scan |
| GET | `/scans/{scan_id}` | user owner/analyst | Poll status and summary |
| GET | `/scans/{scan_id}/observations` | analyst | Technical evidence |
| POST | `/discovery/queries` | analyst | Start authorized SERP/Places query |
| GET | `/discovery/runs/{run_id}` | analyst | Source status, candidate counts |
| GET | `/cases` | analyst | Case list/filter/pagination |
| GET | `/cases/{case_id}` | analyst | Case + findings + artifacts |
| POST | `/cases/{case_id}/decisions` | analyst | Confirm/dismiss/escalate, with reason |
| GET | `/cases/{case_id}/report.pdf` | analyst | Redacted evidence report |
| GET | `/artifacts/{artifact_id}` | analyst | Authorized artifact stream/presign |
| GET | `/events` | analyst | SSE job/case state updates |
| GET | `/guardian/rules` | extension | Versioned approved rules only |
| POST | `/guardian/rules/publish` | admin | Publish reviewed rules |
| POST | `/guardian/rules/rollback` | admin | Revoke erroneous rules |
| POST | `/reports/citizen` | citizen, P3 | Consent-based suspicious-link report |

## 3. Example: submit scan

```http
POST /api/v1/scans
Content-Type: application/json
Idempotency-Key: 1dcd54f7-unique-demo

{
  "url": "https://suspect.example.test/landing",
  "source": "manual",
  "profile": "desktop-en",
  "consent_to_remote_analysis": true
}
```

```json
{
  "scan_id": "00000000-0000-4000-8000-000000000101",
  "case_id": "00000000-0000-4000-8000-000000000201",
  "status": "queued",
  "capture_mode": "fixture",
  "status_url": "/api/v1/scans/00000000-0000-4000-8000-000000000101"
}
```

**Example-only URL:** `.test` is reserved; the response is synthetic, not evidence of a real malicious domain.

## 4. Example: case detail

```json
{
  "case_id": "00000000-0000-4000-8000-000000000201",
  "status": "unreviewed",
  "triage": {"score": 76, "band": "high", "calibrated_probability": null},
  "capture_mode": "fixture",
  "candidate": {"url": "https://suspect.example.test/landing", "source": "fixture"},
  "findings": [
    {
      "kind": "redirect",
      "severity": "high",
      "summary": "Payment destination differs from stated organization",
      "evidence_id": "art-redirect-1",
      "score_contribution": 15,
      "limitations": "Legitimate services can use payment partners"
    }
  ],
  "observations": [
    {"id": "obs-1", "profile": "desktop-en", "status": "completed", "screenshot_id": "art-img-1"}
  ],
  "human_decision": null
}
```

## 5. Example: analyst decision

```http
POST /api/v1/cases/{case_id}/decisions
Content-Type: application/json

{"action":"confirm","reason":"Controlled fixture: known test phishing landing page","evidence_ids":["art-img-1"]}
```

Require reason (min length) and authorization. Confirmation may make case **eligible** for a protection rule, but publication should be a separate explicit action.

## 6. Extension rules feed

```json
{
  "version": 42,
  "generated_at": "2026-11-24T18:00:00Z",
  "expires_at": "2026-11-25T18:00:00Z",
  "rules": [
    {
      "id": 1001,
      "action": "block",
      "host": "suspect.example.test",
      "source_case_id": "00000000-0000-4000-8000-000000000201",
      "expires_at": "2026-11-25T18:00:00Z"
    }
  ],
  "checksum": "sha256:<calculated digest>",
  "signature": "<optional signed-feed signature>"
}
```

Never distribute PII, unredacted reports, or threat provider data that cannot legally be redistributed.

## 7. Error codes

| HTTP | `code` | Meaning |
|---|---|---|
| 400 | `INVALID_URL` | Parse/scheme failure |
| 403 | `SCAN_POLICY_REJECTED` | Internal/private/forbidden target |
| 401 | `UNAUTHENTICATED` | Login required |
| 403 | `FORBIDDEN` | Role denied |
| 404 | `NOT_FOUND` | Missing or inaccessible resource |
| 409 | `INVALID_STATE_TRANSITION` | Review/approval race |
| 422 | `VALIDATION_ERROR` | Schema invalid |
| 429 | `RATE_LIMITED` | Local/provider quota exhausted |
| 502 | `UPSTREAM_UNAVAILABLE` | External provider outage |
| 503 | `WORKER_UNAVAILABLE` | Queue/workers unavailable |

Example: `{ "error": { "code": "SCAN_POLICY_REJECTED", "message": "Target not permitted", "request_id": "..." } }`.

## 8. Auth and rate limits

- Demo may use a preconfigured local analyst account, but routes must still be protected if exposed.
- Never embed a privileged API secret in the extension or frontend.
- Rate-limit `POST /scans`, discovery launches and report generation.
- CSRF protection for cookie sessions, CORS only to known origins; cap URL length and JSON size.
- Extension feed token must be read-only, short-lived/rotatable; prefer signed rule bundles.

## 9. SSE events (if chosen)

Events: `scan.queued`, `scan.running`, `scan.completed`, `scan.failed`, `case.updated`, `rules.published`. Every event includes `id`, `occurred_at`, `case_id`/`scan_id`, `source_mode`, and `schema_version`. Treat events as hints: clients refresh authoritative case state via REST. Use polling fallback.
