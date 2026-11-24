"""Static lists the engine checks against."""

from functools import lru_cache

from ..config import MODELS_DIR

URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly", "cutt.ly",
    "rebrand.ly", "shorturl.at", "rb.gy", "t.ly", "tiny.cc", "s.id", "v.gd", "qrco.de",
    "lnkd.in", "bl.ink", "short.io", "shorturl.gg", "u.to", "clck.ru", "urlz.fr", "linktr.ee",
}

# Free platforms where anyone can host a page under the platform's domain.
# The platform's age, WHOIS and popularity say nothing about the page.
SHARED_PLATFORMS = {
    "vercel.app", "netlify.app", "github.io", "pages.dev", "workers.dev", "web.app",
    "firebaseapp.com", "herokuapp.com", "glitch.me", "repl.co", "replit.app", "replit.dev",
    "onrender.com", "fly.dev", "weebly.com", "wixsite.com", "godaddysites.com", "blogspot.com",
    "wordpress.com", "webflow.io", "framer.app", "framer.website", "carrd.co", "square.site",
    "000webhostapp.com", "ngrok.io", "ngrok-free.app", "trycloudflare.com", "r2.dev",
    "azurewebsites.net", "cloudfront.net", "appspot.com", "myqcloud.com", "notion.site",
    "canva.site", "gitbook.io", "surge.sh", "on.fleek.co", "ipfs.io", "dweb.link",
    "jimdosite.com", "webnode.page", "mystrikingly.com", "my.canva.site", "glide.page",
    "typedream.app", "teachable.com", "sharepoint.com", "translate.goog",
    "webwave.dev", "cdpn.io", "codepen.io", "cloudwaysapps.com", "secureserver.net",
    "wixstudio.io", "tilda.ws", "site123.me", "yolasite.com", "ukit.me", "webs.com",
    "firebasestorage.googleapis.com", "backblazeb2.com", "pinata.cloud", "4everland.app",
    # free dynamic-DNS names
    "linkpc.net", "duckdns.org", "ddns.net", "no-ip.org", "hopto.org", "zapto.org",
    "sytes.net", "serveftp.com", "myftp.biz", "freemyip.com", "dynv6.net",
}

# Most-phished brands worldwide: token in the domain -> official registrable domains.
# A token found in a domain that is neither official nor a popular site is a lookalike.
GLOBAL_BRANDS: dict[str, tuple[str, ...]] = {
    "paypal": ("paypal.com", "paypal.me"),
    "microsoft": ("microsoft.com", "microsoftonline.com", "live.com", "office.com"),
    "office365": ("office.com", "microsoft.com"),
    "outlook": ("outlook.com", "live.com", "office.com"),
    "onedrive": ("live.com", "microsoft.com"),
    "apple": ("apple.com",),
    "appleid": ("apple.com",),
    "icloud": ("icloud.com", "apple.com"),
    "facebook": ("facebook.com", "fb.com"),
    "instagram": ("instagram.com",),
    "whatsapp": ("whatsapp.com", "whatsapp.net"),
    "netflix": ("netflix.com",),
    "amazon": ("amazon.com", "amazon.ae", "amazon.co.uk", "amazon.de", "amazon.sa"),
    "dhl": ("dhl.com", "dhl.de"),
    "fedex": ("fedex.com",),
    "usps": ("usps.com",),
    "wellsfargo": ("wellsfargo.com",),
    "citibank": ("citibank.com", "citi.com"),
    "hsbc": ("hsbc.com", "hsbc.ae", "hsbc.co.uk"),
    "binance": ("binance.com",),
    "coinbase": ("coinbase.com",),
    "metamask": ("metamask.io",),
    "trustwallet": ("trustwallet.com",),
    "gmail": ("google.com", "gmail.com"),
    "docusign": ("docusign.com", "docusign.net"),
    "dropbox": ("dropbox.com",),
    "linkedin": ("linkedin.com",),
    "adobe": ("adobe.com",),
    "roblox": ("roblox.com",),
    "steamcommunity": ("steamcommunity.com",),
    "telegram": ("telegram.org", "t.me"),
    "tiktok": ("tiktok.com",),
    "booking": ("booking.com",),
    "airbnb": ("airbnb.com", "airbnb.ae"),
    "ebay": ("ebay.com",),
    "bankofamerica": ("bankofamerica.com",),
    "americanexpress": ("americanexpress.com",),
    "blockchain": ("blockchain.com",),
}

# Hosts on big trusted domains that serve user-made content (forms, sites, files).
USER_CONTENT_HOSTS = {
    "sites.google.com", "docs.google.com", "drive.google.com", "forms.gle", "storage.googleapis.com",
    "forms.office.com", "onedrive.live.com", "1drv.ms", "dropbox.com", "www.dropbox.com",
    "dl.dropboxusercontent.com", "s3.amazonaws.com", "telegra.ph", "t.me", "wa.me",
    "linktr.ee", "bit.ly",
}

# UAE government hosting networks: a site there is run by a government entity. Verified on
# 24 Nov 2026: adpolice.gov.ae, adpolice.ae, tamm.abudhabi resolve into AS201678 (ADNET).
GOVERNMENT_ASNS = {201678}
GOVERNMENT_NETWORKS = ("abu dhabi digital authority",)

SUSPICIOUS_TLDS = {
    "top", "xyz", "shop", "cfd", "sbs", "icu", "click", "buzz", "rest", "cyou", "lol", "online",
    "site", "store", "vip", "live", "life", "monster", "quest", "bond", "zip", "mov", "work",
    "support", "help", "info", "cc", "tk", "ml", "ga", "cf", "gq", "pw", "best", "fun", "win",
}


@lru_cache(maxsize=1)
def top_domains() -> frozenset[str]:
    """Registrable domains of the most popular sites (Tranco), minus shared platforms."""
    path = MODELS_DIR / "top_domains.txt"
    if not path.exists():
        return frozenset()
    names = {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
    return frozenset(names - SHARED_PLATFORMS)


def platform_of(host: str, registrable: str) -> str | None:
    """The shared platform a host lives on, if any."""
    if registrable in SHARED_PLATFORMS:
        return registrable
    for platform in SHARED_PLATFORMS:
        if host.endswith("." + platform):
            return platform
    if host in USER_CONTENT_HOSTS:
        return host
    return None
