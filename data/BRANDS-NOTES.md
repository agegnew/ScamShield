# brands.json v1 — notes

22 UAE brands. Fields follow the shared contract in the root README.

- `official_domains`: subdomains count as official (e.g. `smartservices.icp.gov.ae` is covered by `icp.gov.ae`).
- `helplines`: digits only, dialed from inside the UAE (e.g. `046019999`, not `+971 4 601 9999`). Normalize before comparing.
- `logo`: `null` until the files are in `data/logos/` (then set e.g. `"tamm.png"`, relative to `data/logos/`).

## Verification (24 Nov 2026)

Every helpline and domain was checked on the brand's own website or an official UAE government site.

| Brand | Helplines | Checked on |
| --- | --- | --- |
| TAMM | 800555 | tamm.abudhabi |
| UAE PASS | 600561111 | icp.gov.ae (UAE PASS page) |
| ICP | 600522222 | icp.gov.ae/en/contact-us |
| MOI | 8005000, 999 | moi.gov.ae/en/contactus.aspx |
| RTA | 8009090 | rta.ae contact page |
| Dubai Police | 901, 999 | dubaipolice.gov.ae contact page |
| Abu Dhabi Police | 8002626, 2828 (Aman SMS), 999 | adpolice.gov.ae/en/Aman |
| Salik | 80072545 | salik.ae / salik.rta.ae contact page |
| Emirates Post | 600599999 | emiratespost.ae/contact-us |
| Aramex | 600544000 | aramex.com UAE office finder |
| DEWA | 046019999, 991 | dewa.gov.ae contact page |
| e& | 101, 800101 | eand.ae / eand.com code of practice |
| du | 155, 800155 | du.ae contact page |
| Emirates NBD | 600540000 | emiratesnbd.com phone banking |
| ADCB | 600502030 | adcb.com/en/get-in-touch/call-us |
| FAB | 600525500 | bankfab.com contact and fraud pages |
| DIB | 046092222 | dib.ae phone banking |
| Mashreq | 044244444 | mashreq.com/en/uae/customer-care/contact-us |
| ADIB | 600543216 | adib.ae/en/pages/contact-us |
| RAKBANK | 042130000 | rakbank.ae contact pages |
| Darb | 800850 ⚠ | **Not yet confirmed on itc.gov.ae.** Guides disagree (800850 vs 800555, which is TAMM's). Open itc.gov.ae contact page and fix if different |
| Consumer Protection | 8001222 (Ministry of Economy), 600545555 (Dubai DET) | u.ae consumer protection page; moet.gov.ae; Dubai DET guides. Covers federal + Dubai; Abu Dhabi complaints go through TAMM |

Domains added after checking: `salik.rta.ae` (Salik), `eand.ae` (e&). Darb uses the ITC domains `itc.gov.ae` (portal `darb.itc.gov.ae`) and `admobility.gov.ae`. Consumer Protection: `moet.gov.ae`, `economy.gov.ae` (old Ministry domain), `consumerrights.ae`, `dubaidet.gov.ae`.

## Other official numbers (not added in v1)

These are real, but for other customer groups. Add them if the helpline check flags them by mistake:
- ADCB: Excellency 600502004, Privilege 600508008, Islamic 600562626
- ADIB: business 600543220, priority 800200, fraud hotline 026100116
- e&: business 8009111
- du: business 188 / 800188, home 043905555
- Mashreq: NEO BIZ 044244550
- FAB: housing loan 600560137
- MOI: child protection 116111

## Still to do

- [ ] Logo files in `data/logos/`
- [x] EN/AR scam keywords: in `data/scam_themes.json` v1
- [ ] Confirm the Darb helpline on itc.gov.ae
