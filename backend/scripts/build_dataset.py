"""Build the labelled URL datasets for training and evaluating the engine.

Run from backend/:  python -m scripts.build_dataset [--crawl-sites 1500]

Inputs (downloaded once into data/datasets/raw/, not committed):
  phishing: PhishTank verified-online, OpenPhish community feed,
            Phishing.Database ACTIVE list, PhiUSIIL (UCI, label 0)
  legit:    PhiUSIIL (label 1, homepages only), Tranco top-1M,
            plus deep pages crawled from Tranco sites and UAE official sites

Outputs in data/datasets/:
  train.csv  - url,label,source        (not committed, large)
  test.csv   - held-out by registrable domain, never seen in training
  test_uae_legit.csv - UAE official pages, legit control (test only)

Labels: 1 = fraud, 0 = legit.
"""

import argparse
import asyncio
import csv
import hashlib
import random
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import urljoin

import httpx

from app.config import REPO_DIR
from app.urls import hostname, registrable_domain

DATA = REPO_DIR / "data" / "datasets"
RAW = DATA / "raw"

SOURCES = {
    "openphish.txt": "https://openphish.com/feed.txt",
    "phishtank.csv": "http://data.phishtank.com/data/online-valid.csv",
    "phishing_db_active.txt": "https://raw.githubusercontent.com/mitchellkrogza/Phishing.Database/master/phishing-links-ACTIVE.txt",
    "phiusiil.zip": "https://archive.ics.uci.edu/static/public/967/phiusiil+phishing+url+dataset.zip",
    "tranco.zip": "https://tranco-list.eu/top-1m.csv.zip",
}

# Official UAE sites: legit control for the test set only (never trained on).
UAE_OFFICIAL = [
    "tamm.abudhabi", "uaepass.ae", "rta.ae", "emiratesnbd.com", "adcb.com", "bankfab.com",
    "dib.ae", "mashreq.com", "adib.ae", "rakbank.ae", "adpolice.gov.ae", "dubaipolice.gov.ae",
    "icp.gov.ae", "moi.gov.ae", "u.ae", "dewa.gov.ae", "etisalat.ae", "du.ae",
    "emiratespost.ae", "aramex.com", "salik.ae", "mohre.gov.ae", "abudhabi.ae",
]

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)
HREF = re.compile(r"""href\s*=\s*["']([^"'#\s]+)""", re.I)
SKIP_EXT = re.compile(r"\.(png|jpe?g|gif|svg|webp|ico|css|js|woff2?|ttf|pdf|zip|mp4|mp3)(\?|$)", re.I)

TEST_SHARE = 5  # 1 in 5 registrable domains goes to the test set
TRAIN_CAP_PER_CLASS = 60000
TEST_CAP_PER_CLASS = 3000


def download() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=300, headers={"User-Agent": UA}) as client:
        for name, url in SOURCES.items():
            path = RAW / name
            if path.exists() and path.stat().st_size > 0:
                continue
            print(f"downloading {name} ...")
            path.write_bytes(client.get(url).raise_for_status().content)


def is_test_domain(domain: str) -> bool:
    return int(hashlib.sha1(domain.encode()).hexdigest(), 16) % TEST_SHARE == 0


def clean(url: str) -> str | None:
    url = url.strip().strip('"')
    if not url or len(url) > 2000 or " " in url:
        return None
    if "://" not in url:
        url = "http://" + url
    if not url.lower().startswith(("http://", "https://")) or not hostname(url):
        return None
    return url


