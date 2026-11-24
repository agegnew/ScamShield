# ScamShield / CipherGuard brand kit

For Nati (UI) and the deck.

| | |
| --- | --- |
| Product | **ScamShield** (Arabic: **درع الاحتيال**) |
| Team | **CipherGuard** |
| Tagline | Check before you tap. / تحقّق قبل أن تضغط. |
| Style | Bright and friendly. Built for everyday residents, not only analysts |
| Logo (official) | [cipher-guard-logo.png](cipher-guard-logo.png): chrome shield with UAE flag, falcon, Grand Mosque skyline, padlock, laurel and the CIPHER GUARD wordmark (1254×1254, transparent) |
| Icon / small use | [cipher-guard-icon-256.png](cipher-guard-icon-256.png): the same emblem at 256px. Detail is lost below ~64px, so use it for title slides, splash and header, not as a 16px favicon |
| Superseded | [logo.svg](logo.svg), [icon.svg](icon.svg) (old SafeTap mark) and [options/](options/) drafts. Don't use them |

## Colours

Every text colour passes WCAG AA (4.5:1 or more) on its background.

| Token | Light (on #FAFAFF) | Dark (on #15121F) | Use |
| --- | --- | --- | --- |
| `bg` | `#FAFAFF` | `#15121F` | Page background |
| `primary` | `#6D28D9` | `#B79CFF` | Header, buttons, links |
| `accent` | `#F97316` | `#FB923C` | Shapes, badges, highlights. Not for text on light |
| `accent-text` | `#C2410C` | `#FB923C` | Orange text |
| `text` | `#1E1B2E` | `#F4F2FA` | Body text |
| `fraud` | `#C81E1E` | `#FF8080` | FRAUD verdict |
| `review` | `#B45309` | `#FBBF24` | SUSPICIOUS / needs review |
| `safe` | `#15803D` | `#4ADE80` | Verified official site only |
| `unknown` | `#57534E` | `#A8A29E` | Not enough evidence |

Verdict rules (from the UX doc):
- Always show an icon and a text label as well as the colour, e.g. ⛔ FRAUD, ⚠ REVIEW, ✓ OFFICIAL, ? UNKNOWN.
- Use green only to say "this is the official site". Never use it to mean "this is safe".

## Shape

- Rounded corners everywhere: 12–16px on cards, full pill shape on buttons and verdict chips.
- Big touch targets (44px or more), soft shadows, plenty of white space.

## Fonts

- English: **Nunito** (rounded and friendly)
- Arabic: **Tajawal**

Both are free on Google Fonts. For Arabic, use full RTL layout with the same sizes.

## Disclaimer

Don't use any police or government logo as our own. If the deck mentions a police pilot, word it as "proposed", not "endorsed".
