# Complete ScamShield feature catalog

**Purpose:** Preserve **all** ideas discussed, mark user selections accurately, separate hackathon deliverables from future ambitions, and prevent scope explosion. A feature being liked does **not** mean it is guaranteed to be built within 24 hours.

## Legend

- **Selected / interesting:** User expressed positive preference; design candidate.
- **Core / agreed vision:** Central to the agreed fraud-discovery architecture.
- **Suggested / undecided:** Discussed but not specifically selected.
- **Excluded:** User explicitly said not needed; leave out of implementation priorities.
- **P0:** Foundation; **P1:** Competition differentiator; **P2:** Moonshot if time permits; **P3:** Later roadmap.

## A. Discovery and early intelligence

| Feature | Summary | Proposed phase | Selection |
|---|---|---|---|
| SearchMind / Search Scam Hunter | Generate UAE-specific risk-intent searches, inspect search results for suspicious destinations | P0 limited; P3 expansion | Core |
| Google Maps / MapProof | Examine website links on business listings, compare claims with independently verified identities | P0 adapter if keys ready; P1 | Core |
| Manual URL checker | Accept pasted URL with job tracking and findings | P0 | Core |
| URL/domain intelligence | URL structure, DNS/RDAP, punycode, redirect, known threat feed matching | P0 | Core |
| Scam Embryo | Detect and prioritize new lookalike domains from CT observations | P2/P3 | Core idea |
| Scam Future Radar | Predictive *risk prioritization* of lookalike domains/infrastructure, not predicting crimes | P3 | Selected |
| Scam Time Machine | Compare timestamped page content/screenshot changes | P3 | Core idea |
| Scam Seismograph | Detect campaign spikes after establishing a baseline | P3 | Core idea |
| Scam Outbreak Intelligence | Combine searches, crowd reports, shared infrastructure and campaign signals | P3 | Selected |

## B. AI inspection and fraud investigation

| Feature | Summary | Proposed phase | Selection |
|---|---|---|---|
| Website content AI | Analyze suspicious claims, requested data, brand context, redirect/payout mismatch | P0 | Core |
| Visual impersonation AI | Compare suspicious screenshot against curated brand reference, show evidence | P0 limited | Core |
| Ghost Agent | Sandboxed browser agent reveals UI paths/redirect behavior without submitting real secrets | P1 | Selected |
| MirrorLens | Compare desktop/mobile/language/authorized region personas to reveal cloaking | P2 | Core idea |
| Victim Journey Simulator | Reconstruct permitted search-to-site-to-checkout journey and trust breakpoints | P1/P3 | Selected |
| TrustChain | Track link hops and explain where legitimate-looking context diverges | P1 | Core |
| Scam DNA / Fraud Farm Graph | Cluster sites via shared infrastructure, visuals, redirects, contacts or page fingerprints | P1 | Core |
| Scam Family Tree | Explain chronological relationships between suspicious campaigns | P3 | Core idea |
| AI Truth Tribunal | Compare site's claims against verified official domain registry, report contradictions | P2/P3 | Core idea |
| SafeView | Remote sandboxed screenshot/preview of suspicious URL rather than client-side visit | P2/P3 | Selected / interesting |
| Risk score / explainable verdict | Evidence-linked triage score; human confirmation remains separate | P0 | Core |

## C. Real-time protection and prevention

| Feature | Summary | Proposed phase | Selection |
|---|---|---|---|
| ScamShield Guardian | Browser extension warns and blocks reviewed malicious domains using Chrome MV3 | P1 | Favorite |
| ScamShield Immunity Network | Share approved/confirmed threat rules among opted-in extensions with expiry/rollback | P1 limited; P3 scale | Selected |
| Credential Tripwire | Warn **before submission** of sensitive fields on a flagged domain; never read values | P2 | Selected / very nice |
| Reality Switch | Offer curated verified official alternative, with user choice and explanation | P2 | Selected / nice |
| SafePay | Verify suspicious checkout/merchant/payment destination mismatch; no banking access | P2/P3 | Selected / interesting |
| Scam Vaccine | Derive proposed detection patterns from confirmed cases, test false positives before approval | P3 | Core idea |
| Safe QR destination check | Decode QR and inspect link before the browser navigates | P2 | Core / AR related |

## D. Citizen usability, accessibility and device experiences

| Feature | Summary | Proposed phase | Selection |
|---|---|---|---|
| ScamShield AR | Camera overlays QR destination safety / independently verified link when available | P2/P3 | Selected / very nice |
| Scan Anything | Submit links, screenshots, QR images, or shared content from SMS/WhatsApp | P2/P3 | Core idea |
| ChatSense | Voluntary shared text, screenshot, voice note analyzed for social engineering | P3 | Selected / interesting |
| Privacy Cloak | On-device/local redaction preview before evidence sharing | P2/P3 | Selected / good |
| Trusted Circle | Explicitly consented family/trusted contact review of risky requests | P3 | Selected / interesting |
| Phone Connect | Desktop/web paired with separately installed consent-based mobile companion | P3 | Favorite / expanded |
| Multilingual UX | Arabic and English/RTL first; Hindi and Urdu are optional extensions | P0 basic; P3 full | Core idea |
| Voice-first accessible mode | Accessibility concept with clear speech and larger text (not yet selected as feature) | P3 | Suggested |
| Chatbot | User-proposed conversational entry point; not yet approved/specified | P3 | Suggested / undecided |
| Voice assistant | User-proposed voice control; not yet approved/specified | P3 | Suggested / undecided |
| ScamShield X-Ray | Consent-based on-screen analysis of the currently visible screen | P3 | Undecided |
| Community intelligence | Citizen reports with deduplication, status tracking and analyst verification | P3 | Core idea |

## E. Rescue and investigation workflow

| Feature | Summary | Proposed phase | Selection |
|---|---|---|---|
| Scam Rescue | Guided after-scam triage: credentials, card/payment, device and official report guidance | P3; small static demo optional | Favorite |
| Investigator dashboard | Queue, timeline, evidence view, risk explanation, review actions and alerts | P0 | Core |
| Alerts | Case alerts with severity, deduplication, evidence, acknowledgement; avoid false urgency | P0 local | Core |
| PDF evidence package | Timestamps, sources, screenshots, technical indicators and limitations | P0 | Core |
| Case graph/map | Related URLs and source origin view; map plotted only for genuine geographic evidence | P1/P3 | Core |
| Human verification & appeals | Confirmation/dismissal with documented rationale and rule rollback | P0/P1 | Core |

## Excluded by user

| Feature | Reason / instruction |
|---|---|
| Notification Detox | User explicitly declined; do not re-propose as a priority |
| Pocket Shield | User explicitly said not needed; no offline Quick Settings work |

## Feature interaction example

1. SearchMind identifies a URL in a permitted SERP result.
2. Ghost Agent gathers technical and visual evidence in sandbox.
3. TrustChain traces redirects; Scam DNA links shared indicators.
4. Investigator approves a confirmed malicious test indicator.
5. Immunity Network updates Guardian; extension blocks next visit.
6. Reality Switch offers a curated legitimate destination.
7. Citizen affected earlier can access Scam Rescue guidance; Privacy Cloak can prepare safe evidence.

## Feature gate rubric

Score each candidate 1-5 on **challenge relevance**, **working demo impact**, **build time**, **external dependencies**, **security/legal risk**, and **testability**. Implement only features that improve the quality of the vertical slice, not feature count.

**Recommended emphasis:** A credible P0 + **Guardian confirmed block** or **Ghost Agent/TrustChain** + a tested legitimate control. Avoid building native phone pairing or camera AR before core discovery is reliable.
