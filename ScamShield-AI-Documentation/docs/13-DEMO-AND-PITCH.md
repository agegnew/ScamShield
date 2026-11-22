# Demo, pitch and judging plan

**North star:** Demonstrate a working early-warning and protection workflow, not feature count. The official rules require a developed product or working MVP.

## 1. The hero story (roughly 60-90 seconds)

1. **Problem (10s):** "Someone searching for a routine UAE service can encounter a convincing impersonation site. A paste-URL checker sees it only after someone submits it."
2. **Discovery (15s):** Launch a known authorized Search/Places query; show where a candidate came from, its source and captured timestamp. If fixture mode, say so visibly.
3. **Investigation (20s):** Open the case, display screenshot + redirect path + identity mismatch. Explain that the score prioritizes review and is not a guilty verdict.
4. **Confirmation (10s):** Investigator confirms controlled malicious case with reason; the action is logged.
5. **Protection (15s):** In another Chrome profile, synced Guardian blocks the now-approved controlled domain. Revoke, and show rollback if time.
6. **Value (10s):** Evidence PDF and roadmap from detection to public safety.

**Alternative hero:** Ghost Agent/TrustChain showing an interactive yet controlled link journey, if extension isn't ready.

## 2. Full pitch outline (3-5 minutes, flexible)

- Slide 1: Problem with Search + Maps fraud and early identification.
- Slide 2: Why ordinary URL checkers alone are insufficient.
- Slide 3: System flow - Discover -> Investigate -> Connect -> Protect -> Rescue.
- Slide 4: Demo (mostly live, with clear mode indicator).
- Slide 5: Architecture/trust boundaries and why the system is safe to use.
- Slide 6: Actual measurements, benign control, limitations.
- Slide 7: How it could grow to Arabic/English citizens, AR QR, Rescue, Maps and phone companion.
- Slide 8: Specific next steps / impact without claiming police adoption.

## 3. Demo cases

| Case | What judges see | Critical condition |
|---|---|---|
| D1 - Discovery | Query results produce candidates | Source and mode clear |
| D2 - Risk evidence | screenshot, redirects, findings | Evidence actually captured |
| D3 - Legitimate control | Benign site gets low/unconfirmed risk, not blocked | No fake exceptions |
| D4 - Confirm and protect | Analyst approves, extension blocks controlled test site | DNR installed, measurable |
| D5 - Rollback | Approved block revoked and rule removed | Fail-safe false-positive recovery |
| D6 - Offline contingency | Local fixtures still run analysis | Clearly say fixture, not live scan |

## 4. 30-second technical defense

> "Our discovery adapters ingest links from Search and Places. A dedicated, restricted Playwright worker captures evidence, deterministic signals and vision analysis produce explainable risk, and analysts control confirmed rule publication. A Chrome MV3 extension blocks only approved known malicious indicators; unknown URLs may require asynchronous review. We maintain audit trails and safe rollback."

## 5. Likely judge questions and honest answers

**How are you different from Google Safe Browsing or urlscan?**

We do not claim to invent threat lists or screenshot scanning. Our differentiation is the integrated, UAE-relevant **discovery journey**, evidence-linked investigation and actionable protection loop. Existing threat services are inputs, not the whole product.

**How do you prevent false positives?**

Scoring creates a review queue. Blocking requires explicit reviewed confirmation; rule TTL and rollback are available. Show a benign control and real evaluation counts.

**Do you block a first-time unknown URL before it loads?**

Not universally. Browser-managed DNR blocks *already known approved rules* before requests. New unknown links need inspection and will be warned later or intercepted at supported checkpoints.

**Can you scan someone's phone from a webpage?**

No. Phone Connect is a proposed opt-in native companion, with OS permission limits and privacy safeguards.

**Do you have access to Abu Dhabi Police systems?**

No such integration is claimed. Reports are investigator-ready **prototypes**, not officially accepted legal evidence.

**Is this safe and legal to crawl?**

Only permitted sources and defensive passive inspection; controlled demo sites. Restrict egress, apply provider terms, avoid sensitive actions.

**Did you train your own phishing model?**

Only if actually done. Otherwise explain LLM + deterministic indicators and evaluated fixtures clearly.

## 6. Disaster-proof presentation plan

- Use two Chrome profiles with extension loaded and ruleset version visible.
- Keep pre-screened controlled test URLs; never rely on a live malicious site remaining online.
- Keep a 90-second screen recording of the **real built application** as a backup, labeled recording.
- Keep live API keys in server environment; provider quota/billing dashboard checked before demo.
- Show fixture mode banner when using sample results, never hide it.
- Pre-generate a PDF from the **same case ID** as demo if PDF export stalls, and say it is pre-generated.
- Test stage Wi-Fi, projector resolution, sound and screen scaling.
- Keep one teammate solely on operator/backup duty.

## 7. Judging positioning

These are recommended messages, not official judging categories:

- Challenge fit: early discovery across Search/Maps rather than just pasted links.
- Technical depth: safe browsing, evidence chain, transparent scoring, rule propagation.
- Usability: explainable results, human review, EN/AR direction, verified alternatives.
- Responsibility: false-positive control, privacy, no unverified public accusations.
- Expansion: AR QR, SafePay, Rescue and Phone Connect as credible future paths.

## 8. Final submission checklist

- [ ] Registered team satisfies official rules
- [ ] Working MVP live URL or reproducible setup included
- [ ] Short README and clear demo user path
- [ ] Video only if requested/allowed; avoid substituting it for MVP
- [ ] Architecture diagram and key differentiator clearly visible
- [ ] Known risks, provider conditions and evaluation disclosed
- [ ] Final Git commit tagged; no secrets in history
- [ ] Submission confirmed before Wed 25 Nov 08:00 UAE

## 9. Proposed pitch sentence

**ScamShield turns a suspicious search result into an evidence-backed investigation and a verified protection rule, before more people can follow the same dangerous journey.**
