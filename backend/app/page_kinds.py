"""What kind of page the fetcher found: real content, or a placeholder (parked, for sale, error...).

Used by the fetcher when it saves Evidence and by the engine, which re-reads the stored title,
text and final address so that evidence saved before a pattern was added benefits from it.
"""

import re
from urllib.parse import urlsplit

from .contracts import Evidence

# Placeholder pages say nothing about the owner; the engine and the network map must not read them as content.
# Order matters: a marketplace that blocks the crawler ("Access Denied" on forsale.godaddy.com) is a for-sale
# page, and a suspended hosting account is a dead site, not a blocked one.
PAGE_KINDS = [
    ("for_sale", re.compile(r"(domain|this name) (is |may be )?for sale|buy this domain|make an offer|"
                            r"available on godaddy|available for purchase|reserved for strategic use|forsale\.|/lander|"
                            r"atom\.com|dan\.com|sedo\.com|afternic|hugedomains|buydomains|namingsystem|brandbucket|"
                            r"unstoppabledomains\.com/d/", re.I)),
    # Expired or suspended by the registrar or the host: registrars suspend a domain until its owner
    # verifies the WHOIS contact ("ICANN Verification", "Contact Verification Suspension Page").
    ("expired", re.compile(r"domain (is|has) expired|renew (the|this|your) domain|expired domain|website expired|"
                           r"cgi-sys/suspendedpage|this account has been suspended|contact your hosting provider|"
                           r"icann verification|contact verification suspension|registrant (whois )?contact "
                           r"information verif|domain (has been )?suspended by", re.I)),
    ("blocked", re.compile(r"access denied|just a moment|attention required|checking your browser|request blocked|"
                           r"403 forbidden|captcha|restricted domain|not authorized|security verification|"
                           r"إجراء التحقق|لحظة…", re.I)),
    ("parked", re.compile(r"parked (domain|free)|domain parking|this domain (is|was|has been) (registered|parked|"
                          r"purchased)|domain (is now )?reserved|registered at .{0,40}(hostinger|namecheap|godaddy)|"
                          r"if this is your domain|déjà enregistré|secureserver\.net|related searches|"
                          r"interim welcome page|headlinelogic", re.I)),
    # Server and CDN error pages ("502: Bad gateway", Cloudflare's "521: Web server is down").
    ("error", re.compile(r"\b404\b|not found|error establishing|critical error|site not configured|"
                         r"cannot be displayed|chrome-error://|bad gateway|service (temporarily )?unavailable|"
                         r"gateway time-?out|internal server error|web server is down|connection timed out|"
                         r"origin is unreachable|dns resolution error|ssl handshake failed|a timeout occurred", re.I)),
    # Whole phrases only: "brand new" or "check back" alone also appear on shop pages ("brand new iPhone").
    ("coming_soon", re.compile(r"launching soon|coming soon|under construction|website is (being built|coming)|"
                               r"(site|website|page) is brand new|please check back|check back (soon|later)|"
                               r"still being worked on|welcome to wordpress\. this is your first post|"
                               r"website maintenance|under maintenance|maintenance mode|\byakında\b", re.I)),
    ("default_host_page", re.compile(r"welcome to nginx|apache2? .{0,20}default page|it works!|"
                                     r"index of /|default web site page", re.I)),
]
# Hosting control panels title their suspension page exactly this; a phishing lure says more
# ("ADCB - Account suspended").
SUSPENDED_TITLES = {"account suspended", "website suspended", "suspended"}


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def parking_redirect(start_url: str | None, final_url: str) -> bool:
    """Parked domains send visitors to an ad lander that carries the domain in its address
    (headlinelogic.com/?d=dewa.online&pcid=56): traffic for sale, not a site of its own."""
    start, final = _host(start_url or ""), _host(final_url)
    if not start or not final or start == final or final.endswith("." + start):
        return False
    try:
        query = urlsplit(final_url).query.lower()
    except ValueError:
        return False
    return start in query


def page_kind(final_url: str, title: str, text: str, form_count: int = 0, start_url: str | None = None) -> str:
    """'content' for a real page; otherwise the kind of placeholder (parked, for_sale, blocked, error...)."""
    if (title or "").strip().lower() in SUSPENDED_TITLES:
        return "expired"
    if parking_redirect(start_url, final_url):
        return "parked"
    sample = f"{final_url} {title} {text[:600]}"
    kind = next((kind for kind, pattern in PAGE_KINDS if pattern.search(sample)), "content")
    if kind == "content" and len(text.strip()) < 20 and not form_count:
        return "empty"
    return kind


# Fetch errors that mean no web site answers at that name at all (as opposed to a timeout or a
# certificate error, which scam kits cause on purpose to keep foreign scanners out).
OFFLINE_ERROR = re.compile(r"^offline:|cannot resolve|err_name_not_resolved|err_connection_refused|"
                           r"err_address_unreachable|resolves to a non-public address", re.I)


def effective_kind(evidence: Evidence, url: str) -> str | None:
    """The stored page kind, unless today's patterns recognise the stored page as a placeholder.
    Never turns a stored placeholder back into content, and never reads short text as 'empty'
    (the stored excerpt can be shorter than what the fetcher saw). 'offline' when no site answers."""
    kind = evidence.page_kind
    if evidence.fetch_error:
        return "offline" if OFFLINE_ERROR.search(evidence.fetch_error) else kind
    if kind not in (None, "content", "blocked"):
        return kind
    again = page_kind(
        evidence.final_url or url, evidence.title or "", evidence.text_excerpt or "", len(evidence.forms), url
    )
    return again if again not in ("content", "empty") else kind
