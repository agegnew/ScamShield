"""Train the URL model and write the popular-domains list.

Run from backend/ after build_dataset:  python -m scripts.train_url_model
Writes backend/models/url_model.joblib and backend/models/top_domains.txt.

Model: character 3-5-grams of the URL (hashed, so the file stays small) plus
hand-made URL features, then logistic regression. Crawled deep legit pages are
weighted up so the model does not learn "has a path = phishing".
"""

import csv
import sys
import zipfile

import joblib
import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, precision_score, recall_score
from sklearn.pipeline import FeatureUnion, make_pipeline
from sklearn.preprocessing import MaxAbsScaler

from app.config import MODELS_DIR, REPO_DIR
from app.engine.features import UrlLexical, url_text
from app.engine.lists import SHARED_PLATFORMS
from app.urls import registrable_domain

DATA = REPO_DIR / "data" / "datasets"
DEEP_LEGIT_WEIGHT = 4.0
TOP_N = 10000


def read(path):
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r["url"] for r in rows], np.array([int(r["label"]) for r in rows]), [r["source"] for r in rows]


def build_model():
    chars = HashingVectorizer(
        analyzer="char",
        ngram_range=(3, 5),
        n_features=2**18,
        alternate_sign=False,
        preprocessor=url_text,
        norm="l2",
    )
    lexical = make_pipeline(UrlLexical(), MaxAbsScaler())
    return make_pipeline(
        FeatureUnion([("chars", chars), ("lexical", lexical)]),
        LogisticRegression(C=4.0, max_iter=3000, solver="liblinear"),
    )


def write_top_domains() -> None:
    raw = DATA / "raw" / "tranco.zip"
    seen: list[str] = []
    with zipfile.ZipFile(raw) as z, z.open("top-1m.csv") as f:
        for line in f:
            domain = registrable_domain(line.decode().strip().split(",", 1)[1])
            if domain not in SHARED_PLATFORMS and domain not in seen:
                seen.append(domain)
            if len(seen) >= TOP_N:
                break
    (MODELS_DIR / "top_domains.txt").write_text("\n".join(seen) + "\n", encoding="utf-8")
    print(f"wrote top {len(seen)} domains")


def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    X, y, sources = read(DATA / "train.csv")
    weights = np.array([DEEP_LEGIT_WEIGHT if s == "crawl_deep" else 1.0 for s in sources])
    print(f"training on {len(X)} URLs ...")
    model = build_model()
    model.fit(X, y, logisticregression__sample_weight=weights)

    Xt, yt, st = read(DATA / "test.csv")
    pred = model.predict(Xt)
    tn, fp, fn, tp = confusion_matrix(yt, pred).ravel()
    print(
        f"URL model alone on held-out test: precision {precision_score(yt, pred):.3f} "
        f"recall {recall_score(yt, pred):.3f} FPR {fp / (fp + tn):.3f}  (TP {tp} FP {fp} TN {tn} FN {fn})"
    )
    for source in sorted(set(st)):
        idx = [i for i, s in enumerate(st) if s == source]
        hits = sum(pred[i] == yt[i] for i in idx)
        print(f"  {source:<12} correct {hits}/{len(idx)}")

    joblib.dump(model, MODELS_DIR / "url_model.joblib", compress=3)
    size = (MODELS_DIR / "url_model.joblib").stat().st_size / 1e6
    print(f"saved models/url_model.joblib ({size:.1f} MB)")
    write_top_domains()
    return 0


if __name__ == "__main__":
    sys.exit(main())
