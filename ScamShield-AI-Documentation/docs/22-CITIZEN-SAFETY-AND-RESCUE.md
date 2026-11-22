# Citizen safety, SafePay, ChatSense, Trusted Circle and Scam Rescue

**Phase:** Mostly P3 roadmap, except a basic public scan view or redaction demo may be P2. The point is usable safety support, not turning citizens into investigators or collecting unnecessary data.

## 1. Scam Rescue - "I've already been scammed" (selected favorite)

The UI should start with **immediate containment**, not a lengthy chatbot conversation or account requirement.

| User situation | First recommended guidance (to verify locally) | What ScamShield must not promise |
|---|---|---|
| Clicked a link, entered nothing | Close page, don't download/install, check account activity if concerned | That clicking alone definitely caused compromise |
| Shared username/password | Change password through official site, revoke sessions, enable MFA, watch account | That password change alone guarantees safety |
| Shared OTP | Contact account provider immediately via verified channel, secure account | That the OTP can be retrieved or cancelled by ScamShield |
| Shared card details / sent money | Contact bank/payment provider promptly, ask about freeze/dispute and report through verified channels | Guaranteed chargeback or recovery |
| Installed suspicious app | Disconnect if needed, seek device security review through trusted services | Full phone malware removal from a website |
| Threatened/extorted | Preserve evidence carefully, avoid further payment/engagement, use official reporting help | That an informal report replaces urgent police assistance |

Use a verified official directory for Abu Dhabi/UAE reporting channels and payment providers; do not hardcode an unverified support number. In an emergency, urge contacting the relevant official emergency service directly, not the product chatbot.

## 2. SafePay - payment checkpoint (selected)

**Inputs:** voluntarily shared checkout URL, payment QR destination, merchant claim, displayed currency/amount or payment host. **Not:** bank app internals, user's card values, unrestricted SMS access.

**Checks:**

- Website organization identity versus independently verified domain.
- Whether checkout destination unexpectedly leaves the merchant's trusted domain/known processor relationship.
- Suspicious impersonation terms, very recent lookalike domain, repeated related cases.
- QR payment destination displayed before navigation.
- Whether claim and redirect contradict each other; evidence-linked explanation.

**Output:** `verified destination`, `suspicious evidence`, `insufficient evidence`, or `could not check`. Do not label payment safe simply because a familiar processor is used.

**Demo (P2 if capacity):** Controlled shop page linking to unexpected fixture checkout versus a legitimate control using a known processor fixture.

## 3. ChatSense - user-initiated conversation analysis (selected)

Supported inputs: pasted text, screenshot, voice-note transcription with consent. Detect pressure/urgency, identity impersonation, OTP requests, requests to move outside official channel and suspicious links.

Safety rules:

- No scraping WhatsApp or other apps' private messages. User explicitly selects/shares content.
- Offer preview and Privacy Cloak redaction before cloud analysis.
- Explain that social-engineering cues can occur in legitimate urgent messages too; avoid definitive labels.
- Retain minimal excerpts and allow deletion per policy.
- If audio is submitted, obtain specific consent and avoid storing raw voice by default.

Output example: "This message claims urgent action and requests a one-time code; those are common risk indicators. Verify with the organization through its independently found official channel."

## 4. Trusted Circle - opt-in trusted review (selected)

**Purpose:** Allow an elderly or otherwise concerned user to ask a chosen trusted person to review a suspicious link or request before acting.

- Explicit invitation and acceptance on both sides.
- Share **only** selected suspicious link, redacted screenshot and system's uncertain findings, not all browsing data.
- Default notification is "Review requested" rather than "A crime is happening."
- Viewer may suggest checking official channels; cannot remotely control or block the owner's phone.
- Revoke sharing with one action; role grants expire or are limited per incident.
- Avoid coercive monitoring; the owner can use the product without Trusted Circle.

## 5. SafeView - remote browser preview (selected)

**Purpose:** Preview a suspicious site from an isolated service, without opening the link directly on the user's device.

- Display server-generated screenshot, title, redirects and safety notes; do not embed the live untrusted page as an iframe in the citizen UI.
- Use same sandbox, egress and no-secret rules as investigation worker.
- Display capture time and `not a guarantee of safety` warning.
- Do not automatically play media, submit forms or trigger downloads.
- Make page content a static screenshot + text excerpt only.

## 6. Scan Anything and Privacy Cloak

- Let users submit QR image, screenshot, URL or selected shared text.
- Detect personal identifiers, email/phone and account-like numbers in a preview; user confirms/redacts.
- Redaction must alter exported image pixels or text values, not just cover elements visually.
- Provide manual erase tool when automatic detection misses a region.
- Show what will be sent to an external AI or evidence service, and request clear consent.

## 7. Community reporting

- Any citizen report opens a **candidate** case, not an immediate malicious verdict.
- Duplicate reporters should not artificially inflate risk scores or create a mob false accusation.
- Abuse protection: throttling, spam checks, reporter privacy and safe attachments.
- Reporter sees generic status (`received`, `under review`, `resolved`) but cannot access investigative identity or sensitive details.
- Reports sent to actual authorities only through officially supported channels, never a fabricated integration.

## 8. UX protections

- Plain-language summaries, high contrast, accessible buttons, bilingual EN/AR.
- Default no marketing/scare tactics, especially during Rescue flow.
- Provide verified alternatives in Reality Switch when available and explain provenance.
- Show `unknown` when an API/provider is offline; never use green "safe" from missing data.
- Do not assume every user has fast data, strong digital literacy or a credit card.

## 9. Delivery order after hackathon

1. Redacted citizen URL/QR share intake.
2. SafeView screenshot + simple explanation.
3. Scam Rescue guided decision tree and official directory.
4. SafePay checkout/QR checks.
5. ChatSense with local privacy checks.
6. Trusted Circle consent workflow.
7. Phone companion/AR and native platform experiences after platform review.

**Acceptance gate for all:** Does the feature reduce real risk, and can it be used without silently collecting sensitive information?
