# Project definition, vision, and overview

## Executive definition

**ScamShield AI** is a proposed early-warning and user-protection system for suspected online fraud. It begins at **discovery** (search-engine and Maps links), continues to **evidence-based inspection**, connects repeat patterns, and supports human review and user-facing protection.

It responds directly to the organizer's published challenge: detect fraudulent websites and links used in cybercrime and financial fraud across the open internet, including Search and Maps, with emphasis on **early identification**. The official problem statement does **not** require an AI chatbot, a mobile device scanner, browser extension, or police integration. These are our choices.

## Why current workflows can fail

- **Submission bottleneck:** A paste-URL checker only investigates a URL already brought to it.
- **Website camouflage:** Suspicious sites may present different content by device, locale, referrer, timing, or interaction.
- **Fragmented signals:** A case may appear isolated until domains, redirect destinations or common visual components are connected.
- **Opaque AI verdicts:** A numeric risk score without evidence is difficult to use in an investigation.
- **Last-mile gap:** Analysts may detect a harmful URL, but ordinary users can still visit it before a protection feed updates.
- **Victim journey gap:** People who already clicked, paid, or shared credentials need recovery guidance rather than only a warning.

## Primary users

| Persona | Job to be done | Top concern |
|---|---|---|
| Threat analyst / investigator | Discover, review, group and document suspected scams | Evidence quality, false positives, auditability |
| General web user | Be warned at the moment of risk | Minimal friction, understandable alternatives |
| Person seeking help after a scam | Understand immediate containment and safe reporting | Speed, privacy, no judgment |
| Trusted family reviewer | Help a relative evaluate a suspicious request, with consent | Privacy boundaries, easy explanation |
| Hackathon judge | Verify it solves the stated challenge | Real working MVP and credible measurement |

## Product outcomes

**For investigators:** Lower time to triage, richer evidence per case, fewer duplicate cases and visible provenance.

**For users:** Clear warning and verified alternative for suspicious links; guidance after an incident; privacy-aware submission.

**For the hackathon:** A memorable demo that goes beyond static UI: discovery -> inspect -> explain -> review -> protect.

## Product modules

1. **Radar:** SearchMind, MapProof, monitored domains and feed adapters.
2. **Investigator:** Safe browser inspection, Ghost Agent, MirrorLens, TrustChain, AI analysis.
3. **Intelligence:** Scam DNA, Scam Family Tree, outbreak trend analysis and hypothesis generation.
4. **Guardian:** Browser extension, Credential Tripwire, Reality Switch, approved Immunity Network.
5. **Citizen:** Scan Anything, ChatSense, SafePay, ScamShield AR, SafeView and Privacy Cloak.
6. **Rescue:** Post-incident triage, reporting guidance, trusted support.

**Only the first working vertical slice and one differentiator are in the recommended 24-hour build scope.**

## Non-goals and anti-claims

- No surveillance of people, scraping of private messages, collecting OTPs/passwords or covert phone inspection.
- No automatic attribution of crimes to individuals. Shared infrastructure creates a hypothesis, not identity proof.
- No promise of preventing a financial transfer or having access to banking apps.
- No assertion of official endorsement, police deployment, real-world blocklist coverage, or detection accuracy without validated testing.
- No unconditional guarantee that unknown URLs can be stopped pre-request in Chrome.

## Branding

**Product name:** ScamShield (Arabic: درع الاحتيال). **Team name:** CipherGuard. The approved logo, icon, colour tokens, typography, tagline and usage notes are in the [brand kit](../../branding/BRANDING.md). Use the product name consistently in the UI and pitch; “ScamShield AI” may be used in descriptive copy where needed, but “ScamShield Digital Immune System” and “GhostHunter” are not alternate product names.

## Value proposition in one sentence

> Where a conventional checker analyzes the link you give it, ScamShield tries to find risky journeys earlier, shows why they are risky, and delivers validated protection without sacrificing user trust.

## Success criteria

- Working candidate discovery (Search or Places) + manual scan.
- Safe investigation pipeline processes controlled test sites without reaching forbidden internal addresses.
- At least one suspicious case with screenshots/redirect evidence and an explainable triage decision.
- At least one legitimate control that does **not** become a confirmed malicious block.
- Demonstrated case review/report export.
- Optional but strong: reviewed rule applied to a browser extension and observed block before navigation.

Details: [PRD](02-PRD-REQUIREMENTS.md), [evaluation](12-TESTING-AND-METRICS.md), [phases](04-PHASES-AND-ROADMAP.md).
