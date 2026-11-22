# Documentation index

This package is the **planning source of truth**, not a source-code release. All APIs, storage objects and schedules are **proposals until implemented and validated**. Feature names are product concepts, not assertions of patentable novelty.

## Recommended reading order

**Everyone:** [README](../README.md) -> [Overview](01-PROJECT-OVERVIEW.md) -> [PRD](02-PRD-REQUIREMENTS.md) -> [Phases](04-PHASES-AND-ROADMAP.md) -> [Demo](13-DEMO-AND-PITCH.md).

**Backend/AI:** [Architecture](../ARCHITECTURE.md) -> [Detection](06-DETECTION-ENGINE.md) -> [Data](07-DATA-MODEL.md) -> [API](08-API-CONTRACTS.md) -> [Security](11-SECURITY-AND-PRIVACY.md).

**Frontend/extension:** [UX](10-UX-AND-ACCESSIBILITY.md) -> [Guardian](09-GUARDIAN-EXTENSION.md) -> [Journeys](19-USER-JOURNEYS.md).

**Lead/DevOps:** [Team](14-TEAM-EXECUTION.md) -> [Stack](05-TECH-STACK.md) -> [Ops](15-DEPLOYMENT-AND-OPS.md) -> [Integration costs](16-INTEGRATIONS-AND-COSTS.md) -> [Risks](17-DECISIONS-AND-RISKS.md).

**Future/mobile and research:** [Mobile + AR](21-MOBILE-AND-AR-ROADMAP.md) -> [Citizen safety + Rescue](22-CITIZEN-SAFETY-AND-RESCUE.md) -> [Innovation experiments](23-INNOVATION-EXPERIMENTS.md).

## Definitions

- **Candidate:** A link discovered or submitted for analysis; not yet suspected/confirmed fraud.
- **Observation:** One timestamped result of inspecting a URL, possibly across visitor profiles.
- **Finding:** A specific evidence-supported signal, not a guilty verdict.
- **Risk score:** Decision-support estimate for prioritization; not a probability unless validated/calibrated.
- **Case:** An analyst-managed investigation grouping observations and findings.
- **Confirmed block indicator:** A URL/domain approved for protection after review and subject to expiry/revocation.
- **Fixture:** Controlled test site/record, explicitly distinct from a live Internet discovery.
- **P0/P1/P2/P3:** Foundation / competitive edge / moonshot / post-hackathon roadmap.

## Quality bar for this documentation

Update docs when the product contract changes. Keep sample outputs clearly labeled example. Record any real test run with date, input data, code version and method. Do not promise police deployment or claim formal forensic admissibility.
