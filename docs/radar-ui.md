# Radar page v2: categories, run button, daily schedule

For Nati (UI). **The backend side is live on `main` (25 Nov).** Copy `docs/api/scamshield-api.d.ts` to `frontend/src/lib/api-types.d.ts`; real samples are in `docs/api/mock/radar_feed.json`, `radar_status.json`, `radar_run.json` and `radar_runs.json`.

**Goal:** an analyst opens the Radar page and sees at a glance what the radar found, grouped the way they think about it: *how* we found it (lookalike, certificate, new domain, search, Maps) and *who* it imitates (banks, police and fines, delivery, shopping offers, and so on). They can also start a radar run with one button and watch it work.

## 1. What changes in the data (backend)

- **More brands:** 23 → 53. More banks, emirate police and parking, delivery, airlines, and shops whose "offers" scammers copy (noon, Dubai Duty Free, Carrefour UAE, Lulu, Emirates, Etihad, ...). Amazon, DHL and FedEx were already covered as worldwide brands.
- **Every brand has a sector** (`category` in `/api/brands`). Two new values: `shopping` and `travel`.
- **Every radar find carries its category data**, so the page can filter without extra calls: `brand_category` and `source_details` on each item (section 4).
- **Radar runs** become visible: a daily automatic run, a manual "Run radar now" button, and live progress while a run is going.

## 2. The two ways to group a find

### Tabs: how we found it (`source`)

| Tab | `source` value(s) | Arabic | One-line explanation under the tab | Extra column |
| --- | --- | --- | --- | --- |
| All | (everything) | الكل | Every site the radar found | Source badge |
| Lookalike domains | `lookalike` | نطاقات مشابهة | Spelling tricks on official names that someone has registered | Trick used, e.g. "Extra word", "Letter swapped" |
| New certificates | `ct` | شهادات أمان جديدة | A new HTTPS certificate was issued for a name containing a brand | Issued (time) |
| New domains | `nrd` | نطاقات مسجلة حديثًا | Registered in the last days with a brand name in it | Registered on |
| Search & ads | `search`, `search_ad` | البحث والإعلانات | Google results and paid ads for what victims type | Query + position; "Ad" badge for `search_ad` |
| Maps | `maps` | الخرائط | Google Maps listings that use a brand name | Listing name + phone; red "Fake helpline" badge |

Each tab label shows its count, e.g. `Lookalike domains 312`. A tab with 0 stays visible but greyed.

**Lookalike trick labels** (`source_details.variant` → what to show):

| `variant` | English | Arabic |
| --- | --- | --- |
| `addition`, `dictionary` | Extra word | كلمة مضافة |
| `hyphenation` | Added hyphen | شرطة مضافة |
| `omission` | Letter missing | حرف ناقص |
| `insertion`, `repetition` | Extra letter | حرف زائد |
| `replacement`, `bitsquatting` | Letter changed | حرف مُبدّل |
| `transposition` | Letters swapped | أحرف مقلوبة |
| `vowel-swap` | Vowel changed | حرف علة مُبدّل |
| `homoglyph` | Look-alike letter | حرف شبيه |
| `tld-swap` | Different ending (.com → .ae) | امتداد مختلف |
| anything else (older finds say `typo`) | Similar name | اسم مشابه |

The backend sends `dictionary` for brand + bait word (tamm-pay), `tld-swap`, and the typo tricks `omission`, `insertion`, `repetition`, `replacement`, `transposition`, `vowel-swap`, `hyphenation`, `homoglyph`.

### Chips: who it imitates (`brand_category`)

| `brand_category` | English | Arabic |
| --- | --- | --- |
| `government` | Government services | الخدمات الحكومية |
| `police` | Police & fines | الشرطة والمخالفات |
| `transport` | Roads, tolls & parking | الطرق والرسوم والمواقف |
| `bank` | Banks & payments | البنوك والدفع |
| `delivery` | Delivery & post | التوصيل والبريد |
| `utility` | Electricity & water | الكهرباء والمياه |
| `telecom` | Telecom | الاتصالات |
| `shopping` (new) | Shopping & offers | التسوق والعروض |
| `travel` (new) | Airlines & travel | الطيران والسفر |
| `null` | No brand named | بدون علامة |

Show them as one row of chips with counts (from `counts_by_category`). Hide chips with 0.

## 3. The page

