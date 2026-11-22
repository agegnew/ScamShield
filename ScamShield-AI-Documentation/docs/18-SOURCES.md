# Source registry and research links

**Last checked:** 22 November 2026. Links and terms can change. This registry lists publicly published material used to ground design constraints; it does **not** verify any actual team's API credentials, budgets or implementation claims.

## Organizer and rules

1. **ScamShield AI official Podium+ page:** https://podium.aevsoft.cc/HackathonMngtWebApp/event.php?e=ad-police-x-42ad-hackathon&lang=en  
   Challenge wording, current dates, team formation requirements and mandatory working MVP. The live page lists registration closing **Sun Nov 22 2026, 23:59**; submission **Wed Nov 25 2026, 08:00**; a working MVP is required.

## Browser/extension engineering

2. **WXT official documentation:** https://wxt.dev/  
   Cross-browser extension development, MV3, React/TypeScript development workflow.
3. **Chrome declarativeNetRequest API:** https://developer.chrome.com/docs/extensions/reference/api/declarativeNetRequest  
   Pre-request known-rule blocking, rule ordering, dynamic/static/session limits.
4. **Chrome extension service worker lifecycle:** https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle  
   Event-driven service workers, termination and persistent storage requirements.
5. **Chrome extension permission model:** https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions  
   Permission warnings, optional host grants, least privilege.

## Discovery and maps

6. **SerpApi Google Search API:** https://serpapi.com/search-api  
   Google `engine=google`, query, geographic/locale parameters, organic result fields.
7. **SerpApi Google Maps engine:** https://serpapi.com/maps-local-results  
   Third-party optional route; evaluate terms/pricing independently.
8. **Google Places API (New) - Place Details:** https://developers.google.com/maps/documentation/places/web-service/place-details  
   Field masks, Place IDs, `websiteUri` and its billing SKU.
9. **Google Maps Places policies and attributions:** https://developers.google.com/maps/documentation/places/web-service/policies  
   Caching, scraping, storage, export and attribution restrictions; Place ID storage exception.
10. **Google Custom Search JSON API:** https://developers.google.com/custom-search/v1/overview  
    Documentation states service **closed to new customers**, transition by 1 Jan 2027 for existing customers.

## Threat intelligence and browser inspection

11. **Google Cloud Web Risk overview:** https://docs.cloud.google.com/web-risk/docs/overview  
    Known-unsafe URL lookups and limits on accuracy, URL privacy, data redistribution.
12. **urlscan.io scan visibility:** https://docs.urlscan.io/pages/visibility  
    Public, unlisted and private exposure; understand before sending user links.
13. **urlscan.io Scan API:** https://docs.urlscan.io/apis/urlscan-openapi/scanning/submitscan  
    Scan API schema, visibility default `public`, API-key requirements.
14. **Playwright BrowserContext isolation:** https://playwright.dev/docs/browser-contexts  
    Isolated browser storage/session contexts; separate from hard OS/network sandboxing.

## Safety and accessibility

15. **OWASP SSRF Prevention Cheat Sheet:** https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html  
    DNS rebinding and destination-IP enforcement guidance.
16. **UAE Design System accessibility guidance:** https://designsystem.gov.ae/guidelines/accessibility  
    WCAG 2.2 AA design guidance; national public-service minimum discussed there.
17. **W3C WCAG 2.2:** https://www.w3.org/TR/WCAG22/  
    Normative Web Content Accessibility Guidelines.

## Recommended further research (not yet incorporated into MVP assumptions)

- ICANN/RDAP registry documentation for domain registration metadata, limits and data interpretation.
- Certificate Transparency transparency.dev and CT log policies.
- OWASP ASVS for application authentication and auditability.
- Applicable UAE data protection and cybercrime law guidance from official UAE authorities before production deployment.
- Independent phishing corpus with source rights and known labels to evaluate false positives without accessing active adversarial content.

## Evidence standards

If a claim is used in the pitch, record whether it is: **official rule**, **provider capability**, **research observation**, **internal test result**, **design hypothesis**, or **future intention**. Do not turn a provider's marketing claim into measured performance of ScamShield.
