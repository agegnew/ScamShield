# Test strategy, benchmark design and evaluation metrics

## 1. Testing policy

A polished demo does **not** prove general scam detection accuracy. The test plan separates **functional proof**, **security proof**, **real-world performance** and **presentation reliability**. Never invent numerical results or infer accuracy from one intentionally constructed example.

## 2. Dataset layers

| Layer | Content | Purpose | Must label |
|---|---|---|---|
| A: Controlled fixtures | Synthetic benign and suspicious pages on `.test`/local fixtures | Deterministic end-to-end behavior, CI | SIMULATED |
| B: Public benign control | Documented official/legitimate domains under ordinary permitted access | False-positive sanity check | LIVE CONTROL |
| C: Authorized known malicious | Carefully sourced historical URL/page snapshots or threat feed entries, no unauthorized interaction | External validity | DATASET / HISTORICAL |
| D: Search/Places candidates | Newly discovered live URLs with no known label | Discovery yield, triage workload | LIVE - UNVERIFIED |

Do not treat all search results as phishing. Do not reuse training labels to measure final test accuracy. Maintain a manifest with source, permissions, observed date, expected label and verification method.

## 3. Minimum fixture cases

1. **SAFE-01:** ordinary small business page with common payment-provider link: must not be automatically confirmed malicious.
2. **SAFE-02:** a legitimate recently created-looking domain: tests weak domain age heuristic.
3. **SUSP-01:** team-controlled government-service impersonation layout and suspicious alternate payment destination.
4. **SUSP-02:** bank-lookalike form with input types but fake credentials never entered.
5. **SUSP-03:** redirect chain from search-like landing to unrelated controlled checkout endpoint.
6. **MIRROR-01:** desktop displays harmless page, mobile receives suspicious controlled landing.
7. **MAP-01:** fixture business listing with unrelated websiteUri; label as synthetic.
8. **SEC-01:** URL redirects to localhost/internal; must be refused.
9. **SEC-02:** name resolves to forbidden IPv6/private address after initial check; must be refused.
10. **FAIL-01:** LLM unavailable; deterministic findings persist and AI marked unavailable.
11. **FAIL-02:** provider quota exhausted; clear degraded mode.
12. **EXT-01:** reviewed rule published then revoked; Chrome extension changes behavior accordingly.

Use reserved `.test` example hostnames and local test server. Never impersonate actual UAE government systems in a publicly accessible demo site.

## 4. Required automated test suites

### Unit tests

- URL parsing, normalization and de-duplication.
- Hostname IDN/punycode and lookalike matching with legitimate counterexamples.
- Score contribution, cap/correlation handling, null/unknown behavior.
- Case transition authorization and audit event creation.
- Rule expiry, versioning, revocation and feed validation.
- PII redaction and safe plain-text error responses.

### Integration tests

- API -> queue -> worker -> DB -> artifacts -> case retrieval.
- Search provider adapter with recorded responses; no live provider dependence in CI.
- Places adapter with recorded, terms-compliant subset of sample response (avoid redistributing restricted data).
- PDF generated with stable case fields and artifact references.
- SSE stream receives scan/case updates or polling fallback.

### Security tests

- All SSRF and redirect cases from [Security](11-SECURITY-AND-PRIVACY.md).
- Prompt injection sample within page body has no effect on rule approval.
- Public report endpoint cannot return unredacted evidence.
- Unauthorized user cannot confirm case or publish rules.
- Basic SAST/dependency check and no API secrets in web/extension bundle.

### E2E tests

- Reviewer opens discovered candidate, sees completed scan, verifies evidence, exports PDF.
- Reviewer dismisses benign case; extension doesn't block it.
- Reviewer approves controlled suspicious case; extension blocks; rollback restores.

## 5. Evaluation metrics (with definitions)

| Metric | Calculation / explanation | Avoid claiming |
|---|---|---|
| Precision | TP / (TP+FP) on independently labeled set | "99% accurate" from 5 handpicked pages |
| Recall | TP / (TP+FN) on independently labeled set | Coverage of unknown universe of scams |
| False positive rate | FP / (FP+TN) | Zero errors unless enough controls tested |
| Discovery yield | Analyst-verified suspicious candidates / total candidates reviewed | All found URLs malicious |
| Median scan latency | Median `completed_at-started_at` (with sample size) | Typical times from a single best-case run |
| P95 latency | 95th percentile measured over sample | Guaranteed worst-case time |
| Lead time | Detection timestamp minus independently established first report/label time | Detection "before first victim" without evidence |
| Evidence completeness | Cases with required artifact/metadata fields / cases attempted | Court-admissible evidence |
| Rule propagation delay | Publish timestamp to installed block, measured in actual browser | Instant network-wide protection |
| Analyst decision time | Time from case open to recorded decision | Real police workflow impact without users |

Store the dataset version, code commit, API mode and date in benchmark output. A metric can be `N/A` when there is insufficient data.

## 6. Example results sheet (fill after execution)

```text
RUN ID:
Date (UAE):
Git commit:
Dataset / fixture version:
Provider mode: LIVE | FIXTURE | MIXED
N benign labeled:
N suspicious labeled:
TP / FP / TN / FN:
Precision / Recall / FPR (if sample sufficient):
Median / P95 scan time:
Security failures:
Rule publish-to-block time:
Major limitations:
Reproduction command:
```

## 7. Stop-ship gates

- Any successful internal egress in SSRF suite -> **stop deployment**.
- Any leaked secret/OTP in logs or report -> **stop demonstration** until fixed.
- Any rule published from unreviewed AI output -> **disable extension sync**.
- Missing screenshots in one demo case -> use explicit metadata-only state or controlled fixture, never fabricate.
- Report uses fake current time or inconsistent IDs -> fix before submission.

## 8. Reproducibility checklist

- [ ] Fresh environment instructions tested by teammate
- [ ] Migrations and fixture seeding automated
- [ ] Tests can run without paid API keys
- [ ] Live access clearly labeled and optional
- [ ] Demo data rights recorded
- [ ] Results document created from actual run
- [ ] At least one benign control and one malicious fixture shown
- [ ] Extension rule rollback tested
- [ ] Smoke test after clean restart