def read_lines(name: str) -> list[str]:
    return [
        line.strip()
        for line in (RAW / name).read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def load_phishing(rng: random.Random) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    with (RAW / "phishtank.csv").open(encoding="utf-8", errors="ignore") as f:
        rows += [(r["url"], "phishtank") for r in csv.DictReader(f)]
    rows += [(u, "openphish") for u in read_lines("openphish.txt")]
    db = read_lines("phishing_db_active.txt")
    rows += [(u, "phishing_db") for u in rng.sample(db, min(60000, len(db)))]
    for url, label in _phiusiil():
        if label == "0":
            rows.append((url, "phiusiil"))
    return rows


def _phiusiil():
    with zipfile.ZipFile(RAW / "phiusiil.zip") as z:
        name = next(n for n in z.namelist() if n.endswith(".csv"))
        with z.open(name) as f:
            text = (line.decode("utf-8-sig", errors="ignore") for line in f)
            for row in csv.DictReader(text):
                yield row["URL"], row["label"]


def tranco(limit: int) -> list[str]:
    with zipfile.ZipFile(RAW / "tranco.zip") as z, z.open("top-1m.csv") as f:
        out = []
        for line in f:
            out.append(line.decode().strip().split(",", 1)[1])
            if len(out) >= limit:
                break
    return out


async def _crawl_site(client: httpx.AsyncClient, domain: str, per_site: int) -> list[str]:
    try:
        res = await client.get(f"https://{domain}/")
    except (httpx.HTTPError, ValueError):
        return []
    if res.status_code >= 400 or "html" not in res.headers.get("content-type", ""):
        return []
    base = str(res.url)
    site = registrable_domain(hostname(base))
    links = {base}
    for href in HREF.findall(res.text[:400_000]):
        url = urljoin(base, href)
        if not url.startswith(("http://", "https://")) or SKIP_EXT.search(url):
            continue
        if registrable_domain(hostname(url)) == site and len(url) < 400:
            links.add(url.split("#")[0])
    links = sorted(links)
    random.Random(domain).shuffle(links)
    return links[:per_site]


async def crawl(domains: list[str], per_site: int) -> dict[str, list[str]]:
    limits = httpx.Limits(max_connections=60)
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=8, headers={"User-Agent": UA}, limits=limits, verify=False
    ) as client:
        sem = asyncio.Semaphore(60)

        async def one(d: str):
            async with sem:
                return d, await _crawl_site(client, d, per_site)

        results = {}
        for i, task in enumerate(asyncio.as_completed([one(d) for d in domains]), 1):
            d, links = await task
            if links:
                results[d] = links
            if i % 200 == 0:
                print(f"  crawled {i}/{len(domains)} sites, {sum(map(len, results.values()))} pages")
        return results


def write(path: Path, rows: list[tuple[str, int, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url", "label", "source"])
        w.writerows(rows)
    print(f"wrote {len(rows):>6} rows -> {path.relative_to(REPO_DIR)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crawl-sites", type=int, default=1500)
    parser.add_argument("--per-site", type=int, default=15)
    args = parser.parse_args()
    rng = random.Random(42)

    download()

    print("crawling legit deep pages ...")
    top = tranco(100_000)
    sites = top[:600] + rng.sample(top[600:], args.crawl_sites - 600)
    crawled = asyncio.run(crawl(sites + UAE_OFFICIAL, args.per_site))

    seen: set[str] = set()
    train: dict[int, list] = {0: [], 1: []}
    test: dict[int, list] = {0: [], 1: []}
    uae: list = []
    uae_domains = {registrable_domain(d) for d in UAE_OFFICIAL}

    def add(raw: str, label: int, source: str) -> None:
        url = clean(raw)
        if url is None or url in seen:
            return
        seen.add(url)
        domain = registrable_domain(hostname(url))
        if label == 0 and domain in uae_domains:
            uae.append((url, 0, "uae_official"))
        elif source == "openphish" or is_test_domain(domain):
            test[label].append((url, label, source))  # fresh feed always held out
        else:
            train[label].append((url, label, source))

    for d, links in crawled.items():
        for url in links:
            add(url, 0, "crawl_deep")
    for url, label in _phiusiil():
        if label == "1":
            add(url, 0, "phiusiil")
    for url, source in load_phishing(rng):
        add(url, 1, source)

    # Never let a test domain appear in training.
    test_domains = {registrable_domain(hostname(u)) for rows in test.values() for u, _, _ in rows}
    for label in (0, 1):
        train[label] = [r for r in train[label] if registrable_domain(hostname(r[0])) not in test_domains]

    def cap(rows: list, n: int) -> list:
        rows = rows[:]
        rng.shuffle(rows)
        # keep every crawled deep page and fresh feed entry, sample the rest
        keep = [r for r in rows if r[2] in ("crawl_deep", "openphish")]
        rest = [r for r in rows if r[2] not in ("crawl_deep", "openphish")]
        return keep + rest[: max(0, n - len(keep))]

    write(DATA / "train.csv", cap(train[0], TRAIN_CAP_PER_CLASS) + cap(train[1], TRAIN_CAP_PER_CLASS))
    write(DATA / "test.csv", cap(test[0], TEST_CAP_PER_CLASS) + cap(test[1], TEST_CAP_PER_CLASS))
    write(DATA / "test_uae_legit.csv", uae)
    return 0


if __name__ == "__main__":
    import warnings

    warnings.filterwarnings("ignore")
    sys.exit(main())
