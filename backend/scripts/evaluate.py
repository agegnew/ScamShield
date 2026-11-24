"""Measure the engine on the held-out test set (URL-only, no page fetching).

Run from backend/:
  python -m scripts.evaluate              # full engine, phishing feeds OFF (honest number)
  python -m scripts.evaluate --feeds      # with PhishTank/OpenPhish lookups ON
  python -m scripts.evaluate --save       # also write eval/latest.json for GET /api/metrics

A URL counts as flagged when the verdict is FRAUD or SUSPICIOUS.
Feeds are off by default because the test set's phishing URLs come from the
same feeds: with them on, recall would be inflated by lookup, not detection.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone

from app import engine
from app.config import BACKEND_DIR, REPO_DIR
from app.contracts import Label

DATA = REPO_DIR / "data" / "datasets"
RESULTS = BACKEND_DIR / "eval" / "latest.json"


def load(names: list[str]) -> list[tuple[str, int, str]]:
    rows = []
    for name in names:
        with (DATA / name).open(encoding="utf-8") as f:
            rows += [(r["url"], int(r["label"]), r["source"]) for r in csv.DictReader(f)]
    return rows


def rates(tp: int, fp: int, tn: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "fpr": round(fp / (fp + tn), 4) if fp + tn else 0.0,
        "f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feeds", action="store_true", help="use phishing feed lookups")
    parser.add_argument("--save", action="store_true", help="write eval/latest.json")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--show-errors", type=int, default=0)
    args = parser.parse_args()

    rows = load(["test.csv", "test_uae_legit.csv"])
    if args.limit:
        rows = rows[: args.limit]

    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    by_source: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # correct, total
    scores: list[tuple[int, int]] = []
    errors: list[tuple[str, int, int, str]] = []
    for url, label, source in rows:
        verdict = engine.score(url, use_feeds=args.feeds)
        flagged = verdict.verdict != Label.LEGIT
        scores.append((verdict.score, label))
        key = {(True, 1): "tp", (True, 0): "fp", (False, 0): "tn", (False, 1): "fn"}[(flagged, label)]
        counts[key] += 1
        correct = flagged == bool(label)
        by_source[source][0] += correct
        by_source[source][1] += 1
        if not correct:
            top = verdict.reasons[0].code if verdict.reasons else "-"
            errors.append((url, label, verdict.score, top))

    summary = rates(**counts)
    n_fraud = sum(1 for _, label, _ in rows if label)
    print(f"engine {engine.core.model_version()}  feeds {'ON' if args.feeds else 'OFF'}")
    print(f"URLs: {len(rows)} ({n_fraud} fraud, {len(rows) - n_fraud} legit)")
    print(f"TP {counts['tp']}  FP {counts['fp']}  TN {counts['tn']}  FN {counts['fn']}")
    print(
        f"precision {summary['precision']:.3f}  recall {summary['recall']:.3f}  "
        f"FPR {summary['fpr']:.3f}  F1 {summary['f1']:.3f}"
    )
    print("by source (correct / total):")
    for source, (ok, total) in sorted(by_source.items()):
        print(f"  {source:<14} {ok:>5}/{total:<5} {ok / total:.1%}")

    print("threshold sweep (flag when score >= t):")
    for t in (20, 25, 30, 35, 40, 45, 50):
        tp = sum(1 for s, label in scores if s >= t and label)
        fp = sum(1 for s, label in scores if s >= t and not label)
        fn = sum(1 for s, label in scores if s < t and label)
        tn = sum(1 for s, label in scores if s < t and not label)
        r = rates(tp, fp, tn, fn)
        print(f"  t={t:<3} precision {r['precision']:.3f} recall {r['recall']:.3f} FPR {r['fpr']:.3f} F1 {r['f1']:.3f}")

    for url, label, score, top in errors[: args.show_errors]:
        print(f"  {'MISSED' if label else 'FALSE+'} score {score:>3} {top:<22} {url[:110]}")

    if args.save:
        fraud_sources = sorted({s for _, label, s in rows if label})
        legit_sources = sorted({s for _, label, s in rows if not label})
        RESULTS.parent.mkdir(parents=True, exist_ok=True)
        RESULTS.write_text(
            json.dumps(
                {
                    "mode": "live",
                    "dataset": (
                        f"held-out test (sites never seen in training): {n_fraud} phishing "
                        f"({', '.join(fraud_sources)}) + {len(rows) - n_fraud} legit "
                        f"({', '.join(legit_sources)}); URL only, no page fetch; "
                        f"phishing feeds {'on' if args.feeds else 'off'}"
                    ),
                    "model_version": engine.core.model_version(),
                    "n_fraud": n_fraud,
                    "n_legit": len(rows) - n_fraud,
                    **counts,
                    **summary,
                    "evaluated_at": datetime.now(timezone.utc).isoformat(),
                    "by_source": {s: {"correct": ok, "total": t} for s, (ok, t) in by_source.items()},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"saved {RESULTS.relative_to(BACKEND_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
