# ScamShield AI - Digital Immune System

> **Status:** Planning / architecture baseline (v0.1, 22 November 2026).  
> **Event:** 42 Abu Dhabi x Abu Dhabi Police, ScamShield AI Hackathon.  
> **Mission:** Discover fraudulent links and websites early, explain the evidence, help investigators respond, and protect people at the moment of risk.  
> **This repository contains design documentation, not a completed application.**

## 1. Executive summary

ScamShield AI is a UAE-focused fraud-discovery and protection platform. Unlike a basic paste-a-URL checker, the product is designed to (1) find suspicious URLs in search results and business listings, (2) safely inspect their technical and visual behavior, (3) connect related threats into investigations, (4) help humans verify findings, and (5) deliver approved warnings to browser users. Longer term, it can provide victim recovery support, a phone companion, QR-camera protection, payment safety checks, and privacy-aware citizen reporting.

**One-line pitch:** *Discover -> Investigate -> Connect -> Protect -> Rescue.*

### The official challenge versus our product choices

**Official problem:** Detect fraudulent websites and links used in cybercrime and financial fraud across the open internet, **including search-engine results and Maps**, emphasizing **early identification**. The challenge does **not** prescribe a crawler, a dashboard, a particular AI model, browser blocking, mobile software, or integration with police systems. Those are our proposed differentiators.

**Proof obligation:** The organizer requires a **working product or MVP**; presentations and mockups alone are insufficient. A clean, measured working pipeline outranks many unfinished features.

## 2. What we will demonstrate

The target end-to-end scenario is:

1. A search-query adapter or Maps/place adapter discovers candidate URLs, while the UI also accepts manually submitted URLs.
2. A queue sends permitted candidates to a sandboxed analyzer; the analyzer records redirects, page content, DNS/domain signals, and screenshot artifacts.
3. Deterministic indicators and a vision-capable model generate **evidence-linked findings**; a scoring engine calculates **risk**, not a declaration of guilt.
4. A dashboard displays the case, evidence, and human review status; a PDF report can be exported.
5. A **confirmed** demo threat flows to an opt-in Chrome extension and is blocked through a browser-managed rule. Unknown sites receive warnings, not unsupported guarantees of pre-request blocking.

**Gold demo:** One controlled suspicious journey discovered, investigated, confirmed, exported, then blocked in a second browser profile. Show a benign lookalike control case to demonstrate restraint.

## 3. Delivery levels

| Level | Name | Required result |
|---|---|---|
| P0 | Foundation | Working end-to-end MVP: at least one discovery route plus manual scan, analysis, explainable risk, dashboard, evidence/report |
| P1 | Competitive Edge | One integrated differentiator: Guardian confirmed-domain block, Ghost Agent/TrustChain, or Scam DNA; choose by dependency and stability |
| P2 | Moonshot | A polished extra: MirrorLens, Tripwire, Reality Switch, or AR QR demonstration; only if P0/P1 are stable |
| P3 | Product Roadmap | Phone Connect, Rescue, SafePay, community intelligence, more accessibility and integrations; not commitments for 24-hour submission |

See [Phases and schedule](docs/04-PHASES-AND-ROADMAP.md) and [Feature catalog](docs/03-FEATURE-CATALOG.md).

## 4. Event facts and planning assumptions

