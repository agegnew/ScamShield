# Product Requirements Document (PRD)

**Version:** v0.1 - planning only. **Owner:** team lead (unassigned). **Target submission:** 25 November 2026, 08:00 UAE time.

## 1. Problem and goals

Fraudulent websites can appear in ordinary search and Maps journeys. A usable detection system must identify candidate URLs, inspect them with technical and visual evidence, prioritize review, and offer safe responses. The hackathon prototype must prove those steps work on real or clearly labeled controlled data.

### P0 goals

- P0-G1: User can submit a URL; backend returns a tracked job ID in under a typical API timeout.
- P0-G2: At least one discovery adapter returns candidate links traceable to original query/source.
- P0-G3: Browser inspection, deterministic signals and optional vision analysis produce structured findings.
- P0-G4: Investigator can review a case, see evidence, change status, and export PDF.
- P0-G5: App stays honest about pending, unavailable and inconclusive states.
- P0-G6: Controlled malicious and benign scenarios prove expected behavior without exposing secrets.

### P1 goals (conditional)

- P1-G1: Chrome extension applies a confirmed-domain blocking rule and can roll it back.
- P1-G2: Ghost Agent/TrustChain traces a safe example of a deceptive redirect journey.
- P1-G3: Detect one related-case cluster with explainable shared indicators.

### Outside required scope

Phone companion scanning, voice assistant/chatbot, AR camera UI, public user accounts, historical domain monitoring, advanced clustering at scale, automated takedown and formal police system integration. See the [feature catalog](03-FEATURE-CATALOG.md) for optional features and statuses.

## 2. Functional requirements and acceptance

| ID | Priority | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-01 | P0 | Manual URL submission | Valid HTTP(S) URL creates a case/scan; malformed/forbidden URL rejected |
| FR-02 | P0 | Search/Maps discovery | At least one configured adapter yields candidate with source, query and timestamp; fixture mode is labeled |
| FR-03 | P0 | Deduplication | Canonical repeat is linked to existing URL; new observation can still be requested |
| FR-04 | P0 | Scan job lifecycle | `queued -> running -> completed/partial/failed`; no silent stuck jobs |
| FR-05 | P0 | Browser observation | Capture attempted and final URL, redirects, timestamp and screenshot where safe |
| FR-06 | P0 | Explainable findings | Each finding has type, severity, explanation, provenance, and optional artifact reference |
| FR-07 | P0 | Risk rating | 0-100 triage score + classification; `unknown` supported for errors |
| FR-08 | P0 | Investigation queue | Filter by status/severity/source, open detailed cases |
| FR-09 | P0 | Human case review | Analyst confirms/dismisses; reason and audit record stored |
| FR-10 | P0 | PDF report | Case IDs, timestamps, URLs, indicators, limits, screenshots/links, analyst decision |
| FR-11 | P0 | Safe handling | Internal IPs blocked, sandbox isolated, timeouts bounded, no credential entry |
| FR-12 | P1 | Guardian extension | Confirmed test domain blocked using MV3 DNR; unblock possible |
| FR-13 | P1 | Trace redirects | Link journey displays evidence-backed hops, not invented steps |
| FR-14 | P1 | Connected sites | Show relation with source evidence (e.g. same redirect target) |
| FR-15 | P2 | MirrorLens | Compare at least two permitted browser profiles and show meaningful differences |
| FR-16 | P2 | Credential Tripwire | Content script warns before submit on flagged test domain; never reads field values |
| FR-17 | P2 | Reality Switch | Verified alternative offered only from a curated trusted source |
| FR-18 | P3 | Scam Rescue | Clear incident guidance, safe official reporting links and user consent |

## 3. Representative user stories

- **Investigator:** As an analyst, I want to inspect a suspicious search result with timestamps and redirect evidence so that I can decide whether to escalate it.
- **Investigator:** As an analyst, I need to dismiss a false positive and document why so that the extension does not block a legitimate site.
- **User:** As a browser user, I want a clear reason and safe route when a confirmed malicious link is blocked.
- **User:** As a privacy-conscious citizen, I want to redact identifying details before reporting a screenshot.
- **Judge:** As a reviewer, I want the system to classify both a controlled fraudulent and a controlled legitimate page without changing the result manually.

## 4. Non-functional requirements (targets, not measured claims)

| Dimension | Prototype target | Method |
|---|---|---|
| Job acknowledgement | < 1 second in local dev | API timed smoke tests |
| Basic non-browser URL features | < 3 seconds when network available | Time 20 URLs; exclude provider outage |
| Full browser scan | Aim < 30 seconds per candidate | Time bounded requests; record P50/P95 |
| Analyst case page | Responsive and navigable on laptop | Keyboard and viewport test |
| Safety | 0 successful internal/metadata egress tests | Automated network policy suite |
| Resilience | Explicit degraded statuses | Disable each provider in rehearsal |
| Auditability | Every case decision has timestamp, user, reason | Database assertions |
| Accessibility | Critical tasks keyboard navigable; EN/AR RTL where implemented | Manual keyboard and contrast checks |

These are engineering targets to verify, **not** performance promises.

## 5. Risk and scoring behavior

- `UNKNOWN`: scan unavailable, blocked by policy, failed, or insufficient evidence; never silently class as safe.
- `LOW` (0-29), `REVIEW` (30-59), `HIGH` (60-79), `CRITICAL` (80-100) are **illustrative thresholds requiring calibration**.
- `CONFIRMED_MALICIOUS` is an **analyst state**, not a score; two concepts must never be conflated.
- Only analyst-approved confirmed indicators become extension block rules; rules must support TTL, appeal and rollback.

## 6. Dependencies and assumptions

- Search and Maps providers require valid accounts, pricing/quota review, and compliance with API terms.
- AI model access is optional to preserve deterministic fallback; API keys must not be committed.
- Browser isolation requires properly configured restricted network egress, not simply Playwright contexts.
- No sensitive user data should enter public urlscan submissions or external LLM requests by default.

## 7. Definition of Done (P0)

- A teammate other than the author can follow a written setup/runbook.
- Seeded safe/suspicious fixtures run from a clean environment.
- A *live* provider path is exercised and labeled separately where credentials permit.
- Database persists jobs, cases, evidence, decisions and logs.
- Dashboard shows no pretend live telemetry.
- Safety tests and end-to-end smoke tests pass.
- Demo/report can be regenerated after restart; failure mode rehearsed.
- A truthful limitations slide is ready.

## 8. Open product questions

1. Which primary discovery source has working keys and quota today?
2. Which P1 differentiator is the hero: Ghost Agent/TrustChain or Guardian?
3. Which verified UAE domains can we use as comparisons without misusing trademarks?
4. Who will review/approve block rules in demo?
5. What real or controlled evaluation set is available, legally and safely?

Close these before full implementation; log decisions in [ADRs](17-DECISIONS-AND-RISKS.md).
