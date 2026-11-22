# Team plan, roles and collaboration

## 1. Team assumptions

Hackathon is 24 hours of implementation and requires a working MVP. Live organizer page requires **at least three registered team members**; initial circulating announcement mentioned teams of 3-5. Do not rely on a maximum without checking event rules. Assign by actual skills and availability, not names guessed by this document.

## 2. Recommended ownership (4-person example)

| Role | Owns | Deliverable and tests |
|---|---|---|
| A - Backend/AI lead | FastAPI, job orchestration, scoring, model output schema | Scan completes with real evidence and bounded errors |
| B - Discovery + security | SerpApi, Places, URL gate, Playwright sandbox | Candidate provenance, strict SSRF suite, screenshot artifacts |
| C - Frontend/UX | Next.js dashboard, case details, filters, PDFs | Operator can triage and export in one flow |
| D - Extension + integration / demo | WXT Guardian, rule feed, e2e tests, pitch/runbook | Confirmed case blocks in second browser; rollback works |

If **3 members**, combine A+B or C+D and reduce P1 scope. If **5 members**, add a dedicated QA/DevOps/privacy and demo owner; do not add new features solely to fill time.

## 3. Shared contracts to settle at kickoff

- `ScanCreate`, `ScanStatus`, `CaseDetail`, `Finding`, `Artifact`, `CaseDecision`, `RulesetResponse` from [API docs](08-API-CONTRACTS.md).
- `capture_mode` mandatory, always visibly distinguish `fixture` / `live`.
- Status enum and risk band consistent in frontend/backend/database.
- Auth roles and review transitions; approved rule publishing separate from AI score.
- Artifact path format and URL access control agreed.
- API errors use stable codes and `request_id`.

## 4. Git workflow

- Protected `main` as submission-ready branch (or very disciplined direct main if team is tiny).
- Feature branches: `feat/discovery`, `feat/analyzer`, `feat/dashboard`, `feat/guardian`.
- Small PRs, mandatory one reviewer when possible, CI smoke suite.
- Use commit format `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- Never check in `.env`, screenshots with secrets, private user reports, API response dumps with tokens.
- Tag pre-demo release `hackathon-mvp-v1` and record commit in evaluation sheet.

## 5. 24-hour team rhythm

- Kickoff: 15-minute architecture and contract lock.
- Every ~3 hours: 10-minute demo of integrated state, blocker list and decision.
- Hour 5: first worker observation persisted.
- Hour 8: source discovery + analysis connected.
- Hour 11: case dashboard has real data.
- Hour 14: P0 freeze decision.
- Hour 19: P1 freeze.
- Hour 22: cold restart and rehearsal.
- Hour 23: final packaging and submission check.

Avoid meetings longer than the engineering work they protect.

## 6. Task board (starter backlog)

| Task ID | Task | Dependency | Priority | Acceptance |
|---|---|---|---|---|
| API-01 | Health/auth/session | - | P0 | Backend starts and auth gates cases |
| API-02 | URL admission + SSRF gate | API-01 | P0 | Forbidden addresses rejected |
| DB-01 | Initial migrations | API-01 | P0 | Clean startup and downgrade documented |
| JOB-01 | Queue + job statuses | DB-01 | P0 | Queued -> complete/failed path |
| BR-01 | Browser sandbox + screenshots | API-02, JOB-01 | P0 | Fixture screenshot + redirect stored |
| DISC-01 | SerpApi Search adapter | API-01 | P0 | One source query creates candidates |
| DISC-02 | Places adapter | API-01 | Optional P0/P1 | One place website link with lawful storage |
| AI-01 | Rule/LLM findings | BR-01 | P0 | Evidence-backed findings JSON |
| CASE-01 | Case list/detail/review | DB-01, AI-01 | P0 | Analyst can review with reason |
| PDF-01 | Evidence PDF | CASE-01 | P0 | Same case ID and timestamps in file |
| WEB-01 | Dashboard shell & states | API-01 | P0 | Actual data and degraded banner |
| SEC-01 | SSRF + authz test suite | API-02 | P0 | All cases pass |
| EXT-01 | Rule feed + WXT extension | CASE-01 | P1 | Confirm -> block -> rollback |
| AGENT-01 | TrustChain steps | BR-01 | P1 | Redirect timeline on controlled site |
| GRAPH-01 | Scam DNA edge extraction | AI-01 | P1/P2 | Every graph edge cites evidence |
| DEMO-01 | Script and fallback | P0 | P0 | Cold-start run completes |

## 7. Team blockers and arbitration

- One person owns final architectural decisions; no unreviewed stack switches after hour 3.
- Provider-key problem after hour 5 -> use approved fixture fallback and don't let everyone wait.
- Broken live demo after hour 19 -> drop P1 first, then recover P0 reliability.
- Naming/design debate -> timebox 15 minutes; choose working placeholder.
- Security failure -> stop relevant feature; do not ship knowingly dangerous crawler.

## 8. Definition of integration-ready

An endpoint or UI is not "done" until another teammate can run it, its sample data is labeled, unit/integration smoke test passes, and relevant docs change is committed. **No hero-only developer laptop dependency.**

## 9. Handoff template

```text
Task:
Owner:
Branch / commit:
What works:
Endpoint(s) or path:
Environment variable(s):
How to reproduce:
Test(s):
Known limits:
Next owner/action:
```
