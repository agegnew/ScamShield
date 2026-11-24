"""Check data/brands.json and data/scam_themes.json before committing them (Samri).

Run from backend/:  python -m scripts.validate_data
"""

import re
import sys
from collections import Counter

from pydantic import BaseModel, ValidationError

from app.brands import normalize_uae_phone
from app.config import BRANDS_PATH, REPO_DIR, THEMES_PATH
from app.contracts import BrandRegistry, ScamThemeRegistry

DOMAIN = re.compile(r"^(?!-)[a-z0-9-]+(\.[a-z0-9-]+)+$")
SLUG = re.compile(r"[a-z0-9_]+")


def _load(path, model: type[BaseModel]) -> tuple[BaseModel | None, list[str]]:
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8")), []
    except (ValidationError, ValueError, OSError) as exc:
        return None, [f"{path.name} is not valid: {exc}"]


def check_brands() -> tuple[list[str], str]:
    registry, problems = _load(BRANDS_PATH, BrandRegistry)
    if registry is None:
        return problems, ""
    ids = Counter(b.id for b in registry.brands)
    problems += [f"duplicate brand id: {i}" for i, n in ids.items() if n > 1]

    owner: dict[str, str] = {}
    for brand in registry.brands:
        where = f"brands [{brand.id}]"
        if not SLUG.fullmatch(brand.id):
            problems.append(f"{where} id must be lowercase letters, digits or _")
        if not brand.official_domains:
            problems.append(f"{where} needs at least one official domain")
        for domain in brand.official_domains:
            if not DOMAIN.match(domain):
                problems.append(f"{where} '{domain}' must be a bare domain like 'tamm.abudhabi'")
            if domain in owner:
                problems.append(f"{where} '{domain}' is also listed under {owner[domain]}")
            owner[domain] = brand.id
        for phone in brand.helplines:
            if len(normalize_uae_phone(phone)) < 3:
                problems.append(f"{where} helpline '{phone}' has too few digits")
        if not brand.keywords_ar:
            problems.append(f"{where} has no Arabic keywords")
        if brand.logo and not (REPO_DIR / "data" / "logos" / brand.logo).exists():
            problems.append(f"{where} logo file data/logos/{brand.logo} not found")
    return problems, f"{len(registry.brands)} brands"


def check_themes() -> tuple[list[str], str]:
    registry, problems = _load(THEMES_PATH, ScamThemeRegistry)
    if registry is None:
        return problems, ""
    ids = Counter(t.id for t in registry.themes)
    problems += [f"duplicate theme id: {i}" for i, n in ids.items() if n > 1]
    for theme in registry.themes:
        where = f"themes [{theme.id}]"
        if not SLUG.fullmatch(theme.id):
            problems.append(f"{where} id must be lowercase letters, digits or _")
        if not theme.keywords_en or not theme.keywords_ar:
            problems.append(f"{where} needs English and Arabic keywords")
        upper = [k for k in theme.keywords_en if k != k.lower()]
        if upper:
            problems.append(f"{where} English keywords must be lower-case: {upper}")
    return problems, f"{len(registry.themes)} scam themes"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    problems: list[str] = []
    counts: list[str] = []
    for check in (check_brands, check_themes):
        found, count = check()
        problems += found
        if count:
            counts.append(count)
    if problems:
        print(f"{len(problems)} problem(s):")
        print("\n".join(f"  - {p}" for p in problems))
        return 1
    print("OK: " + ", ".join(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