```
┌───────────────────────────────────────────────────────────────────────────┐
│ Radar                                                  [ Run radar now ▾ ] │
│ Last run today 03:00 · 312 new sites · next automatic run tomorrow 03:00   │
├───────────────────────────────────────────────────────────────────────────┤
│  RADAR SCOPE (only while a run is going, or after clicking the button)     │
│   ╭───────────╮   Lookalike domains   ██████████░░  41,200 / 56,958 names  │
│  │  · ⟋  •   │   New certificates    ████████████  done · 18 new          │
│  │ •  ⦿   ·  │   New domains         ████████████  done · 4 new           │
│  │   ·   •   │   Search & ads        skipped · needs SerpApi key           │
│   ╰───────────╯   Checking pages      ████░░░░░░░░  41 / 312               │
│                   Found so far: 312 · 9 fraud · 14 suspicious              │
├───────────────────────────────────────────────────────────────────────────┤
│ [All 312] [Lookalike domains 280] [New certificates 18] [New domains 4]    │
│ [Search & ads 6] [Maps 4]                                                  │
│ Spelling tricks on official names that someone has registered.            │
│                                                                           │
│ (Banks 120) (Police & fines 40) (Delivery 31) (Shopping & offers 22) ...   │
│ Verdict: [All] [Fraud] [Suspicious] [No warning signs]   Brand [▾]  [🔍  ] │
├───────────────────────────────────────────────────────────────────────────┤
│ Fraud 100   aramexdelivery.live   Aramex · Delivery   Extra word   2 min ›│
│ Suspicious  uaetamm.com           TAMM · Government   Extra word   5 min ›│
└───────────────────────────────────────────────────────────────────────────┘
```

### Run radar now (manual)

- Primary button at the top right. The arrow opens a small menu: **All sources** (default), then one entry per source. Sources that need a key show "(needs key)" and are disabled.
- Needs a signed-in analyst or admin. Signed out: show the button disabled with the tooltip "Sign in to run the radar".
- On click: `POST /api/radar/run`, then open the radar scope and poll `GET /api/radar/status` every 2 s until `status` is `done` or `failed`.
- If a run is already going (HTTP 409), just open the scope on that run.

### Daily automatic run

- Runs every day at 03:00 UAE time (`schedule` in the status). Nothing to click: just show "next automatic run tomorrow 03:00" in the status line.
- Runs started by the schedule show in the scope the same way, with "Automatic run" instead of "Started by analyst".

### Radar scope (the part that should look good in the demo)

- **Left:** a round radar screen. A sweep line rotates (about 4 s per turn, CSS `conic-gradient` + rotate is enough). Each new find appears as a blip at a random angle: grey while its page is being checked, then red (fraud), orange (suspicious) or green (no warning signs) when its verdict arrives.
- **Right:** one progress row per source, then "Checking pages x / y", then "Found so far: n · f fraud · s suspicious".
- **When the run ends:** the sweep stops and a summary line appears: "Run finished in 6 min: 312 new sites, 38 fraud, 64 suspicious", with a button **Show the fraud** that selects All + Fraud.
- New rows appear at the top of the table as they arrive (SWR refresh of the feed every 2 s while running, 8 s otherwise).
- **Accessibility:** the animation is `aria-hidden`. A polite live region announces "12 new sites found, 3 look like fraud" at most every 10 s. With `prefers-reduced-motion`, no rotation, only the bars.

### Filters

Tab, sector chip, verdict, brand and search box combine. Keep them in the URL like `/cases` does (`/?source=lookalike&category=bank&verdict=FRAUD`), so a filtered view can be shared or reloaded.

## 4. API (backend contract)

All new fields are additive; nothing existing changes.

### `GET /api/radar/feed`

New optional query params: `source` (`lookalike`, `ct`, `nrd`, `search`, `maps`; `search` also returns `search_ad`), `category`, `verdict` (`FRAUD`, `SUSPICIOUS`, `LEGIT`), `brand`, `q` (domain contains), `limit` (default 50, max 500).

```json
{
  "items": [
    {
      "id": "c-9f2a11b0",
      "url": "http://aramexdelivery.live/",
      "domain": "aramexdelivery.live",
      "source": "lookalike",
      "query": "aramex",
      "discovered_at": "2026-11-25T03:02:11Z",
      "verdict": "FRAUD",
      "score": 100,
      "brand_target": "aramex",
      "brand_category": "delivery",
      "status": "new",
      "source_details": { "variant": "addition" }
    }
  ],
  "counts_by_source": { "lookalike": 280, "ct": 18, "nrd": 4, "search": 5, "search_ad": 1, "maps": 4 },
  "counts_by_category": { "bank": 120, "police": 40, "delivery": 31, "shopping": 22, "none": 12 }
}
```

