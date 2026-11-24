# Numbers for the deck

Final engine numbers (24 Nov 2026, evening). Copy them into the `[__]` placeholders. Source and method: the "Results" section of the [README](../../README.md).

## Accuracy slide

- **Held-out test set:** 11,134 URLs the model never saw (3,000 phishing, 8,134 legitimate incl. 230 UAE official pages).
- **Precision 94%** · **Recall 78%** · **False-positive rate 1.8%** · F1 0.85 (URL only, phishing feeds off = honest number).
- **0 of 230 UAE government and bank pages flagged.**
- With phishing-feed lookups on: recall **83%**, same false-positive rate.
- "FRAUD" alone is near-certain: **99.5% precision** (7 false alarms in 8,134 legitimate URLs).
- Speed: about **11,000 URLs in 25 seconds** from the URL alone; the full page check (screenshot, forms, WHOIS) takes a few seconds per site.

## Early detection slide

- One radar run checked **56,958** lookalike names of 23 UAE brands and found **978 registered** domains in **4.5 minutes**, with no human input.
- Of 239 opened with the full check: **38 FRAUD, 64 SUSPICIOUS, 137 LEGIT** (parked, for sale or unrelated businesses).
- It also found **`adpolice.ae`, Abu Dhabi Police's own alias**, and the engine knows it is official (same server as `adpolice.gov.ae`): no false alarm on the police's own site.

## Demo slide / live demo scores

| What | Score |
| --- | --- |
| Fake TAMM fine-payment demo page | **FRAUD 100** |
| Fake Emirates NBD login demo page | **FRAUD 100** |
| Motoring blog that only mentions TAMM/RTA (false-positive test) | **LEGIT 27** |
| `moi-portal.com`: real fake Ministry of Interior portal | **FRAUD 75** (domain and page both claim to be the MOI) |
| `tamm-service.site`: parked TAMM lookalike | **SUSPICIOUS 60** (watched, nothing to take down yet) |
| Phishing kits planted on hacked `.ae` business websites | **FRAUD** |
| `tamm.abudhabi`, `rta.ae`, `emiratesnbd.com`, `adpolice.gov.ae`, `adpolice.ae` | **LEGIT 0** |

## AI slide (25 Nov, night)

- Borderline pages get a second look from **Claude (Opus 5.5)**: it reads the phone screenshot and the page like an analyst and adds one reason in Arabic and English.
- First real run: it recognised `adamex.online` as a **Russian baby-stroller shop** (our rules said SUSPICIOUS 54 as an Aramex lookalike → now LEGIT 24) and `uaetamm.com` as a **real-estate agency called Tamm** (55 → 40), and said "unsure" on empty placeholder pages instead of guessing.
- Safety rails: it never clears a phishing-feed hit, cloaking or a copied official template; it costs a few cents per page and only runs on pages the rules can't decide.
- Coverage now: **53 UAE brands in 9 sectors** (banks, police and fines, parking, delivery, shopping offers, airlines, ...), radar runs daily at 03:00 or on a button.

## One-liners

- "Every verdict comes with its reasons in Arabic and English, and a one-click PDF evidence report for police."
- "Five radars look for new lookalike domains, new certificates, newly registered domains, search ads and Maps listings: nobody has to paste a link."
- Honest limitation: "Search and Maps discovery needs a paid search API key; the other three radars are free."
