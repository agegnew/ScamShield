"""Check data/brands.json before committing it (Samri).

Run from backend/:  python -m scripts.validate_brands
"""

import re
import sys
from collections import Counter

from pydantic import ValidationError

from app.brands import normalize_uae_phone
from app.config import BRANDS_PATH, REPO_DIR
from app.contracts import BrandRegistry

DOMAIN = re.compile(r"^(?!-)[a-z0-9-]+(\.[a-z0-9-]+)+$")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        registry = BrandRegistry.model_validate_json(BRANDS_PATH.read_text(encoding="utf-8"))
    except (ValidationError, ValueError) as exc:
        print(f"brands.json is not valid:\n{exc}")
        return 1

    problems: list[str] = []
    ids = Counter(b.id for b in registry.brands)
    problems += [f"duplicate id: {i}" for i, n in ids.items() if n > 1]

    owner: dict[str, str] = {}
    for brand in registry.brands:
        where = f"[{brand.id}]"
        if not re.fullmatch(r"[a-z0-9_]+", brand.id):
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

    if problems:
        print(f"{len(problems)} problem(s) in {BRANDS_PATH.name}:")
        print("\n".join(f"  - {p}" for p in problems))
        return 1
    print(f"OK: {len(registry.brands)} brands, version '{registry.version}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
