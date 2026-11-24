# Demo pages

Three local pages for the live demo and the engine tests. **Serve them on a laptop only. Never put them online.** They copy a real government service and a real bank, and the hackathon rules and UAE law treat a public copy as a real scam page.

Every form is a dummy: it has no backend and sends nothing. Submitting shows a "this was a ScamShield demo page" message instead. Each page also says "ScamShield demo page" in its footer and in a `scamshield-demo` meta tag.

| Page | Pretends to be | Expected verdict | What the engine should catch |
| --- | --- | --- | --- |
| [fake-fine/](fake-fine/index.html) | TAMM traffic-fine payment | **FRAUD** | Brand `tamm` named on a non-official domain; theme `traffic_fines` ("90% discount", "black points", "vehicle impound", "last day to pay"); asks for card number, CVV, OTP and Emirates ID; countdown timer |
| [fake-bank/](fake-bank/index.html) | Emirates NBD login | **FRAUD** | Brand `emiratesnbd` on a non-official domain; theme `account_verification` ("account blocked", "verify your account", "update your details"); asks for password, OTP and card PIN; WhatsApp "help" number that is not the official helpline (600 54 0000) |
| [legit/](legit/index.html) | An independent motoring blog | **LEGIT** or **UNKNOWN**, never FRAUD | Mentions TAMM, RTA and "traffic fine" but only links to official domains; its only form is an email newsletter sign-up, with no password, card or OTP fields |

The legit page is the false-positive test: it uses the same keywords as the fake fine page, so if the engine flags it, keyword scoring is too strong.

## Serve them

```bash
python3 -m http.server 8080 --bind 127.0.0.1 --directory demo-pages
```

Then open `http://127.0.0.1:8080/fake-fine/`, `/fake-bank/` and `/legit/`.

To make the demo look real, give them lookalike names that only exist on the demo laptop. Add these lines to `/etc/hosts` and open `http://tamm-fines-pay.ae:8080/fake-fine/`:

```
127.0.0.1  tamm-fines-pay.ae
127.0.0.1  emiratesnbd-verify.com
127.0.0.1  gulfdriverguide.ae
```

## Scanning them with ScamShield

The SSRF guard (`backend/app/workers/safety.py`) refuses anything that resolves to a private address, including `127.0.0.1`. That stays on for real scans. For the demo, only the exact hostnames in `SCAMSHIELD_DEMO_HOSTS` may resolve locally (empty by default; WHOIS lookups are skipped for them, because the real domains belong to someone else). Put this in `.env` on the demo laptop:

```
SCAMSHIELD_DEMO_HOSTS=tamm-fines-pay.ae,emiratesnbd-verify.com,gulfdriverguide.ae
```

- **Docker:** `docker compose --profile demo up --build` also starts a `demo` service that serves this folder on `127.0.0.1:8080` and gives the worker the three names as network aliases. Add the hosts-file lines above so the laptop's browser opens the same URLs.
- **Without Docker:** serve the folder as shown above, add the hosts-file lines, and run the worker with the same `SCAMSHIELD_DEMO_HOSTS`.

Then scan `http://tamm-fines-pay.ae:8080/fake-fine/`, `http://emiratesnbd-verify.com:8080/fake-bank/` and `http://gulfdriverguide.ae:8080/legit/`. Measured on 24 Nov (engine v1 + combination rules): fake fine **FRAUD 100**, fake bank **FRAUD 100**, legit blog **LEGIT 27**. The legit page sits close to the SUSPICIOUS line (30) because the URL model dislikes the `:8080` port; scan exactly these URLs in the demo.
