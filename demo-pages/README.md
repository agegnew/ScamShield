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

## Note for Simon: the fetcher will block these pages

`safety.assert_public_url()` refuses anything that resolves to a private address, including `127.0.0.1`. That is correct for real scans. For the demo you need a small exception, for example:
- an env setting such as `DEMO_ALLOWED_HOSTS=tamm-fines-pay.ae,emiratesnbd-verify.com,gulfdriverguide.ae` that skips the check only for those exact hostnames, and is empty by default; or
- saving each page's Evidence once and loading it as demo data.

Don't switch the check off globally.
