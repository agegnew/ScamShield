# ARCHITECTURE.md - System and Threat Architecture

**Status:** Proposed architecture; implementation choices require a team ADR.  
**Scope:** A realistic P0/P1 MVP that can extend into a longer-term digital protection platform.

## 1. Architecture goals

- One browser-to-case vertical slice working within 24 hours.
- Loosely coupled discovery adapters so Search, Places, threat feeds and manual reports share one ingestion contract.
- Strong isolation between the main application and untrusted websites.
- Explainable decision-making: the LLM writes analysis, but does not unilaterally blacklist domains.
- Investigator dashboard that reflects authentic job states and evidence.
- Extension that can receive approved protection rules without requiring a page reload.
- Simple local deployment (Docker Compose) instead of Kubernetes/microservices.

## 2. Logical component view

```mermaid
flowchart TD
  subgraph Input[Discovery and users]
    SERP[SerpApi Google Search]
    MAPS[Google Places API New]
    FEED[Threat feeds / CT optional]
    SUB[Manual URL / citizen submission]
    EXT[WXT Chrome extension]
  end
  subgraph App[Application boundary]
    API[FastAPI REST + SSE / WebSocket]
    QUEUE[Redis + RQ job queue]
    DB[(PostgreSQL)]
    ART[(Evidence artifact store)]
    REVIEW[Review / cases / reporting]
    RULES[Approved protection rules]
  end
  subgraph Untrusted[Isolated investigation environment - untrusted content]
    NET[DNS and URL policy gate]
    BROWSE[Playwright Chromium sandbox]
    SNAP[Evidence collector / screenshots / redirects]
  end
  subgraph AI[Analysis services]
    SIGNAL[Deterministic URL/domain/redirect checks]
    VISION[Vision-capable model + content classification]
    RISK[Risk fusion + explainable rationale]
  end
  WEB[Next.js investigator dashboard]
  SERP --> API
  MAPS --> API
  FEED --> API
  SUB --> API
  EXT --> API
  API --> QUEUE
  API <--> DB
  QUEUE --> NET --> BROWSE --> SNAP
  SNAP --> ART
  SNAP --> SIGNAL
  SNAP --> VISION
  SIGNAL --> RISK
  VISION --> RISK
  RISK --> DB
  DB --> REVIEW
  REVIEW --> RULES
  RULES --> API
  API <--> WEB
  API --> EXT
```

**Critical note:** The logical diagram does not imply that Redis, the investigator API, and an adversarial browser may share unrestricted networking. Their network access must be explicitly segmented.

## 3. User-to-protection sequence

```mermaid
sequenceDiagram
  participant S as Search/Places adapter
  participant A as FastAPI
  participant Q as Worker queue
  participant B as Isolated browser
  participant D as Analyzer/DB
  participant H as Human investigator
  participant E as Browser extension
  S->>A: Candidate URL + source metadata
  A->>A: Normalize, deduplicate, check policy
  A->>Q: Create scan job
  Q->>B: Inspect permitted destination
  B->>D: Screenshots, redirect path, content, hashes
  D->>D: Compute indicators, AI explanation, risk
  D-->>H: Case + evidence + provisional verdict
  H->>D: Confirm malicious or dismiss, reason
  D->>A: Publish versioned confirmed protection rules
  E->>A: Poll approved rules / authenticate
  A-->>E: Rule updates, no secrets
  E->>E: Apply Chrome DNR block rules
```

**Never** publish provisional, unverified risk scores as mandatory extension block rules.

## 4. Services and responsibilities

| Component | Responsibility | Explicitly not responsible for |
|---|---|---|
| `web` | Investigator/citizen UI, SSE stream, cases, reports | Crawling or deciding guilt |
| `api` | Auth, API routes, validation, jobs, cases, persistence | Running untrusted page JS |
| `worker` | Queue processing, safe inspection orchestration, retries | Reading raw passwords or handling payments |
| `sandbox` | Constrained browser visit, screenshots, redirect tracing | Open network access to internal infrastructure |
| `analysis` | Feature extraction, model context, explainable provisional scores | Automatic permanent takedown/block of unconfirmed links |
| `extension` | Local rules, UI warnings, on-page sensitive-field checks where permitted | Reading all device apps or capturing user credentials |
| `storage` | Cases, artifacts, hashes, audit trail | Indefinite retention by default |

## 5. Suggested monorepo

```text
scamshield/
  apps/
    web/                       # Next.js dashboard / citizen UI
    extension/                 # WXT + React + MV3
  services/
    api/                       # FastAPI routes + domain models
    worker/                    # queue consumers and analysis orchestration
  packages/
    contracts/                 # generated OpenAPI types / shared schemas
    ui/                        # shared design tokens / reusable components
  infra/
    compose.yaml               # database, Redis, API, web, worker, sandbox
    nginx/ or caddy/           # demo reverse proxy, TLS if public
  fixtures/
    safe/                      # controlled legitimate pages
    suspicious/                # controlled simulation, not actual phishing
    expected/                  # labels and expected case data
  tests/
    integration/
    e2e/
    security/
  docs/                        # this documentation pack
  .env.example
  README.md
```

