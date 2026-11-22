# Architecture decisions, project risks and unknowns

**Status:** Proposed ADRs, to be confirmed by teammates. Do not silently turn draft choices into established implementation facts.

## 1. Decision log

| ID | Question | Proposed choice | Status / reopen when |
|---|---|---|---|
| ADR-001 | Architecture style? | Modular FastAPI monolith + isolated async worker | Proposed; reopen if team has better proven stack |
| ADR-002 | Discovery API? | SerpApi Google Search primary, Places secondary | Pending credentials/terms |
| ADR-003 | Unsafe browser isolation? | Restricted Playwright/Chromium worker and network egress firewall | Security acceptance required |
| ADR-004 | AI as security judge? | No; structured evidence support + deterministic scoring + human approval | Proposed policy |
| ADR-005 | Extension block policy? | Approved confirmed indicators only, versioned/expiring | Proposed safety gate |
| ADR-006 | Realtime transport? | SSE plus polling fallback, no complex sockets needed | Proposed |
| ADR-007 | Geography visualization? | Case table first, map optional after data permits | Proposed |
| ADR-008 | Data store? | PostgreSQL and local private artifact volume | Proposed |
| ADR-009 | Hero differentiator? | Guardian OR Ghost Agent/TrustChain after P0 | **Open, decide by hour 14** |
| ADR-010 | Product name/team name? | Working ScamShield AI; team name undecided | Open |
| ADR-011 | Mobile? | Future explicit-consent companion, no phone scanning from web alone | Proposed limitation |
| ADR-012 | Public deployment? | Local-only unless separate security acceptance | Proposed |

## 2. Risk register

Scale: impact and likelihood H/M/L are estimates, not measured probabilities.

| Risk | Impact | Likelihood | Mitigation | Owner |
|---|---|---|---|---|
| Live API quota exhausted | H | M | Prevalidate key; fixture fallback, visible mode | Integrations lead |
| Google Places billing/terms conflict | H | M | Check Enterprise SKU and storage rules; limit Place IDs | Integrations lead |
| Website scanner SSRF | H | M | Harden network egress + tests; local demo if not ready | Security lead |
| Model hallucination / prompt injection | H | M | Structured evidence; no autonomous block | AI lead |
| False-positive browser block | H | M | Human confirmation, TTL, rollback | Extension lead |
| Chrome extension lifecycle/permissions | M | M | WXT, Chrome DNR tests, local storage | Extension lead |
| No time for all features | H | H | Hard P0/P1 gates, scope freeze | Team lead |
| Search/Maps content data licensing | H | M | Use provider rules; store permitted metadata only | Product lead |
| Demo Wi-Fi failure | M | M | Pre-cached fixture, local server, recording | Demo lead |
| Team merge conflict | M | M | Shared schema, small PRs, checkpoints | Team lead |
| Unrealistic "real-time" claims | H | M | Exact known vs unknown guarantees in UI | Product lead |
| Screenshot PII leak | H | M | Privacy Cloak, redact, restricted store | Security lead |
| Controlled demo mistaken for live result | H | M | Fixture banner, labels in PDF and pitch | Demo lead |
| Team formation/registration miss | H | M | Recheck live organizer page; urgent action | Team lead |

## 3. Assumptions to validate

- We have 3+ individually registered members before organizer team deadline.
- The event permits the chosen amount of pre-event preparation; confirm what prebuilt code is allowed.
- The team has Chrome, Docker-compatible machines and API accounts/credits.
- Local fixture scanning with private domain names is reliably configured and isolated.
- At least one person can build and debug the browser extension in time.
- A reviewer is designated to approve or dismiss cases.
- We can show a real source-query result without violating provider terms.

## 4. Decision procedure

For each ADR, record: **context**, **constraints**, **options**, **decision**, **consequences**, **owner**, **date**, **test/proof**. Keep decisions reversible until P0 is stable. Use [ADR template](../templates/ADR-TEMPLATE.md).

## 5. Emergency scope reductions

| If this fails | Reduce to |
|---|---|
| Maps billing/API | SERP discovery only + controlled Maps fixture labeled |
| SERP API | Manual URL and authorized feed intake, controlled SERP fixture |
| LLM vision | Deterministic + screenshot evidence; explain no AI verdict |
| Real-time push | Polling case statuses every few seconds |
| Browser extension | Show investigator-case PDF and Ghost Agent instead |
| Playwright sandbox security | Local fixture inspection only; no open internet scanning |
| Graph clustering | Evidence table of related URLs, not node animation |
| Native phone/AR | Pitch roadmap, don't mock as built |

## 6. Open questions for organizer / legal review

- Final team maximum, allowed pre-build and external API use?
- Are real malicious URLs permitted during demo, or should only controlled fixtures be shown?
- Are there limits on data retention, hosting region, internet connectivity and recordings?
- Are there restrictions on post-submission changes and final-presentation materials?
- Does organizer supply a threat dataset, judging rubric or testing endpoint?

Unanswered questions should not block safe P0 preparation; choose conservative implementation and document assumptions.
