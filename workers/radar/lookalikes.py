"""Radar 1: find registered domains that imitate UAE brands.

Generates typo, homoglyph and brand+bait-word variants of each brand name on the TLDs scammers use,
keeps the ones that exist in DNS, and queues them for scanning.

Usage: python -m workers.radar.lookalikes [--brand tamm] [--dry-run]
"""
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor

import dns.resolver
import dnstwist

from workers import brands, store
from workers.enrich import icann_domain

log = logging.getLogger("lookalikes")

TYPO_TLDS = ["com", "ae", "net", "org", "online", "site", "info", "co"]
COMBO_TLDS = ["com", "net", "online", "site", "xyz", "top", "info", "ae", "live", "icu", "vip", "shop"]
BAIT_WORDS = ["pay", "payment", "fine", "fines", "login", "secure", "verify", "update", "portal", "online",
              "service", "services", "uae", "ae", "gov", "refund", "renew", "track", "delivery", "rewards"]
# Unicode homoglyphs of a short brand name produce hundreds of unregistrable IDNs; ASCII lookalikes are enough.
SKIP_FUZZERS = {"*original", "homoglyph", "cyrillic", "bitsquatting", "tld-swap", "subdomain", "dictionary"}
ASCII_HOMOGLYPHS = {"m": ["rn"], "l": ["1", "i"], "i": ["1", "l"], "o": ["0"], "a": ["4"], "e": ["3"], "s": ["5"]}

# Typos of short names (tamm -> tmm, yamm) are mostly unrelated existing sites.
MIN_TYPO_LENGTH = 6

RESOLVER = dns.resolver.Resolver(configure=False)
RESOLVER.nameservers = ["1.1.1.1", "8.8.8.8"]
RESOLVER.lifetime = 4
THREADS = 64


def brand_labels(brand: dict) -> set[str]:
    return {d.split(".")[0] for d in brand["official_domains"]}


def typo_labels(label: str) -> set[str]:
    fuzzer = dnstwist.Fuzzer(f"{label}.com")
    fuzzer.generate()
    found = {d["domain"].rsplit(".", 1)[0] for d in fuzzer.domains if d["fuzzer"] not in SKIP_FUZZERS}
    for i, ch in enumerate(label):
        for glyph in ASCII_HOMOGLYPHS.get(ch, []):
            found.add(label[:i] + glyph + label[i + 1:])
    return {f for f in found if f and f != label and "." not in f and not f.startswith("xn--")}


def combo_labels(label: str) -> set[str]:
    out = set()
    for word in BAIT_WORDS:
        out |= {f"{label}-{word}", f"{word}-{label}", f"{label}{word}", f"{word}{label}"}
    return out


def generate(brand: dict) -> dict[str, str]:
    """Candidate domain -> how it was made."""
    official = set(brand["official_domains"])
    out: dict[str, str] = {}
    for label in brand_labels(brand):
        for typo in typo_labels(label) if len(label) >= MIN_TYPO_LENGTH else []:
            for tld in TYPO_TLDS:
                out[f"{typo}.{tld}"] = "typo"
        for combo in combo_labels(label):
            for tld in COMBO_TLDS:
                out[f"{combo}.{tld}"] = "combo"
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


def scan(brand_ids: list[str] | None = None) -> list[dict]:
    hits = []
    for brand in brands.load():
        if brand_ids and brand["id"] not in brand_ids:
            continue
        candidates = generate(brand)
        with ThreadPoolExecutor(THREADS) as pool:
            registered = [d for d, ok in zip(candidates, pool.map(exists, candidates)) if ok]
        log.info("%s: %d variants, %d registered", brand["id"], len(candidates), len(registered))
        hits += [{"domain": d, "brand": brand["id"], "how": candidates[d]} for d in sorted(registered)]
    return hits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", action="append", help="brand id; repeatable; default all")
    parser.add_argument("--dry-run", action="store_true", help="print hits without queueing")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    hits = scan(args.brand)
    if args.dry_run:
        for hit in hits:
            print(hit["brand"], hit["how"], hit["domain"])
        return
    conn = store.connect()
    new = sum(store.add_candidate(conn, f"http://{h['domain']}/", "lookalike", query=h["brand"],
                                  extra={"brand": h["brand"], "variant": h["how"]}) is not None for h in hits)
    print(f"{len(hits)} registered lookalikes, {new} new queued")


if __name__ == "__main__":
    main()