`counts_*` describe everything the radar found, ignoring the active filters, so the tab and chip numbers don't jump while filtering. A brand-less find is counted under `"none"`.

`source_details` by source (any field can be missing):

| `source` | Fields |
| --- | --- |
| `lookalike` | `variant` (see the trick table) |
| `ct` | `issuer`, `issued_at` |
| `nrd` | `registered_on` (date) |
| `search`, `search_ad` | `query`, `position`, `title`, `lang`, `replayed` (true = saved result, not live) |
| `maps` | `listing_name`, `phone`, `helpline_mismatch` (true = phone is not the official helpline), `rating`, `reviews`, `replayed` |

When `replayed` is true, show a small grey "saved result" tag on the row.

### `GET /api/radar/status`

Open like the other dashboard reads. Poll every 2 s while `running`, every 30 s otherwise.

```json
{
  "running": true,
  "run": {
    "id": "run-20261125-1412",
    "trigger": "manual",
    "started_by": "analyst",
    "status": "running",
    "started_at": "2026-11-25T14:12:03Z",
    "finished_at": null,
    "sources": [
      { "name": "lookalikes", "status": "running", "checked": 41200, "total": 56958, "new": 280 },
      { "name": "ct", "status": "done", "checked": 46, "total": 46, "new": 18 },
      { "name": "nrd", "status": "done", "checked": 1, "total": 1, "new": 4 },
      { "name": "search", "status": "skipped", "note": "needs_key" },
      { "name": "maps", "status": "skipped", "note": "needs_key" }
    ],
    "pages": { "checked": 41, "total": 312 },
    "verdicts": { "FRAUD": 9, "SUSPICIOUS": 14, "LEGIT": 18 },
    "error": null
  },
  "schedule": { "enabled": true, "time": "03:00", "timezone": "Asia/Dubai", "next_run_at": "2026-11-26T03:00:00+04:00" },
  "sources": [
    { "name": "lookalikes", "enabled": true, "needs_key": null, "last_run_at": "2026-11-25T03:00:00Z", "last_new": 12 },
    { "name": "search", "enabled": false, "needs_key": "SERPAPI_KEY", "last_run_at": null, "last_new": 0 }
  ]
}
```

- `run` is the current run while `running` is true, otherwise the last finished one (`null` if the radar never ran). `run.brands` is the brands it looked for (`null` = all).
- `searches_left` (top level) is the SerpApi searches left this month, `null` without a key. Show it small next to the Search & ads tab ("212 searches left this month").
- Search & Maps entries carry `note: "N live searches so far"` once done: the run's search budget is shared and capped (40 for a manual run).
- Source `status`: `waiting`, `running`, `done`, `skipped`, `failed`. `total` can be `null` when unknown (show an indeterminate bar).
- `verdicts` counts finds of this run that already have a verdict. The rest are still being checked.

### `POST /api/radar/run`

Needs a token (analyst or admin). Body is optional:

```json
{ "sources": ["lookalikes", "ct"], "brands": ["tamm", "emiratesnbd"] }
```

- Leave out `sources` for all enabled sources, and `brands` for all brands.
- `202` → `{ "run": { ...same shape as above... } }`
- `409` → `{ "detail": "radar_already_running", "run": { ... } }`
- `401` signed out, `400` unknown source or brand.

### `GET /api/radar/runs?limit=10`

The last runs, newest first, same `run` shape. Optional: a small "History" list under the scope.

## 5. Done when (simple checks)

1. The tabs show the six groups with counts, and each tab shows only its own finds with its extra column.
2. Sector chips filter the list; chips and tab counts don't change while filtering.
3. Tab + chip + verdict + brand + search combine, live in the URL, and survive a reload.
4. "Run radar now" is disabled when signed out and works when signed in; a second click during a run doesn't start another.
5. During a run, the scope shows a sweep, blips that change colour as verdicts arrive, and per-source bars that move. New rows appear at the top.
6. After the run, the summary line and "Show the fraud" work.
7. The status line shows the last run and the next automatic run.
8. Search & ads and Maps show "needs SerpApi key" when there is no key, and "saved result" tags on replayed rows.
9. Everything works in Arabic (RTL, labels from the tables above), by keyboard, and with reduced motion.

## 6. Order

1. **Now (Nati):** tabs, sector chips, filters and the scope animation, on the sample JSON above.
2. **Next (Agegnew):** more brands, `brand_category` and `source_details` in the feed, the run, status and runs endpoints, and the daily 03:00 schedule.
3. **Then:** swap the sample JSON for the real API and run one real radar run together for the demo video.
