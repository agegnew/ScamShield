"""URL features for the URL model. Used at training and at scoring time,
so this module must stay importable for the saved model to load."""

import math
import re
from collections import Counter
from urllib.parse import urlsplit

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

from .lists import SUSPICIOUS_TLDS, URL_SHORTENERS

SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://", re.I)
IP_HOST = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
BAIT_WORDS = (
    "login", "signin", "sign-in", "verify", "verification", "secure", "account", "update",
    "confirm", "password", "banking", "wallet", "invoice", "billing", "payment", "pay",
    "refund", "unlock", "suspend", "support", "service", "auth", "webscr", "recover",
)


def url_text(url: str) -> str:
    """What the character model reads: lower-case URL without scheme and 'www.'."""
    text = SCHEME.sub("", url.strip().lower())
    return text[4:] if text.startswith("www.") else text


def _entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    return -sum(c / len(text) * math.log2(c / len(text)) for c in counts.values())


def lexical(url: str) -> list[float]:
    try:
        parts = urlsplit(url if "://" in url else "http://" + url)
        host = (parts.hostname or "").lower()
    except ValueError:
        parts, host = urlsplit("http://invalid"), "invalid"
    path, query = parts.path or "", parts.query or ""
    labels = host.split(".")
    tld = labels[-1] if labels else ""
    text = url_text(url)
    digits = sum(ch.isdigit() for ch in text)
    specials = sum(not ch.isalnum() for ch in text)
    return [
        len(text),
        len(host),
        len(path),
        len(query),
        host.count("."),
        host.count("-"),
        sum(ch.isdigit() for ch in host),
        max(0, len(labels) - 2),
        float(bool(IP_HOST.match(host))),
        float("@" in text),
        float("xn--" in host),
        query.count("&") + (1 if query else 0),
        path.count("/"),
        digits / max(1, len(text)),
        specials / max(1, len(text)),
        _entropy(host),
        float(tld in SUSPICIOUS_TLDS),
        float(host in URL_SHORTENERS),
        float(bool(re.search(r"\.(php|html?|aspx?)$", path))),
        float("//" in path),
        sum(word in text for word in BAIT_WORDS),
        max((len(t) for t in re.split(r"[./\-_?=&]", text)), default=0),
        float(parts.port is not None if host != "invalid" else 0),
    ]


class UrlLexical(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return np.array([lexical(u) for u in X], dtype=float)
