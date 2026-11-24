"""Police-ready evidence report for one case: an A4 PDF in English and Arabic.

Pure Python (fpdf2 + uharfbuzz for Arabic shaping and right-to-left order), so the API image
needs no browser or system libraries. Fonts (Noto Sans, Noto Sans Arabic, OFL) live in
app/assets/fonts. `build_report()` is the only entry point.
"""

from __future__ import annotations

import hashlib
import io
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont
from fpdf import FPDF
from fpdf.enums import MethodReturnValue, XPos, YPos
from PIL import Image

from .api_models import Case, RelatedDomain
from .brands import brand_by_id
from .config import ARTIFACTS_DIR, VERSION
from .contracts import Evidence
from .engine import domain_age_days
from .takedown import build_takedown

FONTS_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
LATIN = "NotoSans"
ARABIC = "NotoSansArabic"
_FONT_FILES = {
    (LATIN, ""): "NotoSans-Regular.ttf",
    (LATIN, "B"): "NotoSans-Bold.ttf",
    (ARABIC, ""): "NotoSansArabic-Regular.ttf",
    (ARABIC, "B"): "NotoSansArabic-Bold.ttf",
}
UAE = timezone(timedelta(hours=4))

# Layout (mm). A4 is 210 x 297.
MARGIN = 15
WIDTH = 210 - 2 * MARGIN
LABEL_W = 40  # English label (left) and Arabic label (right) columns of a key/value row
PAD = 1.5

NAVY = (15, 42, 68)
INK = (31, 41, 55)
MUTED = (107, 114, 128)
RULE = (209, 213, 219)
SHADE = (243, 244, 246)
WHITE = (255, 255, 255)

VERDICTS = {
    "FRAUD": ("FRAUD", "احتيال", (185, 28, 28)),
    "SUSPICIOUS": ("SUSPICIOUS", "مشبوه", (180, 83, 9)),
    "LEGIT": ("LEGIT", "سليم", (21, 128, 61)),
}
STATUSES = {
    "new": ("New, not reviewed", "جديدة، لم تُراجع"),
    "confirmed": ("Confirmed by an analyst", "أكّدها محلل"),
    "dismissed": ("Dismissed by an analyst", "استبعدها محلل"),
}
SOURCES = {
    "lookalike": "Look-alike domain check",
    "ct": "Certificate Transparency (new TLS certificate)",
    "nrd": "Newly registered domains list",
    "search": "Google search result",
    "search_ad": "Google paid ad",
    "maps": "Google Maps listing",
    "manual": "Submitted by an analyst",
    "citizen": "Reported by a citizen",
    "batch": "Batch file",
}
PROFILES = {
    "mobile_ae": "Phone browser in the UAE (Arabic/English, Asia/Dubai)",
    "desktop_us": "Desktop browser outside the UAE",
}
PAGE_KINDS = {
    "content": "Real page content",
    "parked": "Parked domain page (shown by the registrar or a parking service)",
    "for_sale": "Domain-for-sale page",
    "expired": "Expired domain page",
    "blocked": "Blocked page (host or security service)",
    "error": "Error page",
    "coming_soon": "'Coming soon' page",
    "default_host_page": "Default web-host page",
    "empty": "Empty page",
}
SENSITIVE = {
    "password": "password",
    "card": "card number",
    "otp": "one-time code (OTP)",
    "emirates_id": "Emirates ID",
    "phone": "phone number",
    "email": "email address",
}
DOWNLOADS = {
    "remote_access_link": "Link to a remote-access app",
    "remote_access_text": "Text asking to install a remote-access app",
    "app_download_link": "Link to download an app (APK)",
}
CLOAKING = {
    "desktop_blocked": "The foreign desktop visit was blocked or failed; the UAE phone visit loaded",
    "different_destination": "The foreign desktop visit ended on a different domain",
    "forms_hidden_from_desktop": "Sensitive form fields were shown only to the UAE phone visitor",
    "different_page": "The foreign desktop visitor saw a visibly different page",
}
NO_EVIDENCE = (
    "No page evidence collected / لم تُجمع أدلة من الصفحة",
    "The site may be offline, or the case was scored from the URL alone.",
)


