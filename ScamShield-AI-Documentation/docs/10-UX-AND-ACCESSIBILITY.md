# Experience, usability and accessibility specification

## 1. Experience objective

ScamShield is not only a cybercrime dashboard. It must let three audiences complete different safety-critical journeys: **investigators triage evidence**, **everyday users avoid dangerous links**, and **affected users obtain recovery guidance**. Do not overload the P0 dashboard with all P3 concepts.

Design target: A nontechnical person should understand a warning in under a few seconds without needing to know what DNS or TLS means. An analyst must still access raw provenance and limitations.

## 2. Navigation architecture

### Investigator app (P0)

- **Overview:** number of actually processed URLs, open investigations, pending human reviews, current provider status; clearly label fixture vs live.
- **Discover:** search query / Places search / manual URL input; query origin and time.
- **Investigations:** case list by severity, status, observed time, source.
- **Case detail:** URL provenance, inspection timeline, screenshots, observed redirects, risk reasons, limitations, analyst decision and PDF export.
- **Networks (P1/P3):** related cases with evidence on each edge.
- **Protection (P1):** approved rule versions, publishes/rollbacks, extension health and time.
- **Settings:** integrations/key status (masked), scan budgets, display language.

### Citizen-facing UI (P3)

- Scan / paste / share / camera QR.
- Risk details using plain terms and links to official verified alternatives.
- After-scam help (no shame or blame, clear urgent steps).
- Report suspicious link or screenshot with preview/redaction and consent.
- Trusted Circle invitation and visible permissions.

### Guardian extension (P1)

- Popup: protection on/off, last sync, manual scan, settings.
- Block/interstitial: what was blocked, reason, what is known/unknown, verified alternative when available, report a mistake.

## 3. Screen inventories and wireframes

### Overview (desktop)

```text
+----------------------------------------------------------------------+
| ScamShield AI     Overview  Discover  Cases  Protection    [EN] [AR]  |
+----------------------------------------------------------------------+
| Provider status: LIVE / PARTIAL / FIXTURE                              |
|                                                                     |
| [URLs inspected] [High-risk pending] [Confirmed cases] [Open alerts]  |
|                                                                     |
| Discovery activity    | Recent cases                                  |
| [Source + query list] | [Time] [URL] [Evidence] [Risk] [Status]       |
|                                                                     |
| [Search query] [Scan URL] [View case]                                |
+----------------------------------------------------------------------+
```

### Case detail (desktop)

```text
+----------------------------------------------------------------------+
| Case SC-204 | Needs review | Risk: HIGH (provisional, not proof)      |
+----------------------------------------------------------------------+
| Source: SERP query, locale, observed timestamp                         |
| URL: punycode and human-readable host                                  |
| [Captured screenshot]       [Evidence findings + citations]           |
| [Redirect timeline / host changes]                                     |
| Known limitations: provider failed? blocked resources?                |
| [Confirm] [Dismiss] [More evidence] [Export redacted PDF]            |
+----------------------------------------------------------------------+
```

### Browser protection (simple)

```text
+--------------------------------------------------------+
| Caution: this link matches an approved block rule.      |
| Why: confirmed impersonation case (reviewed [date]).   |
| You have not shared any passwords with ScamShield.      |
| [Go to verified official site] [Details] [Report error]|
+--------------------------------------------------------+
```

Do not use alarming animation for uncertain results; do not label an unconfirmed site "criminal".

## 4. Visual system

- **Color:** Red for confirmed danger, amber for review, neutral for unknown, green only for verified safe *destination identity*, never global safety guarantees.
- **Labels:** Every status needs text and icon; do not rely on color alone.
- **Typography:** Responsive text scale; avoid tiny 10px labels, long URLs need wrapping and copy controls.
- **Layout:** 8px rhythm, consistent card spacing, visible evidence hierarchy, sticky case actions only if mobile safe.
- **Charts:** Add textual summary, tooltip accessible by keyboard, visible source and time range. Do not invent numbers.
- **Microcopy:** "Suspicious signs detected" is better than "You are definitely being scammed." Distinguish "not tested" from "no threats found."

## 5. Languages and inclusive access

Prioritize **English and Arabic**, including full RTL layout, not just translated labels. Arabic/English mixed URLs and codes must maintain logical reading order. Hindi and Urdu can join the roadmap only after high-quality translation review.

Target WCAG 2.2 AA design practices; UAE Design System targets this level. Essential checks:

- Keyboard operation (Tab/Shift+Tab/Enter/Escape), visible focus, predictable order.
- Text alternatives for icons and screenshots; actionable labels (not "click here").
- Color contrast, non-color risk cues, large touch targets, no timeout that steals a case review.
- Screen reader announcements for scan status changes (ARIA live regions without flooding).
- Accessible modal behavior, form validation, logical headings and skip links.
- Reduced-motion option for graphs/alerts and no flashing danger animations.
- High zoom and mobile responsive layouts at 200% and narrow viewports.
- Error language that can be understood by nontechnical and elderly audiences.

Reference: https://designsystem.gov.ae/guidelines/accessibility

## 6. Advanced accessibility / wow candidates

### ScamShield AR (selected; P2/P3)

- Camera detects QR; display extracted destination **without opening**.
- Assess local policy + reputation; overlay a textual badge on a camera freeze-frame, not fake certainty.
- Offer verified official QR destination/website only from independent registry.
- Accessibility fallback: upload QR image or enter URL; AR must not be the only interaction.

### Credential Tripwire (selected; P2)

- Intervene at sensitive form submission on a previously flagged host.
- Copy: "This site may not belong to the organization it claims to represent. Check the official website."
- No logging of password or OTP values; make warning keyboard accessible.

### Reality Switch (selected; P2)

- Present suspicious vs verified destination; explain why the verified destination is trusted.
- User chooses to navigate; no silent automatic redirection for uncertain cases.

### Privacy Cloak (selected; P2/P3)

- Extract sensitive text / visually marked regions, preview proposed redactions and let user edit before submission.
- Redaction is irreversible in exported artifact (not just a visual blur layer); retain original only with explicit need/consent and strict access policy.

### X-Ray (undecided)

- User-initiated visible-screen analysis could use OS-specific screen capture, but requires explicit runtime permission, privacy controls and a native helper. Not part of P0.

### Chatbot and voice assistant (suggested, not selected)

- User raised them as possible interaction concepts, but did not approve them for the build. Keep as exploration, not default scope.

## 7. Usability test tasks

1. Submit controlled suspicious URL and find evidence without guidance.
2. Explain why a flagged site is *suspicious* using only the UI.
3. Dismiss legitimate control and verify no block rule is published.
4. Recover from disconnected API and understand what still works.
5. Navigate the case screen fully by keyboard.
6. Switch English/Arabic and check mixed URL display/RTL alignment.
7. Find "report error" on a blocking screen.

Record completion rate, mistaken clicks, time and participant comments. Do not claim a formal accessibility certification from a quick manual test.

## 8. Design anti-patterns

- Red everywhere; it teaches users to ignore warnings.
- Fake live stats or animation while no scan runs.
- Blocking simply because AI returns "high confidence" without independent checks.
- Mobile companion claiming to scan all apps from a webpage.
- Publishing a screenshot to external AI/urlscan without consent or PII redaction.
