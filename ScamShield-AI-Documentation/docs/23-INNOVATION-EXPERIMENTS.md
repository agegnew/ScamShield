# Research-grade innovations and differentiator experiments

**Status:** Ideas, not proven proprietary inventions. This document specifies how to *demonstrate* novelty in workflow and assess whether a feature adds meaningful fraud-detection value.

## 1. Core innovation hypothesis

An integrated system that **discovers candidate links from victim search intent**, inspects **what a victim actually sees**, finds **related scam infrastructure**, and pushes **human-approved protections** can be more actionable than a paste-a-URL risk score. Each claim must be backed by an implemented test and transparent comparison.

## 2. Experimental candidates

| Hypothesis ID | Feature | What to compare | Feasible controlled proof |
|---|---|---|---|
| EXP-01 | SearchMind | Manual URL queue vs query-driven discovery | Query adapter returns new candidate with provenance |
| EXP-02 | Ghost Agent | Static fetch vs bounded UI interaction | Controlled page reveals redirect after harmless navigation |
| EXP-03 | MirrorLens | Desktop-only vs desktop+mobile+Arabic profiles | Controlled site reveals different form; inspect false benign locale differences |
| EXP-04 | TrustChain | Final URL only vs full redirect path | Controlled payment journey shows trust breakpoint |
| EXP-05 | Scam DNA | Isolated cases vs relation-graph triage | 3 synthetic cases share hashed component; graph cites evidence |
| EXP-06 | Immunity Network | Analyst case alone vs reviewed rule propagation | Rule publish -> Chrome block -> rollback timed |
| EXP-07 | Scam Embryo | Content-only detector vs lookalike-domain watcher | CT fixture flags potential impersonation domain early; false positive tracked |
| EXP-08 | Scam Time Machine | Single page snapshot vs multiple time snapshots | Fixture changes content, timeline captures transition |
| EXP-09 | Scam Outbreak Intelligence | Alert list vs grouped campaign timeline | Controlled burst of related indicators yields one campaign with evidence |
| EXP-10 | AI Truth Tribunal | Free-form text label vs curated identity cross-check | Fixture false official claim contrasted with verified registry |
| EXP-11 | Scam Vaccine | Manual reviewed rule vs automatically suggested candidate rule | Suggest candidate, test benign set, human approve/reject |
| EXP-12 | AR / Reality Switch | Generic warning vs QR + verified alternative | Controlled QR displays destination and safe alternative |

## 3. Priority and sequencing

**Best 24-hour integrated innovation:** EXP-01 plus EXP-04 or EXP-06. Start from a real query and finish with evidence or blocking.

**Strong backup:** EXP-02 / EXP-03 controlled site comparison with precisely recorded screenshots.

**Post-event research:** EXP-07 to EXP-11 require historical datasets/longer monitoring and formal false-positive evaluation; they shouldn't become unsubstantiated "predicts scams before they exist" claims.

## 4. Experimental design standard

For each feature prepare:

```text
Experiment ID:
Hypothesis:
Baseline method:
Proposed method:
Dataset and rights:
Controlled or live mode:
What counts as TP/FP/TN/FN:
What result would falsify our hypothesis:
Expected failure modes:
Measured results (fill after run):
Screenshot / log / commit evidence:
```

Use **held-out examples** not just demo fixtures to claim generalized improvement. Repeat each experiment and record environment. Call a concept "novel integration" instead of "world-first" unless research substantiates that assertion.

## 5. Fraud-network relation caveats

- Same CDN IP: weak connection; many unrelated websites share hosting.
- Same tracking ID/form endpoint: stronger shared operational relationship, but still not necessarily same human owner.
- Similar screenshot: maybe common marketplace template or copied legitimate UI.
- Domain newly registered/CT-observed: raises priority, not a verdict.
- Search rank/advertisement placement: discovery context, not guilt.

Graph UI must show **why** two nodes connect, how the evidence was obtained, and a confidence category. Never represent unconfirmed graph edges as proven criminal organizations.

## 6. Demo adversarial controls

- Benign page with payment provider redirection, to reduce false accusations.
- Benign mobile/Arabic variation, to test MirrorLens specificity.
- Login form on real official domain, to prevent Credential Tripwire blanket blocking.
- Newly registered legitimate site, to test CT/domain age heuristic.
- Shared public CDN host between benign and suspicious site, to prevent naive clustering.
- Website with deliberately misleading "Ignore previous instructions" HTML, to test prompt injection resistance.

## 7. Recommended wow sequence

1. An investigator enters a search-intent query.
2. Candidate is discovered with source and date.
3. Passive browser evidence reveals redirect and screenshot identity mismatch.
4. Optional controlled MirrorLens profile exposes a hidden path.
5. A human analyst confirms the relevant controlled test case.
6. Guardian blocks it in a second browser, while a benign control stays open.
7. Evidence report includes the same case ID, screenshot hashes, timestamps and uncertainty.

This is an achievable **narrative**, not a guaranteed demo until implemented and tested.

## 8. Claim discipline

- "Proactive discovery" means a scheduled/intent-based discovery workflow exists; it does **not** mean identified before every first victim.
- "AI-driven" means specified model input/output is integrated and logged; it does **not** establish correctness.
- "Real-time protection" means pre-request blocking for **known approved rules**; not all unknown links.
- "Police-ready evidence" means structured triage report; not legal admissibility or official integration.
- "Predictive" means prioritization based on observable patterns; not ability to forecast future crimes as fact.
