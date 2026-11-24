"""The trained URL model (scripts/train_url_model.py). Optional: if the file is
missing the engine still runs on its rules."""

import logging
from functools import lru_cache

import joblib

from ..config import MODELS_DIR

MODEL_PATH = MODELS_DIR / "url_model.joblib"
log = logging.getLogger("scamshield.engine")


@lru_cache(maxsize=1)
def _load():
    if not MODEL_PATH.exists():
        log.warning("URL model not found at %s; scoring without it", MODEL_PATH)
        return None
    return joblib.load(MODEL_PATH)


def phishing_probability(url: str) -> float | None:
    model = _load()
    if model is None:
        return None
    return float(model.predict_proba([url])[0][1])


def model_name() -> str:
    return "url-model" if _load() is not None else "no-model"
