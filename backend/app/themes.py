from functools import lru_cache

from .config import THEMES_PATH
from .contracts import ScamThemeRegistry


@lru_cache(maxsize=1)
def load_themes() -> ScamThemeRegistry:
    return ScamThemeRegistry.model_validate_json(THEMES_PATH.read_text(encoding="utf-8"))
