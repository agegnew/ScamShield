"""Radar 1 (Simon): registered domains that imitate UAE brands.

Generates typo, homoglyph and brand+bait-word variants of each brand name on the TLDs scammers
use, and keeps the ones that exist in DNS.

Try it: python -m app.workers.radar.lookalikes tamm
"""

import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import dns.exception
import dns.resolver
import dnstwist

from ...brands import GENERIC_LABELS, load_registry
from ...contracts import Brand, Candidate, CandidateExtra, Source
from ..enrich import icann_domain
from .base import RadarSource

log = logging.getLogger("scamshield.radar.lookalikes")

TYPO_TLDS = ["com", "ae", "net", "org", "online", "site", "info", "co"]
COMBO_TLDS = ["com", "net", "online", "site", "xyz", "top", "info", "ae", "live", "icu", "vip", "shop"]
BAIT_WORDS = ["pay", "payment", "fine", "fines", "login", "secure", "verify", "update", "portal", "online",
              "service", "services", "uae", "ae", "gov", "refund", "renew", "track", "delivery", "rewards"]
# Unicode homoglyphs of a short brand name produce hundreds of unregistrable IDNs; ASCII lookalikes are enough.
SKIP_FUZZERS = {"*original", "homoglyph", "cyrillic", "bitsquatting", "tld-swap", "subdomain", "dictionary"}
ASCII_HOMOGLYPHS = {"m": ["rn"], "l": ["1", "i"], "i": ["1", "l"], "o": ["0"], "a": ["4"], "e": ["3"], "s": ["5"]}
# Typos of short names (tamm -> tmm, yamm) are mostly unrelated existing sites.
MIN_TYPO_LENGTH = 6
THREADS = 64

RESOLVER = dns.resolver.Resolver(configure=False)
RESOLVER.nameservers = ["1.1.1.1", "8.8.8.8"]
RESOLVER.lifetime = 4


def brand_labels(brand: Brand) -> set[str]:
    # Ordinary words (economy, added) and two-letter names (du) give thousands of unrelated domains.
    return {d.split(".")[0] for d in brand.official_domains} - GENERIC_LABELS


# How a lookalike was made, in the names the Radar page translates (docs/radar-ui.md).
# dnstwist "addition" appends a letter, which the page calls an extra letter like "insertion".
VARIANT_NAMES = {"addition": "insertion", "plural": "insertion"}


def typo_labels(label: str) -> dict[str, str]:
    """Misspelled label -> the trick used (omission, transposition, homoglyph, ...)."""
    fuzzer = dnstwist.Fuzzer(f"{label}.com")
    fuzzer.generate()
    found: dict[str, str] = {}
    for d in fuzzer.domains:
        if d["fuzzer"] not in SKIP_FUZZERS:
            found.setdefault(d["domain"].rsplit(".", 1)[0], VARIANT_NAMES.get(d["fuzzer"], d["fuzzer"]))
    for i, ch in enumerate(label):
        for glyph in ASCII_HOMOGLYPHS.get(ch, []):
            found.setdefault(label[:i] + glyph + label[i + 1:], "homoglyph")
    return {
        f: how for f, how in found.items() if f and f != label and "." not in f and not f.startswith("xn--")
    }


def combo_labels(label: str) -> set[str]:
    out = set()
    for word in BAIT_WORDS:
        out |= {f"{label}-{word}", f"{word}-{label}", f"{label}{word}", f"{word}{label}"}
    return out


def generate(brand: Brand) -> dict[str, str]:
    """Candidate domain -> how it was made: a dnstwist trick (omission, ...), "dictionary"
    (brand + bait word, e.g. tamm-pay) or "tld-swap" (tamm.com for tamm.abudhabi)."""
    official = set(brand.official_domains)
    out: dict[str, str] = {}
    for label in brand_labels(brand):
        typos = typo_labels(label) if len(label) >= MIN_TYPO_LENGTH else {}
        for typo, how in typos.items():
            for tld in TYPO_TLDS:
                out[f"{typo}.{tld}"] = how
        for combo in combo_labels(label):
            for tld in COMBO_TLDS:
                out[f"{combo}.{tld}"] = "dictionary"
        for tld in TYPO_TLDS:
            out.setdefault(f"{label}.{tld}", "tld-swap")
    return {d: how for d, how in out.items() if d not in official and icann_domain(d) == d}


def exists(domain: str) -> bool:
    """A registered domain has NS records; NXDOMAIN means nobody owns it."""
    try:
        RESOLVER.resolve(domain, "NS")
        return True
    except dns.resolver.NXDOMAIN:
        return False
    except dns.resolver.NoAnswer:
        return True
    except dns.exception.DNSException:
        return False


class Lookalikes(RadarSource):
    name = "lookalikes"
    source = Source.LOOKALIKE
    interval_minutes = 6 * 60

    def discover(self, brands: list[Brand]) -> list[Candidate]:
        now = datetime.now(timezone.utc)
        found: list[Candidate] = []
        planned = [(brand, generate(brand)) for brand in brands]
        total, checked = sum(len(c) for _, c in planned), 0
        self.report(0, total)
        for brand, candidates in planned:
            with ThreadPoolExecutor(THREADS) as pool:
                registered = [d for d, ok in zip(candidates, pool.map(exists, candidates)) if ok]
            checked += len(candidates)
            self.report(checked, total)
            log.info("%s: %d variants, %d registered", brand.id, len(candidates), len(registered))
            found += [
                Candidate(
                    url=f"http://{domain}/",
                    source=Source.LOOKALIKE,
                    query=brand.id,
                    discovered_at=now,
                    extra=CandidateExtra(brand=brand.id, details={"variant": candidates[domain]}),
                )
                for domain in sorted(registered)
            ]
        return found


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    chosen = [b for b in load_registry().brands if not sys.argv[1:] or b.id in sys.argv[1:]]
    for c in Lookalikes().discover(chosen):
        print(c.extra.brand, c.extra.details["variant"], c.url)
