# Discovery, analysis, Maps and external integration guide

**Status:** Provider choices and billing requirements verified against public documentation on 22 Nov 2026; actual account plans, prices, credentials, scopes and quotas are **not** confirmed for this team. Recheck pricing and terms before enabling a provider. Do not publish API keys.

## 1. Integration decision matrix

| Provider | Purpose | Fields / API choice | Key restriction | Fallback |
|---|---|---|---|---|
| SerpApi Google Search | Discover suspicious search-result URLs | `engine=google`, `q`, `gl=ae`, `hl`, `location`, `organic_results[].link` | Provider credits/usage terms | Recorded source fixture |
| Google Places API (New) | Find business listings and linked websites | Place Search/Details with field mask including `id`, `displayName`, `websiteUri` | `websiteUri` Enterprise SKU; data use/caching rules | Controlled listing fixture |
| Google Maps JavaScript API | Visualize genuine location data in UI | JS map and markers | Billing and Maps attribution | No map UI; show cases table |
| Google Web Risk | Match unsafe URL list | Lookup/Update API | URL privacy, pricing, usage & redistribution restrictions | Local reviewed rule set |
| urlscan.io | Retrieve/page scan evidence | Scan API with explicit visibility; result references | `public` default, quota, PII risks | Isolated own Playwright worker |
| RDAP / DNS | Registration and name resolution | RDAP via standard bootstrap/registry; DNS A/AAAA | Rate limits; domain age unreliable as standalone indicator | Unknown metadata |
| Certificate Transparency | Newly observed certificate/domain signals | CT feeds/stream | No proof of registration/new scam | Later roadmap |
| AI model provider | Screenshot/text explanation | Vision-capable model with structured JSON output | Cost, latency, privacy, model availability | Deterministic engine |
| Chrome MV3 | User protection | DNR dynamic rules | Permissions, rules limits, async unknowns | Warning-only popup |

## 2. Google Search adapter

**Why:** Official challenge explicitly names search-engine results. SearchMind generates safe, permitted queries for high-risk user intents and obtains structured results via SerpApi.

Example query categories: `UAE traffic fine payment`, `Emirates ID update service`, `bank customer support`, `parcel delivery fee UAE`. Queries are **search intent hypotheses**, not evidence of fraud.

Potential request parameters:

```text
GET https://serpapi.com/search?engine=google&q=<encoded>&gl=ae&hl=en&location=Abu%20Dhabi%2C%20Abu%20Dhabi%2C%20United%20Arab%20Emirates
```

Send API key securely server-side (transport per SerpApi docs). Keep source/query/time/position and raw URL only as allowed; never treat sponsored/organic rank as a risk score. Use English and Arabic query families, controlled request budget and duplicate filtering.

**Do not use Google Custom Search JSON API as the default plan for a new customer:** Google documentation says it is **closed to new customers** and existing users are transitioning by 1 Jan 2027.

Sources: https://serpapi.com/search-api ; https://developers.google.com/custom-search/v1/overview

## 3. Google Places and Maps adapter

### Suggested path

1. Search for businesses in a chosen authorized category via Places Search (New), obtaining place IDs.
2. Use Place Details (New) with an explicit `X-Goog-FieldMask` requesting **only required fields**, potentially `id,displayName,websiteUri`.
3. Evaluate website URI and compare against independently maintained verified domain registry **without making unsubstantiated fraud accusations**.
4. Display provider attribution and fresh Place information within Google Maps policies.

**Key constraints:** `websiteUri` is Place Details **Enterprise** billing. Google Places terms restrict caching, prefetching, scraping, exporting and creating derived content from Maps data. **Place IDs** have a special retention allowance. Store only permitted data, request fresh content, obtain legal/provider review for any persistent threat-intelligence indexing based on Places data. If terms are incompatible with chosen product design, use another permitted source or controlled demo fixtures.

Sources: https://developers.google.com/maps/documentation/places/web-service/place-details ; https://developers.google.com/maps/documentation/places/web-service/policies

## 4. Web Risk and reputation checks

Google Web Risk checks against Google's unsafe URL lists. It provides **known unsafe list membership**, not a guarantee that a non-match is safe. The Lookup API sends the URL to Google; the Update API supports local hashed lookups but is more complex. Follow redistribution/usage conditions. Consider privacy when submitting user-supplied URLs with tokens.

Source: https://docs.cloud.google.com/web-risk/docs/overview

## 5. urlscan.io privacy

urlscan submission has `visibility=public|unlisted|private` with **public as default**. Public scan data may be visible to researchers and everyone. A copied private user URL could contain tokens or personal details. For the hackathon:

- Prefer **own isolated Playwright scan** for unknown/private URLs.
- If using urlscan, sanitize input, require explicit consent and choose appropriate visibility/plan.
- Never assume private visibility is enabled for the team's free account; check entitlements and quotas.
- Treat urlscan results as evidence that still requires interpretation.

Sources: https://docs.urlscan.io/pages/visibility ; https://docs.urlscan.io/apis/urlscan-openapi/scanning/submitscan

## 6. AI and token/cost budget

Model use is optional but can amplify investigator understanding. **Only send the smallest necessary content.** A conservative per-URL budget may include one resized screenshot plus 1-3 KB sanitized text and structured indicators. Use hard max tokens/call, timeout, 0-1 retry and caching on image/text hash.

Create an actual budget sheet before the event:

```text
Provider + plan:
Monthly/daily request quota:
Cost per query or unit:
Expected demo calls:
Fallback if quota hit:
Privacy/retention terms checked by:
Approval date:
```

Do **not** include invented prices. Billing/quotas are team-account-dependent and change over time.

## 7. Provider control pattern

Every integration should implement:

- Typed request/response and `source_provider` metadata.
- `enabled` flag and quota budget.
- Circuit breaker / timeout; retry with exponential backoff on temporary failure but no repeated abuse.
- Logging without tokens, original secret URL params or PII.
- `capture_mode=live|fixture` status returned to UI.
- Legal/ToS review checklist before production use.

## 8. Before-hackathon credential checklist

- [ ] SerpApi account and quota checked
- [ ] Places API enabled; billing and `websiteUri` SKU understood
- [ ] Google Maps data-use policy reviewed
- [ ] LLM account and request limits tested
- [ ] Web Risk or urlscan chosen with safe submission settings
- [ ] Rate limits and budget hard-coded/configured
- [ ] Safe offline fixtures available for every critical demo step
- [ ] Secrets only in env/secret manager, never in frontend or Git
