"""Fingerprints that link scam sites run by the same people: favicon, page template, look, trackers, contacts.

favicon_mmh3 uses Shodan's formula, so analysts can pivot with `http.favicon.hash:<value>` on Shodan.
"""
import base64
import hashlib
import re
from io import BytesIO

import phonenumbers
from PIL import Image

DOM_SHAPE_JS = """
() => [...document.body ? document.body.querySelectorAll('*') : []].slice(0, 3000).map(el => el.tagName).join(' ')
"""
FAVICON_JS = """
() => { const l = document.querySelector('link[rel~="icon"], link[rel="shortcut icon"], link[rel="apple-touch-icon"]');
        return l ? l.href : new URL('/favicon.ico', location.href).href; }
"""

TRACKERS = {
    "google_analytics": re.compile(r"\b(G-[A-Z0-9]{6,12}|UA-\d{4,10}-\d{1,3})\b"),
    "google_tag_manager": re.compile(r"\bGTM-[A-Z0-9]{4,9}\b"),
    "facebook_pixel": re.compile(r"fbq\(\s*['\"]init['\"]\s*,\s*['\"](\d{10,20})['\"]"),
    "yandex_metrica": re.compile(r"ym\(\s*(\d{6,10})\s*,\s*['\"]init['\"]"),
}
WHATSAPP = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send/?\?phone=)\+?(\d{8,15})", re.I)
TELEGRAM = re.compile(r"(?:t\.me|telegram\.me)/([A-Za-z0-9_]{5,32})", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def murmur3_32(data: bytes, seed: int = 0) -> int:
    """Signed 32-bit MurmurHash3 (x86), the hash Shodan uses for favicons."""
    c1, c2, h = 0xCC9E2D51, 0x1B873593, seed
    rounded = len(data) & ~3
    for i in range(0, rounded, 4):
        k = int.from_bytes(data[i:i + 4], "little")
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
        h = ((h << 13) | (h >> 19)) & 0xFFFFFFFF
        h = (h * 5 + 0xE6546B64) & 0xFFFFFFFF
    k = 0
    tail = data[rounded:]
    for i, byte in enumerate(tail):
        k |= byte << (8 * i)
    if tail:
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
    h ^= len(data)
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h - (1 << 32) if h & 0x80000000 else h


def favicon_hashes(icon: bytes) -> dict:
    if not icon:
        return {"favicon_mmh3": None, "favicon_sha256": None}
    return {"favicon_mmh3": murmur3_32(base64.encodebytes(icon)),
            "favicon_sha256": hashlib.sha256(icon).hexdigest()}


def dom_hash(tag_sequence: str) -> str | None:
    """Same page template (tag structure, ignoring text) gives the same hash."""
    return hashlib.sha256(tag_sequence.encode()).hexdigest()[:16] if tag_sequence else None


def screenshot_dhash(png: bytes, size: int = 8) -> str | None:
    """64-bit difference hash of the top of the page: similar-looking pages differ in few bits (see hamming)."""
    if not png:
        return None
    image = Image.open(BytesIO(png)).convert("L")
    image = image.crop((0, 0, image.width, min(image.height, image.width * 2)))
    pixels = list(image.resize((size + 1, size), Image.Resampling.LANCZOS).getdata())
    bits = 0
    for row in range(size):
        for col in range(size):
            left, right = pixels[row * (size + 1) + col], pixels[row * (size + 1) + col + 1]
            bits = (bits << 1) | (left > right)
    return f"{bits:016x}"


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def tracking_ids(html: str) -> list[str]:
    return sorted({f"{name}:{m}" for name, rx in TRACKERS.items() for m in rx.findall(html)})


def contacts(text: str, html: str) -> dict:
    phones = {
        phonenumbers.format_number(m.number, phonenumbers.PhoneNumberFormat.E164)
        for m in phonenumbers.PhoneNumberMatcher(text, "AE") if phonenumbers.is_valid_number(m.number)
    }
    whatsapp = set()
    for digits in WHATSAPP.findall(html):
        try:
            number = phonenumbers.parse("+" + digits)
        except phonenumbers.NumberParseException:
            continue
        if phonenumbers.is_valid_number(number):
            whatsapp.add(phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164))
    return {
        "phones": sorted(phones),
        "whatsapp": sorted(whatsapp),
        "telegram": sorted({h.lower() for h in TELEGRAM.findall(html)}),
        "emails": sorted({e.lower().rstrip(".") for e in EMAIL.findall(text)})[:20],
    }