Verified from the live [Podium+ event page](https://podium.aevsoft.cc/HackathonMngtWebApp/event.php?e=ad-police-x-42ad-hackathon&lang=en) on **22 November 2026**:

| Event | Current posted date/time (UAE) |
|---|---|
| Registration closes | **Sunday, 22 Nov 2026, 11:59 PM** |
| Hackathon begins | Tuesday, 24 Nov 2026, 8:00 AM |
| Team formation deadline | Tuesday, 24 Nov 2026, 11:00 AM |
| Submission deadline | Wednesday, 25 Nov 2026, 8:00 AM |
| Elimination round | Wednesday, 25 Nov 2026, 10:00 AM |
| Finalist presentations | Thursday, 26 Nov 2026 |
| Awards | Monday, 30 Nov 2026 |
| Minimum team size | At least 3; initial call suggested 3-5, verify any maximum with organizers |

**Important correction:** The original circulated message mentioned a November 23 registration close. The live event page instead says **November 22**. Use the live organizer page as source of truth, recheck before acting. **The coded MVP window is 24 hours**, not three full days of development.

## 5. Proposed stack

- **Web:** Next.js, React, TypeScript, Tailwind CSS, shadcn/ui.
- **API:** FastAPI, Pydantic, SQLAlchemy, Alembic.
- **Data:** PostgreSQL; Redis + RQ workers; local filesystem or S3-compatible object storage for artifacts.
- **Investigation:** Python URL/DNS/RDAP utilities plus isolated Playwright/Chromium workers.
- **AI:** Vision-capable LLM as an explanatory signal; deterministic logic remains authoritative for policy.
- **Discovery:** SerpApi for Google search; Google Places API (New) for Places website links; controlled fixtures when external APIs fail.
- **Threat intelligence:** Google Web Risk and/or urlscan.io, subject to keys, quotas, privacy settings, and terms.
- **Extension:** WXT + React + Manifest V3 + `declarativeNetRequest` for approved/confirmed URL blocking.
- **Visualization/transport:** REST and SSE or WebSocket; avoid needless infrastructure.
- **DevOps:** Docker Compose, GitHub Actions, environment variables and documented backups.

This is the recommended starting point, **not** a claim that licenses, pricing or access are already secured. See [Technology decisions](docs/05-TECH-STACK.md).

## 6. Design principles

1. **Proof over promise.** No fabricated scans, unmeasured accuracy, or fake detection lead times.
2. **Investigate safely.** Untrusted URLs never execute in the API container or reach internal networks.
3. **Evidence before verdict.** Findings cite captured signals; distinguish suspicion, confidence, and confirmed findings.
4. **Human-controlled enforcement.** Only vetted, confirmed indicators automatically enter blocking feeds in the MVP.
5. **Privacy first.** No passwords or OTPs collected; redact screenshots; no covert phone monitoring.
6. **Fail clearly.** If search/Maps/AI is unavailable, show degraded mode; don't silently substitute fixtures as live data.
7. **Accessible by design.** EN/AR + RTL where implemented, keyboard access, readable explanations, meaningful text and contrast.

## 7. Repository documentation map

| File | Purpose |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System diagrams, components, trust boundaries, deployment and decisions |
| [docs/00-INDEX.md](docs/00-INDEX.md) | Navigation and reading order |
| [docs/01-PROJECT-OVERVIEW.md](docs/01-PROJECT-OVERVIEW.md) | Vision, users, problem framing, boundaries |
| [docs/02-PRD-REQUIREMENTS.md](docs/02-PRD-REQUIREMENTS.md) | Requirements, user stories, acceptance criteria |
| [docs/03-FEATURE-CATALOG.md](docs/03-FEATURE-CATALOG.md) | **Every brainstormed feature**, selection status and limitations |
| [docs/04-PHASES-AND-ROADMAP.md](docs/04-PHASES-AND-ROADMAP.md) | Hour-by-hour hackathon plan, gates and post-event phases |
| [docs/05-TECH-STACK.md](docs/05-TECH-STACK.md) | Technologies, alternatives and why |
| [docs/06-DETECTION-ENGINE.md](docs/06-DETECTION-ENGINE.md) | Technical pipeline, scoring, AI prompts and failure handling |
| [docs/07-DATA-MODEL.md](docs/07-DATA-MODEL.md) | Entities, schema, relationships and retention |
| [docs/08-API-CONTRACTS.md](docs/08-API-CONTRACTS.md) | Proposed routes, auth, examples and errors |
| [docs/09-GUARDIAN-EXTENSION.md](docs/09-GUARDIAN-EXTENSION.md) | Browser extension design and browser limitations |
| [docs/10-UX-AND-ACCESSIBILITY.md](docs/10-UX-AND-ACCESSIBILITY.md) | Information architecture, inclusivity, user flow and copy |
| [docs/11-SECURITY-AND-PRIVACY.md](docs/11-SECURITY-AND-PRIVACY.md) | Threat model, SSRF, isolation, privacy and reporting safeguards |
| [docs/12-TESTING-AND-METRICS.md](docs/12-TESTING-AND-METRICS.md) | Evaluations, safety tests, accuracy and performance |
| [docs/13-DEMO-AND-PITCH.md](docs/13-DEMO-AND-PITCH.md) | Live demo, judge questions, failover and submission checklist |
| [docs/14-TEAM-EXECUTION.md](docs/14-TEAM-EXECUTION.md) | Roles, ownership, coding agreements and task plan |
| [docs/15-DEPLOYMENT-AND-OPS.md](docs/15-DEPLOYMENT-AND-OPS.md) | Local and demo deployment, logs and recovery |
| [docs/16-INTEGRATIONS-AND-COSTS.md](docs/16-INTEGRATIONS-AND-COSTS.md) | Search, Maps, AI, risk feeds, licensing and quotas |
| [docs/17-DECISIONS-AND-RISKS.md](docs/17-DECISIONS-AND-RISKS.md) | ADRs, assumptions, unknowns and contingency plans |
| [docs/18-SOURCES.md](docs/18-SOURCES.md) | Verified official documentation and references |
| [docs/19-USER-JOURNEYS.md](docs/19-USER-JOURNEYS.md) | Investigator, extension, citizen, recovery and mobile journeys |
| [docs/20-EVIDENCE-AND-REPORTING.md](docs/20-EVIDENCE-AND-REPORTING.md) | Chain of custody, report format and admissibility disclaimers |
| [docs/21-MOBILE-AND-AR-ROADMAP.md](docs/21-MOBILE-AND-AR-ROADMAP.md) | Phone pairing, Android/iOS limitations, camera QR UX |
| [docs/22-CITIZEN-SAFETY-AND-RESCUE.md](docs/22-CITIZEN-SAFETY-AND-RESCUE.md) | SafePay, ChatSense, Trusted Circle, Rescue, SafeView |
| [docs/23-INNOVATION-EXPERIMENTS.md](docs/23-INNOVATION-EXPERIMENTS.md) | Competitive ideas, experiments and measurement discipline |
| [templates/](templates/) | Issue, ADR and demo checklists |
| [.env.example](.env.example) | Placeholder configuration, never credentials |

## 8. What is explicitly not promised

- No ability for a **website alone** to scan all files/apps on a connected phone. Phone monitoring requires a separate, consent-based app and OS permissions.
- No guarantees of detecting every scam, stopping payment transfers, or accessing private WhatsApp messages.
- No autonomous arrests, enforcement actions, public naming of suspects, takedowns, or official police integration.
- No real-time pre-network blocking of all previously unknown URLs by an MV3 extension; confirmed rules can block before request, while asynchronous checks take time.
- No claim that a domain age, a valid TLS certificate, or an AI output proves criminality.

## 9. First steps for the team

1. Confirm registrations/team and obtain API keys under team-controlled accounts.
2. Read **PRD**, **Architecture**, **Security**, **Phases** and **Demo** together.
3. Select exactly one primary discovery path; prepare local fixtures as a fallback.
4. Implement and test the P0 vertical slice before building moonshot interfaces.
5. Rehearse the real demo and record measured results and limitations.

**License and ownership:** Not yet selected. Decide before public release; this package contains draft planning material only.