def build_report(case: Case, related: list[RelatedDomain], now: datetime | None = None) -> bytes:
    """Return the PDF bytes of the evidence report for one case."""
    now = now or datetime.now(timezone.utc)
    pdf = _ReportPDF(case)
    pdf.add_page()
    _summary(pdf, case, now)
    _reasons(pdf, case)
    ev = case.evidence
    if ev is None:
        pdf.section("Page evidence", "أدلة الصفحة")
        pdf.font(9, True, INK)
        pdf.set_x(MARGIN)
        pdf.cell(WIDTH, 5, NO_EVIDENCE[0], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.note(NO_EVIDENCE[1])
    else:
        _screenshot(pdf, ev)
        _redirects(pdf, ev)
        _domain_hosting(pdf, case, ev, now)
        _page_findings(pdf, ev)
    _related(pdf, related)
    _decisions(pdf, case)
    _takedown(pdf, case)
    return bytes(pdf.output())


# ---- text helpers ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _covered() -> frozenset[int]:
    codes: set[int] = set()
    for file in _FONT_FILES.values():
        codes |= set(TTFont(FONTS_DIR / file, lazy=True).getBestCmap())
    return frozenset(codes)


def _clean(text: object) -> str:
    """Printable text the bundled fonts can draw (scam pages carry emoji and control chars)."""
    covered = _covered()
    out = []
    for ch in str(text):
        if ch == "\n":
            out.append(ch)
        elif ch in "\t\r":
            out.append(" ")
        elif unicodedata.category(ch) in ("Cc", "Cs", "Co", "Cn"):
            continue
        elif ord(ch) in covered or unicodedata.category(ch) in ("Mn", "Cf"):
            out.append(ch)
        else:
            out.append("?")
    return "".join(out)


def _when(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    uae, utc = dt.astimezone(UAE), dt.astimezone(timezone.utc)
    utc_text = f"{utc:%H:%M:%S}" if utc.date() == uae.date() else f"{utc:%Y-%m-%d %H:%M:%S}"
    return f"{uae:%Y-%m-%d %H:%M:%S} UAE (UTC+4)  ·  {utc_text} UTC"


def _brand(case: Case) -> tuple[str | None, str | None]:
    brand = brand_by_id(case.verdict.brand_target)
    if brand:
        return brand.name_en, brand.name_ar
    return case.verdict.brand_target, None


def _headline(case: Case) -> tuple[str, str]:
    name_en, name_ar = _brand(case)
    label = case.verdict.verdict.value
    if label == "FRAUD":
        if name_en:
            ar = f"موقع تصيّد احتيالي ينتحل صفة «{name_ar}»" if name_ar else "موقع تصيّد احتيالي"
            return f"Phishing site impersonating {name_en}", ar
        return "Likely phishing or scam site", "موقع تصيّد أو احتيال على الأرجح"
    if label == "SUSPICIOUS":
        if name_en and name_ar:
            return (
                f"Suspicious site that may impersonate {name_en}: needs review",
                f"موقع مشبوه قد ينتحل صفة «{name_ar}»، ويحتاج إلى مراجعة",
            )
        return "Suspicious site: needs analyst review", "موقع مشبوه يحتاج إلى مراجعة محلل"
    return "No signs of fraud found", "لم تُرصد علامات احتيال"


def _days(n: int) -> str:
    return "1 day" if n == 1 else f"{n} days"


# ---- PDF ------------------------------------------------------------------------------------


class _ReportPDF(FPDF):
    def __init__(self, case: Case) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.case = case
        self.sections = 0
        self.set_margins(MARGIN, 14, MARGIN)
        self.set_auto_page_break(True, margin=20)
        for (family, style), file in _FONT_FILES.items():
            self.add_font(family, style, str(FONTS_DIR / file))
        self.set_fallback_fonts([ARABIC], exact_match=False)
        self.set_text_shaping(True)
        self.c_margin = 0
        self.set_title(f"ScamShield evidence report {case.id}")
        self.set_author("ScamShield")
        self.set_subject(f"{case.verdict.verdict.value} {case.domain}")
        self.set_creator(f"ScamShield {VERSION}")
        self.set_lang("en")

    # fonts and colours
    def font(self, size: float = 9, bold: bool = False, color=INK) -> None:
        self.set_font(LATIN, "B" if bold else "", size)
        self.set_text_color(*color)
        # fpdf2 sets the font for a line that starts with fallback (Arabic) glyphs inside that
        # line's q/Q block, then believes the page font is set; the next Latin text would be
        # drawn with the wrong font (garbled glyphs). Always set the page font explicitly.
        if self.page > 0:
            self._out(self._set_font_for_page(self.current_font, self.font_size_pt))

    def header(self) -> None:
        if self.page_no() == 1:
            self.set_fill_color(*NAVY)
            self.rect(0, 0, 210, 30, style="F")
            self.set_xy(MARGIN, 8)
            self.font(18, True, WHITE)
            self.cell(90, 8, "ScamShield")
            self.font(16, True, WHITE)
            self.set_xy(MARGIN + 90, 8)
            self.cell(WIDTH - 90, 8, "تقرير الأدلة", align="R")
            self.set_xy(MARGIN, 17)
            self.font(10.5, False, (203, 213, 225))
            self.cell(90, 6, f"Evidence Report  ·  Case {self.case.id}")
            self.set_xy(MARGIN + 90, 17)
            self.cell(WIDTH - 90, 6, "تقرير قضية احتيال إلكتروني", align="R")
            self.set_y(33)
            return
        self.set_y(8)
        self.font(8, True, NAVY)
        self.cell(WIDTH / 2, 5, f"ScamShield Evidence Report  ·  {self.case.id}")
        self.font(8, True, NAVY)
        self.cell(WIDTH / 2, 5, "تقرير الأدلة", align="R")
        self.set_draw_color(*NAVY)
        self.set_line_width(0.3)
        self.line(MARGIN, 14, MARGIN + WIDTH, 14)
        self.set_y(18)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_draw_color(*RULE)
        self.set_line_width(0.2)
        self.line(MARGIN, self.get_y(), MARGIN + WIDTH, self.get_y())
        self.set_y(-13.5)
        self.font(7.5, False, MUTED)
        line = (
            f"ScamShield {VERSION}  ·  {self.case.verdict.model_version}  ·  "
            f"page {self.page_no()} of {{nb}}"
        )
        self.cell(WIDTH / 2, 4, line)
        self.cell(WIDTH / 2, 4, f"Case {self.case.id}", align="R")
        self.set_xy(MARGIN, -9.5)
        self.font(7.5, True, MUTED)
        self.cell(WIDTH / 2, 4, "Automated assessment — confirm before acting")
        self.cell(WIDTH / 2, 4, "تقييم آلي — يُرجى التحقق قبل اتخاذ أي إجراء", align="R")

    # measuring and drawing
    def lines(self, w: float, text: str) -> int:
        return len(self.multi_cell(w, 4, text, dry_run=True, output=MethodReturnValue.LINES))

    def room(self, height: float) -> None:
        """Start a new page unless `height` mm still fit on this one."""
        if self.get_y() + height > self.page_break_trigger:
            self.add_page()

    def section(self, en: str, ar: str) -> None:
        self.sections += 1
        number = self.sections
        self.room(24)
        self.ln(4)
        y = self.get_y()
        self.font(11.5, True, NAVY)
        self.set_x(MARGIN)
        self.cell(WIDTH / 2, 7, f"{number}.  {en}")
        self.cell(WIDTH / 2, 7, ar, align="R")
        self.set_draw_color(*NAVY)
        self.set_line_width(0.4)
        self.line(MARGIN, y + 7.5, MARGIN + WIDTH, y + 7.5)
        self.set_y(y + 9.5)

    def row(self, cells: list[dict], header: dict | None = None, shade: bool = False) -> None:
        """One table row of wrapped cells, kept on one page.

        A cell is {text, w, align?, size?, bold?, color?, link?}. `header`, when given,
        is redrawn first if the row moves to a new page.
        """
        line_h = {}
        heights = []
        for c in cells:
            size = c.get("size", 9)
            self.font(size, c.get("bold", False))
            line_h[id(c)] = size * 0.47
            n = self.lines(c["w"] - 2 * PAD, c["text"])
            heights.append(n * line_h[id(c)])
        height = max(heights) + 2 * PAD
        if self.get_y() + height > self.page_break_trigger:
            self.add_page()
            if header:
                self.row(**header)
        y = self.get_y()
        if shade:
            self.set_fill_color(*SHADE)
            self.rect(MARGIN, y, sum(c["w"] for c in cells), height, style="F")
        x = MARGIN
        for c in cells:
            self.font(c.get("size", 9), c.get("bold", False), c.get("color", INK))
            self.set_xy(x + PAD, y + PAD)
            self.multi_cell(
                c["w"] - 2 * PAD,
                line_h[id(c)],
                c["text"],
                align=c.get("align", "L"),
                link=c.get("link"),
                new_x=XPos.LEFT,
                new_y=YPos.NEXT,
            )
            x += c["w"]
        self.set_draw_color(*RULE)
        self.set_line_width(0.2)
        self.line(MARGIN, y + height, MARGIN + sum(c["w"] for c in cells), y + height)
        self.set_xy(MARGIN, y + height)

    def kv(
        self,
        en: str,
        ar: str,
        value: object,
        *,
        bold: bool = False,
        color=INK,
        link: str | None = None,
        align: str = "L",
    ) -> None:
        """English label | value | Arabic label, as on UAE bilingual forms."""
        missing = value is None or value == "" or value == []
        text = "Not recorded" if missing else _clean(value)
        self.row(
            [
                {"text": en, "w": LABEL_W, "size": 8, "bold": True, "color": MUTED},
                {
                    "text": text,
                    "w": WIDTH - 2 * LABEL_W,
                    "bold": bold and not missing,
                    "color": MUTED if missing else color,
                    "link": None if missing else link,
                    "align": align,
                },
                {"text": ar, "w": LABEL_W, "size": 8, "bold": True, "color": MUTED, "align": "R"},
            ]
        )

    def note(self, text: str, color=MUTED, size: float = 8.5) -> None:
        self.font(size, False, color)
        self.set_x(MARGIN)
        self.multi_cell(
            WIDTH, size * 0.47, _clean(text), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )
        self.ln(1)


# ---- sections ---------------------------------------------------------------------------------


def _th(text: str, w: float, align: str = "L") -> dict:
    """Table heading cell."""
    return {"text": text, "w": w, "size": 8, "bold": True, "color": NAVY, "align": align}


def _summary(pdf: _ReportPDF, case: Case, now: datetime) -> None:
    pdf.section("Summary", "الملخص")
    label = case.verdict.verdict.value
    name_en, name_ar, colour = VERDICTS[label]
    head_en, head_ar = _headline(case)

    # Verdict badge: colour plus the label written out, never colour alone.
    y = pdf.get_y() + 1
    badge_w, badge_h = 46, 24
    pdf.set_fill_color(*colour)
    pdf.rect(MARGIN, y, badge_w, badge_h, style="F", round_corners=True, corner_radius=2)
    pdf.set_xy(MARGIN, y + 2.5)
    pdf.font(15, True, WHITE)
    pdf.cell(badge_w, 7, name_en, align="C")
    pdf.set_xy(MARGIN, y + 9.5)
    pdf.font(10, False, WHITE)
    pdf.cell(badge_w, 6, f"Risk score {case.verdict.score}/100", align="C")
    pdf.set_xy(MARGIN, y + 15.5)
    pdf.font(10.5, True, WHITE)
    pdf.cell(badge_w, 6, name_ar, align="C")

    text_x = MARGIN + badge_w + 6
    text_w = WIDTH - badge_w - 6
    pdf.set_xy(text_x, y + 1)
    pdf.font(12.5, True, colour)
    pdf.multi_cell(text_w, 6, _clean(head_en), new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.set_x(text_x)
    pdf.font(12, True, colour)
    pdf.multi_cell(text_w, 6.5, _clean(head_ar), align="R", new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.set_x(text_x)
    pdf.font(8, False, MUTED)
    pdf.multi_cell(
        text_w,
        4,
        f"Scored by {case.verdict.model_version} at {_when(case.verdict.scored_at)}",
        new_x=XPos.LEFT,
        new_y=YPos.NEXT,
    )
    pdf.set_xy(MARGIN, max(pdf.get_y(), y + badge_h) + 3)

    ev = case.evidence
    cand = case.candidate
    pdf.kv("Case ID", "رقم القضية", case.id, bold=True)
    pdf.kv("Report generated", "تاريخ التقرير", _when(now))
    brand_en, brand_ar = _brand(case)
    brand = f"{brand_en}  ·  {brand_ar}" if brand_en and brand_ar else brand_en
    pdf.kv("Brand targeted", "الجهة المستهدفة", brand or "None identified")
    pdf.kv("URL", "الرابط", cand.url)
    pdf.kv("Final URL", "الرابط النهائي", (ev.final_url if ev else None) or cand.url)
    pdf.kv("Domain", "النطاق", case.domain, bold=True)
    source = SOURCES.get(cand.source.value, cand.source.value)
    if cand.query:
        source += f"  ·  query: “{cand.query}”"
    pdf.kv("Source", "المصدر", source)
    extra = cand.extra
    if extra.listing_name or extra.phone or extra.address:
        listing = "  ·  ".join(x for x in (extra.listing_name, extra.phone, extra.address) if x)
        pdf.kv("Listing", "بيانات الإدراج", listing)
    pdf.kv("First seen", "أول رصد", _when(cand.discovered_at))
    status_en, status_ar = STATUSES.get(case.status, (case.status, case.status))
    pdf.kv("Case status", "حالة القضية", f"{status_en}  ·  {status_ar}")


def _reasons(pdf: _ReportPDF, case: Case) -> None:
    pdf.section("Reasons for the score", "أسباب التقييم")
    w_weight, w_text = 16, (WIDTH - 16) / 2
    header = {
        "cells": [
            _th("Weight\nالوزن", w_weight, "C"),
            _th("Reason (English)", w_text),
            _th("السبب (العربية)", w_text, "R"),
        ],
        "shade": True,
    }
    pdf.row(**header)
    if not case.verdict.reasons:
        pdf.note("No reasons recorded.")
        return
    for r in sorted(case.verdict.reasons, key=lambda r: -r.weight):
        colour = VERDICTS["FRAUD"][2] if r.weight > 0 else VERDICTS["LEGIT"][2]
        pdf.row(
            [
                {
                    "text": f"{r.weight:+d}",
                    "w": w_weight,
                    "bold": True,
                    "color": colour,
                    "align": "C",
                },
                {"text": _clean(r.text_en), "w": w_text},
                {"text": _clean(r.text_ar), "w": w_text, "align": "R"},
            ],
            header=header,
        )
    pdf.note(
        "Positive weights raise the risk, negative weights lower it. "
        f"Final score {case.verdict.score}/100: FRAUD from 70, SUSPICIOUS from 30."
    )


def _artifact(rel: str | None) -> Path | None:
    """The artifact file, only if it exists inside the artifacts dir."""
    if not rel:
        return None
    root = ARTIFACTS_DIR.resolve()
    path = (root / rel).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path if path.is_file() else None


def _svg_size(path: Path) -> tuple[float, float]:
    head = path.read_text(encoding="utf-8", errors="ignore")[:2000]
    box = re.search(r'viewBox="[\d.\-]+[ ,]+[\d.\-]+[ ,]+([\d.]+)[ ,]+([\d.]+)"', head)
    if box:
        return float(box.group(1)), float(box.group(2))
    w, h = re.search(r'width="([\d.]+)', head), re.search(r'height="([\d.]+)', head)
    return (float(w.group(1)), float(h.group(1))) if w and h else (16.0, 10.0)


def _image(path: Path) -> tuple[object, float, float] | None:
    """(image for fpdf, width px, height px): tall captures cropped to the top, downscaled."""
    try:
        if path.suffix.lower() == ".svg":
            w, h = _svg_size(path)
            return str(path), w, h
        with Image.open(path) as im:
            im = im.convert("RGB")
            w, h = im.size
            if h > w * 1.75:  # full-page phone capture: keep the first screen
                im = im.crop((0, 0, w, int(w * 1.75)))
            im.thumbnail((900, 1600))
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=82, optimize=True)
            buf.seek(0)
            return buf, im.size[0], im.size[1]
    except Exception:  # a broken capture must not break the report
        return None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _screenshot(pdf: _ReportPDF, ev: Evidence) -> None:
    pdf.section("Screenshot", "لقطة الشاشة")
    path = _artifact(ev.screenshot_path)
    pdf.kv("SHA-256", "بصمة SHA-256", ev.screenshot_sha256)
    if path and ev.screenshot_sha256:
        same = _sha256(path) == ev.screenshot_sha256
        pdf.kv(
            "Integrity",
            "سلامة الملف",
            "Stored file matches the hash recorded at capture"
            if same
            else "WARNING: stored file does not match the hash recorded at capture",
            color=VERDICTS["LEGIT"][2] if same else VERDICTS["FRAUD"][2],
        )
    pdf.kv("Captured at", "وقت الالتقاط", _when(ev.fetched_at))
    pdf.kv("Browser", "المتصفح", PROFILES.get(ev.profile, ev.profile))
    pdf.kv("File", "الملف", ev.screenshot_path)

    if not ev.screenshot_path:
        pdf.ln(2)
        pdf.note("No screenshot was captured" + (f": {ev.fetch_error}" if ev.fetch_error else "."))
        return
    shots = [("UAE phone visit", "زيارة من هاتف في الإمارات", path)]
    desktop = ev.cloaking.desktop if ev.cloaking else None
    if desktop and desktop.screenshot_path:
        shots.append(
            (
                "Foreign desktop visit (cloaking check)",
                "زيارة من حاسوب خارج الإمارات",
                _artifact(desktop.screenshot_path),
            )
        )

    gap = 8
    box_w = (WIDTH - gap * (len(shots) - 1)) / len(shots)
    max_w, max_h = min(box_w, 130), 115
    placed = []
    for en, ar, file in shots:
        img = _image(file) if file else None
        if img is None:
            placed.append((en, ar, None, 64, 28))
            continue
        src, wpx, hpx = img
        scale = min(max_w / wpx, max_h / hpx)
        placed.append((en, ar, src, wpx * scale, hpx * scale))
    tallest = max(p[4] for p in placed)
    pdf.ln(3)
    pdf.room(tallest + 14)
    y = pdf.get_y()
    for i, (en, ar, src, w, h) in enumerate(placed):
        x0 = MARGIN + i * (box_w + gap)
        x = x0 + (box_w - w) / 2
        if src is not None:
            try:
                pdf.image(src, x=x, y=y, w=w, h=h)
            except Exception:  # an unreadable file must not break the report
                src = None
        if src is None:
            pdf.set_fill_color(*SHADE)
            pdf.rect(x, y, w, h, style="F")
            pdf.set_xy(x + 3, y + h / 2 - 4)
            pdf.font(8, False, MUTED)
            pdf.multi_cell(w - 6, 4, "Screenshot file not available on this server", align="C")
        pdf.set_draw_color(*RULE)
        pdf.set_line_width(0.3)
        pdf.rect(x, y, w, h)
        pdf.set_xy(x0, y + tallest + 1.5)
        pdf.font(8, True, MUTED)
        pdf.cell(box_w, 4, en, align="C")
        pdf.set_xy(x0, y + tallest + 5.5)
        pdf.cell(box_w, 4, ar, align="C")
    pdf.set_xy(MARGIN, y + tallest + 11)


def _redirects(pdf: _ReportPDF, ev: Evidence) -> None:
    pdf.section("Redirect chain", "سلسلة إعادة التوجيه")
    if not ev.redirect_chain:
        pdf.note(
            f"No redirects recorded: the link opened directly (HTTP {ev.http_status or 'status unknown'})."
        )
        return
    header = {
        "cells": [
            _th("Hop\nخطوة", 12, "C"),
            _th("HTTP", 16, "C"),
            _th("URL / الرابط", WIDTH - 28),
        ],
        "shade": True,
    }
    pdf.row(**header)
    for i, hop in enumerate(ev.redirect_chain, 1):
        pdf.row(
            [
                {"text": str(i), "w": 12, "align": "C"},
                {"text": str(hop.status or "—"), "w": 16, "align": "C"},
                {"text": _clean(hop.url), "w": WIDTH - 28},
            ],
            header=header,
        )


def _domain_hosting(pdf: _ReportPDF, case: Case, ev: Evidence, now: datetime) -> None:
    pdf.section("Domain and hosting", "النطاق والاستضافة")
    rdap = ev.rdap
    pdf.kv("Registrar", "المسجّل", rdap.registrar if rdap else None)
    created = rdap.created if rdap else None
    if created:
        c = created if created.tzinfo else created.replace(tzinfo=timezone.utc)
        text = f"{c.astimezone(timezone.utc):%Y-%m-%d} UTC"
        age = domain_age_days(ev, now)
        if age is not None:
            seen = case.candidate.discovered_at
            seen = seen if seen.tzinfo else seen.replace(tzinfo=timezone.utc)
            before = (seen.astimezone(timezone.utc).date() - c.astimezone(timezone.utc).date()).days
            text += f"  ·  {_days(age)} old"
            if before >= 0:
                text += f"  ·  registered {_days(before)} before first seen"
        elif ev.shared_hosting:
            text += "  ·  the shared platform's record, not the site owner's"
        pdf.kv("Registered", "تاريخ التسجيل", text)
    else:
        pdf.kv("Registered", "تاريخ التسجيل", None)
    pdf.kv("Registrar abuse email", "بريد بلاغات المسجّل", rdap.abuse_email if rdap else None)
    pdf.kv("IP address", "عنوان IP", ev.ip)
    pdf.kv("ASN", "رقم النظام المستقل", f"AS{ev.asn}" if ev.asn else None)
    pdf.kv("Hosting provider", "مزوّد الاستضافة", ev.hosting_org)
    pdf.kv("Hosting abuse email", "بريد بلاغات المستضيف", ev.hosting_abuse_email)
    if ev.shared_hosting:
        pdf.kv(
            "Shared platform",
            "منصة مشتركة",
            "Yes. The site lives on a shared platform: the WHOIS registrar, domain age and IP "
            "belong to the platform, not to the site owner. Report it to the host.",
            bold=True,
            color=VERDICTS["SUSPICIOUS"][2],
        )
    else:
        pdf.kv("Shared platform", "منصة مشتركة", "No: WHOIS and IP describe this site's own domain")


def _forms_text(ev: Evidence) -> str | None:
    parts = []
    for i, f in enumerate(ev.forms[:6], 1):
        asks = [SENSITIVE.get(s, s.replace("_", " ")) for s in f.sensitive]
        lines = [f"Form {i}" + (f" sends to {f.action[:300]}" if f.action else "")]
        if asks:
            lines.append("Asks for: " + ", ".join(asks))
        hints = [h for h in f.field_hints if h not in f.sensitive]
        if hints:
            lines.append("Fields: " + ", ".join(hints[:12]))
        parts.append("\n".join(lines))
    if len(ev.forms) > 6:
        parts.append(f"... and {len(ev.forms) - 6} more forms")
    return "\n".join(parts) or None


def _page_findings(pdf: _ReportPDF, ev: Evidence) -> None:
    pdf.section("Page findings", "نتائج فحص الصفحة")
    if ev.fetch_error:
        pdf.kv("Fetch error", "خطأ في الجلب", ev.fetch_error, color=VERDICTS["SUSPICIOUS"][2])
    pdf.kv("Page title", "عنوان الصفحة", ev.title)
    pdf.kv("HTTP status", "رمز HTTP", ev.http_status)
    kind = PAGE_KINDS.get(ev.page_kind or "", ev.page_kind)
    if ev.page_kind not in (None, "content"):
        kind = f"{kind}. A placeholder says nothing about who owns the domain."
    pdf.kv("Page kind", "نوع الصفحة", kind or "Not classified")
    pdf.kv("Forms", "النماذج", _forms_text(ev) or "No forms on the page")
    signals = [
        f"{DOWNLOADS.get(s.kind, s.kind)}: {(s.href or s.text or '')[:300]}".rstrip(": ")
        for s in ev.download_signals[:8]
    ]
    pdf.kv(
        "Downloads / remote access",
        "التنزيلات / التحكم عن بعد",
        "\n".join(signals) or "None found",
        color=VERDICTS["FRAUD"][2] if signals else INK,
    )
    if ev.cloaking is None:
        cloak = "Not checked"
    elif ev.cloaking.signals:
        cloak = "\n".join(CLOAKING.get(s, s) for s in ev.cloaking.signals)
    else:
        cloak = "No difference between the UAE phone visit and the foreign desktop visit"
    pdf.kv(
        "Cloaking check",
        "فحص الإخفاء",
        cloak,
        color=VERDICTS["FRAUD"][2] if ev.cloaking and ev.cloaking.signals else INK,
    )
    desktop = ev.cloaking.desktop if ev.cloaking else None
    if desktop:
        status = f"HTTP {desktop.http_status}" if desktop.http_status else None
        parts = [x for x in (status, desktop.title, desktop.final_url) if x]
        seen = desktop.fetch_error or "  ·  ".join(parts)
        pdf.kv("Desktop visit saw", "ما رآه زائر الحاسوب", seen)
    vm = ev.visual_match
    if vm:
        brand = brand_by_id(vm.brand)
        what = "favicon" if vm.kind == "same_favicon" else "page template"
        text = f"Reuses the official {brand.name_en if brand else vm.brand} site's {what}"
        if vm.reference_url:
            text += f" (reference: {vm.reference_url})"
        pdf.kv("Visual match", "تطابق بصري", text, color=VERDICTS["FRAUD"][2])
    else:
        pdf.kv("Visual match", "تطابق بصري", "No copy of an official site's favicon or template")
    fp = ev.fingerprints
    if fp:
        ct = fp.contacts
        contacts = [
            f"{name}: {', '.join(vals[:6])}"
            for name, vals in (
                ("Phone", ct.phones),
                ("WhatsApp", ct.whatsapp),
                ("Telegram", ct.telegram),
                ("Email", ct.emails),
            )
            if vals
        ]
        pdf.kv("Contacts on page", "جهات الاتصال", "\n".join(contacts) or "None found")
        if fp.tracking_ids:
            pdf.kv("Tracking IDs", "معرّفات التتبع", ", ".join(fp.tracking_ids[:10]))
        if fp.favicon_mmh3 is not None:
            pdf.kv("Favicon hash", "بصمة الأيقونة", f"{fp.favicon_mmh3} (Shodan http.favicon.hash)")
    if ev.text_excerpt:
        excerpt = ev.text_excerpt[:600] + ("…" if len(ev.text_excerpt) > 600 else "")
        pdf.kv("Visible text (excerpt)", "نص الصفحة (مقتطف)", excerpt, color=MUTED)


def _related(pdf: _ReportPDF, related: list[RelatedDomain]) -> None:
    pdf.section("Related domains", "نطاقات مرتبطة")
    if not related:
        pdf.note("No other case shares infrastructure with this one.")
        return
    widths = (64, 30, WIDTH - 94)
    header = {
        "cells": [
            _th("Domain / النطاق", widths[0]),
            _th("Verdict / التقييم", widths[1]),
            _th("Shared with this case / القواسم المشتركة", widths[2]),
        ],
        "shade": True,
    }
    pdf.row(**header)
    by_case: dict[str, list[RelatedDomain]] = {}
    for r in related:
        by_case.setdefault(r.case_id, []).append(r)
    for links in by_case.values():
        first = links[0]
        colour = VERDICTS.get(first.verdict.value, ("", "", INK))[2]
        pdf.row(
            [
                {"text": f"{_clean(first.domain)}\nCase {first.case_id}", "w": widths[0]},
                {
                    "text": f"{first.verdict.value} {first.score}",
                    "w": widths[1],
                    "bold": True,
                    "color": colour,
                },
                {
                    "text": "\n".join(_clean(r.detail) for r in links),
                    "w": widths[2],
                },
            ],
            header=header,
        )
    pdf.note("A shared trait suggests one operator; it is a lead to check, not proof.")


def _decisions(pdf: _ReportPDF, case: Case) -> None:
    pdf.section("Analyst decisions", "قرارات المحلل")
    if not case.decisions:
        pdf.note("No analyst decision recorded yet.")
        return
    widths = (24, 28, 52, WIDTH - 104)
    titles = ("Action / الإجراء", "By / بواسطة", "At / الوقت", "Reason / السبب")
    header = {"cells": [_th(t, w) for t, w in zip(titles, widths)], "shade": True}
    pdf.row(**header)
    for d in case.decisions:
        pdf.row(
            [
                {"text": d.action.capitalize(), "w": widths[0], "bold": True},
                {"text": _clean(d.by), "w": widths[1]},
                {"text": _when(d.at).replace("  ·  ", "\n"), "w": widths[2], "size": 8},
                {"text": _clean(d.reason), "w": widths[3]},
            ],
            header=header,
        )


def _takedown(pdf: _ReportPDF, case: Case) -> None:
    pdf.section("Takedown request", "طلب الإزالة")
    if case.verdict.verdict.value == "LEGIT":
        pdf.note("Not needed: the site is assessed as legitimate.")
        return
    t = build_takedown(case)
    pdf.kv(
        "Send to",
        "يُرسل إلى",
        ", ".join(t.recipients) or "No abuse contact found: report through the registry or host",
        link=t.mailto,
        bold=bool(t.recipients),
        color=NAVY,
    )
    pdf.kv("Subject", "الموضوع", t.subject)
    shared = case.evidence is not None and case.evidence.shared_hosting
    registrar = t.registrar or (
        "Not contacted: on a shared platform the domain belongs to the platform" if shared else None
    )
    pdf.kv("Registrar", "المسجّل", registrar)
    pdf.kv("Hosting provider", "مزوّد الاستضافة", t.hosting_org)
    pdf.note(
        f"The full request text in English and Arabic is at GET /api/cases/{case.id}/takedown; "
        f"the evidence bundle is at GET /api/cases/{case.id}/export.json."
    )