A simpler repo with `web/`, `api/`, `extension/`, `worker/` is also acceptable. Favor a working deployment over folder purity.

## 6. Boundary and data flow design

1. **Ingestion:** Search and Places providers return candidate records. Do not assume any result is malicious. Store only provider data permitted by its license; Google Place IDs are generally allowed for persistent storage, but Google Maps content is restricted (see integration guide).
2. **Normalization:** Parse HTTP(S); lower-case/punycode hostname where appropriate; remove tracking fragments when safe; retain both original and canonical URL; hash for deduplication.
3. **Admission:** Reject local, loopback, multicast, link-local, cloud metadata, internal DNS names, unsupported ports, and non-HTTP(S) schemes. Revalidate every redirect and DNS resolution.
4. **Investigation:** Independent browser profile, no preexisting sessions/cookies, disabled downloads, no typed credentials, no payment form submission. Capture first and final URL, timestamps, redirect hops, DOM-derived text, screenshot, links and contact hints.
5. **Signals:** Combine known threat-intelligence matches, unusual URL composition, identity claims, mismatched destination, and visual similarity. Avoid treating new domain age alone as proof.
6. **Decision:** Provisional risk score (0-100) + discrete indicators + confidence/limitations. `UNKNOWN` is valid when inspection fails.
7. **Review:** Analyst confirms/dismisses/escalates; case status and rationale recorded in audit log.
8. **Protection:** Publish only reviewed block indicators and version numbers; extension applies browser-managed rules and supports unblocking and expiry.

## 7. Storage & concurrency

- **PostgreSQL:** candidates, scans, observations, findings, cases, approvals, rules, audits; URLs and screenshots are sensitive and require access controls.
- **Redis/RQ:** asynchronous jobs, bounded concurrency, TTL for ephemeral state; **Postgres is the system of record**.
- **Artifacts:** local private volume during hackathon; production could use S3-compatible storage with short-lived signed URLs. Store hash, capture timestamp, collector version, provenance.
- **Events:** Use SSE for server-to-dashboard status updates; use WebSockets only if genuinely bidirectional interaction is needed. Browser extension can poll versioned feed for MVP simplicity.
- **Idempotency:** key on `(canonical_url, profile, analyzer_version, time_bucket)` for bounded rescans; still retain observation timestamps.
- **Limits:** workers 2-4 concurrent visits initially, ~15-25 sec browser timeout, max 5 redirect hops, max 1-3 MB fetched HTML per page (configuration, not security guarantees). Protect upstream quota.

## 8. Deployment topology (hackathon)

```mermaid
flowchart LR
  B[Judge browser] --> P[Reverse proxy localhost / HTTPS if public]
  X[Chrome extension] --> P
  P --> WEB[Next.js]
  P --> API[FastAPI]
  API --> DB[(Postgres)]
  API --> REDIS[(Redis)]
  REDIS --> WORK[Worker]
  WORK --> SEC[Restricted outbound sandbox]
  WORK --> STORE[(Private evidence volume)]
  WORK --> LLM[LLM API - metadata minimization]
  WORK --> SCAN[Threat intelligence provider]
```

- **Local-only demo** is preferred to public deployment if security review is incomplete.
- Never expose database/Redis to the internet. Keep provider keys server-side. Require token-based auth for investigator routes.
- If outbound visit capability is unavailable, use controlled fixtures labeled **SIMULATED**, never pose as live discovery.

## 9. Availability & failure behavior

| Failure | Expected response |
|---|---|
| SerpApi unavailable/quota exhausted | Manual URL + controlled fixtures; UI displays discovery adapter degraded |
| Google Places missing billing/key | Disable Maps discovery; keep adapter interface and demo with labeled fixture |
| LLM timeout | Deterministic indicators remain, AI finding marked unavailable |
| Worker crashes | Scan becomes `failed` or requeued once; no false clean verdict |
| Screenshot capture blocked | Store metadata and reason; mark visual analysis inconclusive |
| Risk decision uncertain | Use `needs_review`, not confirmed malicious |
| Extension cannot fetch rules | Maintain last trusted signed/versioned rules within expiry; display sync error |

## 10. Architecture decision records to finalize

- ADR-001: Search discovery provider and contingency.
- ADR-002: Maps adapter and compliant data storage.
- ADR-003: Scan isolation and egress enforcement.
- ADR-004: Rule publishing approval model.
- ADR-005: P0 scope and one P1 differentiator.
- ADR-006: SSE vs WebSocket for live dashboard.

See [decisions](docs/17-DECISIONS-AND-RISKS.md), [security](docs/11-SECURITY-AND-PRIVACY.md) and [detector](docs/06-DETECTION-ENGINE.md).
