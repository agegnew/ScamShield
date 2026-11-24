"""SerpApi helpers shared by the Search and Maps radars (Simon; search budget: Agegnew).

Every SerpApi answer is saved under data/cache/serp/. A query only costs a live search when
  - SERPAPI_KEY is set,
  - its saved answer is older than SCAMSHIELD_SERPAPI_FRESH_HOURS (a fresh one is reused for free), and
  - the current radar run's budget picked it (plan()).
Otherwise the saved answer is replayed and its results are marked replayed=true, so the UI can label them.

Fewer searches, same quality: the free plan has 250 searches a month, and one search per query
of every brand would spend more than that in a single run. So each run spends its budget on the
queries that find the most scams: what victims type ("pay traffic fine abu dhabi") first, then
brand queries by how often that sector is impersonated, never-searched and stalest answers
first. Ads arrive in the same answer at no extra cost, and every URL found still gets the full
page check, so the verdicts are as good as for any other source.
"""

import calendar
import hashlib
import json
import logging
import os
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date

import phonenumbers
import requests

from ...config import CACHE_DIR
from ...engine.lists import platform_of, top_domains
from ..enrich import icann_domain

log = logging.getLogger("scamshield.radar.serp")

SERPAPI_URL = "https://serpapi.com/search.json"
ACCOUNT_URL = "https://serpapi.com/account.json"  # free: does not count as a search
GOV_SUFFIXES = (".gov.ae", ".abudhabi", ".dubai")
# Results on these hosts are news, social or directories, not impersonation.
NEUTRAL_HOSTS = {"wikipedia.org", "youtube.com", "facebook.com", "instagram.com", "x.com", "twitter.com",
                 "linkedin.com", "tiktok.com", "gulfnews.com", "khaleejtimes.com", "thenationalnews.com",
                 "apps.apple.com", "play.google.com", "google.com", "reddit.com", "wam.ae", "u.ae"}

# Live searches one radar run may spend at most.
RUN_MAX = int(os.getenv("SCAMSHIELD_SERPAPI_RUN_MAX", "40"))
# The plan's monthly searches (free plan: 250), used when SerpApi's own count can't be read.
MONTHLY = int(os.getenv("SCAMSHIELD_SERPAPI_MONTHLY", "250"))
# Kept back from the daily runs for manual runs and the demo.
RESERVE = int(os.getenv("SCAMSHIELD_SERPAPI_RESERVE", "30"))
# A saved answer younger than this is reused instead of searching again.
FRESH_HOURS = float(os.getenv("SCAMSHIELD_SERPAPI_FRESH_HOURS", "20"))


def _cache_path(params: dict):
    key = json.dumps({k: v for k, v in sorted(params.items()) if k != "api_key"}, ensure_ascii=False)
    return CACHE_DIR / "serp" / f"{params['engine']}_{hashlib.sha256(key.encode()).hexdigest()[:16]}.json"


def _ledger_path():
    return CACHE_DIR / "serp" / "usage.json"


