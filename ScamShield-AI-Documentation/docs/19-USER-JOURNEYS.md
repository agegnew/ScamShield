# User journeys and end-to-end experience flows

## 1. Journey A: investigator discovers suspicious search result (P0)

**Persona:** Fraud analyst. **Trigger:** Worries about fake service websites appearing in Search.

1. Analyst opens Discover and enters a permitted query, region `AE`, locale `en` or `ar`.
2. UI records provider/mode/observed time, lists search candidates without calling them malicious.
3. Analyst starts scan on one candidate; request passes URL policy and enters queue.
4. Dashboard shows queued/running/completed/partial/failed, with request and job ID.
5. Isolated browser obtains screenshot and redirect evidence; deterministic analysis and optional AI produce findings.
6. Analyst opens case, reads risk + limitations, verifies screenshot and official domain comparison.
7. Analyst confirms/dismisses with a reason; status and audit are persisted.
8. Analyst exports evidence report with source, time, artifact hashes and caveats.

**Acceptance:** Case retrievable after reload; data source not lost; a failed scan remains unknown; source is labeled fixture/live.

**Failure route:** SerpApi unavailable -> UI says discovery unavailable; offers manual scan and controlled fixture with `SIMULATED` banner.

## 2. Journey B: suspicious Maps listing website (P0/P1)

**Persona:** Analyst investigating links surfaced in a business listing.

1. Search Places via an approved query; retrieve Place ID.
2. Fetch current necessary fields using field mask, including `websiteUri` when billing permits.
3. Scan linked website through normal URL gate; verify identity against independently verified organization domains.
4. Capture suspected mismatch with evidence; do not accuse the business or attribute intentional change without proof.
5. Show provider attribution according to Google policies; don't store unrestricted Maps content.
6. Analyst records decision, preserves independently captured evidence where legally permitted.

**Acceptance:** No hidden assumption of a free Google Places `websiteUri` field or unrestricted caching. On unavailable billing, fixture labeled and no fake live places.

## 3. Journey C: Guardian protects a known bad link (P1)

**Persona:** Chrome browser user.

1. User opts into Guardian and its stated permissions.
2. Extension downloads approved, versioned ruleset and installs DNR rules.
3. User attempts navigation to team-controlled known malicious demo domain.
4. Browser blocks pre-network using installed DNR rule; user sees explanatory page/popup and case reference.
5. Optional Reality Switch points to curated verified destination.
6. User can report a suspected false positive; analyst reviews and can revoke the rule.

**Acceptance:** Benign control still loads; no credential values captured; disabling/revoking rule restores browsing.

**Failure route:** New unknown URL with no installed rule may load before asynchronous analysis; UI must **not** claim it was already blocked.

## 4. Journey D: Credential Tripwire (P2)

**Persona:** User about to submit sensitive information on suspicious page.

1. Extension has permission for a page/active tab.
2. Page contains password/OTP/payment-field types or a form submitting to unusual host.
3. On submit attempt, content script checks **known flag + field metadata only**, never contents.
4. Warning: "This page may not be operated by the organization it claims to represent. Check the verified site."
5. User can cancel, see details, or make a deliberate choice to continue where allowed by product policy.

**Acceptance:** No DOM access to typed secret values, no keylogging, no unrestricted page scraping.

## 5. Journey E: ScamShield AR (P2/P3)

**Persona:** Citizen sees a QR code on a parking sign or poster.

1. App opens camera with explicit permission; user points at QR.
2. QR decoder extracts destination and displays raw host before navigation.
3. Engine checks locally available known indicators and may request server evaluation after consent.
4. Overlay shows one of: known dangerous, suspicious/unverified, no known flags, unable to check.
5. Independently verified official website is offered only when such an identity registry exists.
6. User can copy, share for review, or open with explicit choice.

**Acceptance:** No automatic navigation to decoded URL; offline/unknown state correctly described; camera is not recording persistently without consent.

## 6. Journey F: "I've already been scammed" (P3)

**Persona:** Victim already clicked, shared credentials or transferred funds.

1. Entry: prominent **Get help now** path, without asking for a full story first.
2. User selects incident type: clicked only; entered login/OTP; shared card information; transferred money; suspicious app installed.
3. UI offers ordered first actions: stop interaction, contact bank through independently verified channels, secure accounts, preserve evidence, report through official UAE/Abu Dhabi routes as applicable.
4. Privacy Cloak previews sensitive data redaction before sharing screenshots or logs.
5. User can export a personal incident summary; no promise of fund recovery.
6. Optional Trusted Circle shares only user-approved case summary to chosen person.

**Acceptance:** Does not instruct victim to message original scammer or share OTP; emergency steps precede lengthy data collection.

## 7. Journey G: ChatSense (P3)

1. User explicitly selects message text, screenshot or voice note.
2. Local/consented pipeline removes personal details when possible.
3. Model flags social-engineering patterns (urgency, fake authority, OTP demand, payment redirection) with quotes/regions.
4. Results explain uncertainty and practical verification steps.
5. No private-message scraping, no background microphone access.

## 8. Journey H: phone pairing (P3)

1. User installs **separate native companion** and signs in/approves pairing.
2. Desktop/web displays one-time pairing QR or code with short TTL.
3. Phone app scans QR, user accepts scoped permissions (e.g. QR scan, share-link intake, optional browser/network protection on supported OS).
4. Desktop displays consented device status and reported safety alerts, **not** arbitrary phone file contents.
5. User revokes pairing or any permission at any time; expiry and audit enforced.

See [Mobile companion architecture](21-MOBILE-AND-AR-ROADMAP.md).

## 9. Journey-to-feature traceability

| Journey | Main modules | Phase |
|---|---|---|
| A | SearchMind, Ghost Agent optional, risk, dashboard, report | P0 |
| B | MapProof, Places adapter, URL engine | P0/P1 |
| C | Guardian, Immunity Network, rule approval | P1 |
| D | Credential Tripwire, Reality Switch | P2 |
| E | ScamShield AR, SafePay QR check | P2/P3 |
| F | Scam Rescue, Privacy Cloak, Trusted Circle | P3 |
| G | ChatSense, Privacy Cloak | P3 |
| H | Phone Connect and scoped native companion | P3 |