def _ledger() -> dict[str, int]:
    try:
        return json.loads(_ledger_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _ledger_add(n: int) -> None:
    month = date.today().strftime("%Y-%m")
    usage = _ledger()
    usage[month] = usage.get(month, 0) + n
    _ledger_path().parent.mkdir(parents=True, exist_ok=True)
    _ledger_path().write_text(json.dumps(usage), encoding="utf-8")


# ---- budget ----------------------------------------------------------------


@dataclass
class Budget:
    """Live searches one radar run may spend, and which queries plan() chose to spend them on."""

    total: int
    spent: int = 0
    allowed: set[str] | None = field(default=None)  # cache file names; None = any query

    @property
    def left(self) -> int:
        return max(0, self.total - self.spent)

    def may_spend(self, name: str) -> bool:
        return self.left > 0 and (self.allowed is None or name in self.allowed)

    def allow(self, names: set[str]) -> None:
        self.allowed = (self.allowed or set()) | names


_current: Budget | None = None


@contextmanager
def budget(total: int) -> Iterator[Budget]:
    """Use `total` live searches for the radar run inside this block."""
    global _current
    previous, _current = _current, Budget(total)
    try:
        yield _current
    finally:
        _current = previous


def current_budget() -> Budget:
    """The running radar run's budget; outside a run (CLI), one run's worth per process."""
    global _current
    if _current is None:
        _current = Budget(RUN_MAX)
    return _current


def searches_left() -> int:
    """Searches left this month: SerpApi's own count (free to ask), else our ledger."""
    key = os.environ.get("SERPAPI_KEY")
    if not key:
        return 0
    try:
        resp = requests.get(ACCOUNT_URL, params={"api_key": key}, timeout=15)
        if resp.ok:
            data = resp.json()
            left = data.get("total_searches_left", data.get("plan_searches_left"))
            if left is not None:
                return max(0, int(left))
    except (requests.RequestException, ValueError):
        pass
    return max(0, MONTHLY - _ledger().get(date.today().strftime("%Y-%m"), 0))


def run_budget(trigger: str, left: int | None = None, today: date | None = None) -> int:
    """Live searches for one run. A manual run may use up to RUN_MAX; the daily run spreads what
    is left this month (minus RESERVE) over the remaining days, so the month never runs dry."""
    left = searches_left() if left is None else left
    if left <= 0:
        return 0
    if trigger == "manual":
        return min(RUN_MAX, left)
    today = today or date.today()
    days_left = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    return max(0, min(RUN_MAX, (left - RESERVE) // days_left))


# ---- choosing queries -------------------------------------------------------


@dataclass(frozen=True)
class Query:
    params: dict = field(hash=False, compare=False)
    weight: float  # how much this query is worth: victim-intent 3, high-risk sector 2, ...
    label: str  # the search text, for logs

    @property
    def name(self) -> str:
        return _cache_path(self.params).name


def age_hours(params: dict) -> float | None:
    cache = _cache_path(params)
    if not cache.exists():
        return None
    return (time.time() - cache.stat().st_mtime) / 3600


def plan(queries: list[Query], allowance: int) -> list[Query]:
    """The queries that get a live search: never-searched ones first (most important first), then
    the stalest answers weighted by importance. Fresh answers are reused for free."""
    ranked = []
    for q in queries:
        age = age_hours(q.params)
        if age is None:
            ranked.append(((1, q.weight), q))
        elif age >= FRESH_HOURS:
            ranked.append(((0, age * q.weight), q))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [q for _, q in ranked[: max(0, allowance)]]


def plan_into_budget(queries: list[Query], share: float = 1.0) -> list[Query]:
    """Pick from `queries` with `share` of what's left in the run's budget, and allow them."""
    b = current_budget()
    chosen = plan(queries, int(b.left * share))
    b.allow({q.name for q in chosen})
    if chosen:
        log.info("live searches this run: %s", ", ".join(q.label for q in chosen))
    return chosen


# ---- calling SerpApi --------------------------------------------------------


def serpapi(params: dict) -> dict:
    cache = _cache_path(params)
    age = age_hours(params)
    key = os.environ.get("SERPAPI_KEY")
    b = current_budget()
    if key and (age is None or age >= FRESH_HOURS) and b.may_spend(cache.name):
        b.spent += 1
        _ledger_add(1)
        try:
            resp = requests.get(SERPAPI_URL, params={**params, "api_key": key}, timeout=60)
            if resp.status_code == 200:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(resp.text, encoding="utf-8")
                return resp.json()
            log.warning("SerpApi %s: HTTP %s", params.get("q"), resp.status_code)
        except requests.RequestException as exc:
            log.warning("SerpApi %s: %s", params.get("q"), type(exc).__name__)
    if cache.exists():
        return {**json.loads(cache.read_text(encoding="utf-8")), "_replayed": True}
    return {}


def e164(raw: str) -> str | None:
    digits = re.sub(r"[^\d+]", "", raw or "")
    if len(digits) <= 4:
        return digits or None
    try:
        number = phonenumbers.parse(raw, "AE")
    except phonenumbers.NumberParseException:
        return None
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def is_neutral(host: str) -> bool:
    """News, social, government and popular sites: a search hit there is not an impersonation.
    Shared platforms (wixsite, pages.dev, ...) are not in the popular list, so scams there still count."""
    registrable = icann_domain(host)
    if platform_of(host, registrable):  # sites.google.com, forms.gle, *.wixsite.com: anyone can publish there
        return False
    if any(host == h or host.endswith("." + h) for h in NEUTRAL_HOSTS) or host.endswith(GOV_SUFFIXES):
        return True
    return registrable in top_domains()
