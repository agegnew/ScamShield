"""Batch mode: a file of URLs in, a CSV of verdicts out (for the judges' hidden test set).

Run from backend/:
  python -m scripts.batch urls.txt -o verdicts.csv                # URL only: ~1 ms per URL
  python -m scripts.batch urls.txt -o verdicts.csv --mode whois   # + domain age and hosting (RDAP, DNS)
  python -m scripts.batch urls.csv -o verdicts.csv --mode full    # + page fetch (screenshot, forms, brand text)

Input: a .txt file with one URL per line (blank lines and lines starting with # are skipped), or a
.csv file with a `url` column (otherwise the first column is used). If the CSV also has a `label`
column (1/0, fraud/legit, phishing/benign), precision and recall are printed at the end.

Output columns: url, verdict (FRAUD/SUSPICIOUS/LEGIT), flagged (1 = FRAUD or SUSPICIOUS), score,
brand_target, final_url, reason_codes, reasons_en, reasons_ar, error (+ label when given). The file
is UTF-8 with a byte-order mark so Excel shows the Arabic reasons correctly.

Phishing-feed lookups (PhishTank, OpenPhish) are on unless --no-feeds; --refresh-feeds downloads
fresh copies first. The page fetch needs the worker packages and Playwright Chromium
(pip install -r requirements-worker.txt && playwright install chromium).
"""

import argparse
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from app import engine
from app.contracts import Evidence, Label, Verdict
from app.engine import feeds
from app.urls import InvalidURL, normalize_url

FRAUD_LABELS = {"1", "fraud", "phishing", "malicious", "scam", "bad", "true", "yes"}
LEGIT_LABELS = {"0", "legit", "legitimate", "benign", "safe", "good", "false", "no"}
COLUMNS = [
    "url", "verdict", "flagged", "score", "brand_target", "final_url",
    "reason_codes", "reasons_en", "reasons_ar", "error",
]


def parse_label(raw: str | None) -> int | None:
    value = (raw or "").strip().lower()
    if value in FRAUD_LABELS:
        return 1
    if value in LEGIT_LABELS:
        return 0
    return None


def read_input(path: Path) -> list[tuple[str, int | None]]:
    """(url, label or None) per row, in file order."""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if path.suffix.lower() != ".csv":
        lines = (line.strip() for line in text.splitlines())
        return [(line, None) for line in lines if line and not line.startswith("#")]
    rows = list(csv.reader(text.splitlines()))
    if not rows:
        return []
    header = [h.strip().lower() for h in rows[0]]
    if "url" in header:
        url_col, body = header.index("url"), rows[1:]
        label_col = next((header.index(n) for n in ("label", "is_fraud", "class") if n in header), None)
    else:  # no header: first column holds the URLs
        url_col, body, label_col = 0, rows, None
    out = []
    for row in body:
        if len(row) <= url_col or not row[url_col].strip():
            continue
        label = parse_label(row[label_col]) if label_col is not None and len(row) > label_col else None
        out.append((row[url_col].strip(), label))
    return out


def evidence_for(url: str, mode: str) -> Evidence | None:
    if mode == "url":
        return None
    if mode == "whois":
        from app.workers import enrich

        page = Evidence(url=url, fetched_at=datetime.now(timezone.utc), fetch_error="Page not fetched (whois mode)")
        return enrich.enrich(page)
    from app.workers import evidence as collector

    return collector.collect(url)


def judge(raw: str, mode: str, use_feeds: bool) -> dict:
    try:
        url = normalize_url(raw)
    except InvalidURL as exc:
        return {"url": raw, "error": str(exc)}
    error = ""
    try:
        evidence = evidence_for(url, mode)
    except Exception as exc:  # one bad site must not stop the batch; fall back to the URL alone
        evidence, error = None, f"{mode} lookup failed ({type(exc).__name__}); scored from the URL only"
    if mode == "full" and evidence is not None:
        # Borderline pages also get Claude's look (app/workers/ai_review.py); off without ANTHROPIC_API_KEY.
        from app.workers import ai_review

        evidence, verdict = ai_review.score_with_review(url, evidence, use_feeds=use_feeds)
    else:
        verdict: Verdict = engine.score(url, evidence=evidence, use_feeds=use_feeds)
    final_url = evidence.final_url if evidence and evidence.final_url else ""
    if evidence and evidence.fetch_error and mode == "full" and not error:
        error = evidence.fetch_error
    return {
        "url": raw,
        "verdict": verdict.verdict.value,
        "flagged": int(verdict.verdict != Label.LEGIT),
        "score": verdict.score,
        "brand_target": verdict.brand_target or "",
        "final_url": final_url if final_url != url else "",
        "reason_codes": ";".join(r.code for r in verdict.reasons),
        "reasons_en": " | ".join(f"{r.weight:+d} {r.text_en}" for r in verdict.reasons),
        "reasons_ar": " | ".join(f"{r.weight:+d} {r.text_ar}" for r in verdict.reasons),
        "error": error,
    }


def metrics(results: list[dict], labels: list[int | None]) -> dict | None:
    pairs = [(r.get("flagged"), label) for r, label in zip(results, labels) if label is not None and "flagged" in r]
    if not pairs:
        return None
    tp = sum(1 for f, label in pairs if f and label)
    fp = sum(1 for f, label in pairs if f and not label)
    fn = sum(1 for f, label in pairs if not f and label)
    tn = sum(1 for f, label in pairs if not f and not label)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "n": len(pairs), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": round(precision, 4), "recall": round(recall, 4),
        "fpr": round(fp / (fp + tn), 4) if fp + tn else 0.0, "f1": round(f1, 4),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score a file of URLs and write a CSV of verdicts.")
    parser.add_argument("input", type=Path, help=".txt (one URL per line) or .csv with a url column")
    parser.add_argument("-o", "--output", type=Path, help="CSV to write (default: <input>-verdicts.csv)")
    parser.add_argument("--mode", choices=("url", "whois", "full"), default="url",
                        help="url: URL only (fast); whois: + domain age and hosting; full: + page fetch")
    parser.add_argument("--workers", type=int, default=0, help="parallel lookups (default 1 / 16 / 4 by mode)")
    parser.add_argument("--no-feeds", action="store_true", help="skip PhishTank / OpenPhish lookups")
    parser.add_argument("--refresh-feeds", action="store_true", help="download fresh phishing feeds first")
    parser.add_argument("--limit", type=int, default=0, help="only the first N URLs")
    args = parser.parse_args(argv)

    rows = read_input(args.input)
    if args.limit:
        rows = rows[: args.limit]
    if not rows:
        print(f"no URLs found in {args.input}", file=sys.stderr)
        return 1
    output = args.output or args.input.with_name(f"{args.input.stem}-verdicts.csv")
    if args.refresh_feeds:
        feeds.refresh()
    use_feeds = not args.no_feeds
    workers = args.workers or {"url": 1, "whois": 16, "full": 4}[args.mode]

    started = time.monotonic()
    urls = [url for url, _ in rows]
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, result in enumerate(pool.map(lambda u: judge(u, args.mode, use_feeds), urls), 1):
            results.append(result)
            if i % 100 == 0 or (args.mode != "url" and i % 10 == 0):
                print(f"  {i}/{len(urls)} scored", file=sys.stderr)

    labels = [label for _, label in rows]
    has_labels = any(label is not None for label in labels)
    columns = COLUMNS + (["label"] if has_labels else [])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for result, label in zip(results, labels):
            writer.writerow({c: "" for c in columns} | result | ({"label": label} if has_labels else {}))

    counts = {v.value: sum(1 for r in results if r.get("verdict") == v.value) for v in Label}
    errors = sum(1 for r in results if "verdict" not in r)
    print(
        f"{len(results)} URLs in {time.monotonic() - started:.1f}s  mode {args.mode}  feeds {'on' if use_feeds else 'off'}"
        f"  engine {engine.core.model_version()}"
    )
    print("  " + "  ".join(f"{k} {n}" for k, n in counts.items()) + (f"  invalid {errors}" if errors else ""))
    summary = metrics(results, labels)
    if summary:
        print(
            f"  labelled {summary['n']}: precision {summary['precision']:.3f}  recall {summary['recall']:.3f}"
            f"  FPR {summary['fpr']:.3f}  F1 {summary['f1']:.3f}  (TP {summary['tp']} FP {summary['fp']}"
            f" TN {summary['tn']} FN {summary['fn']})"
        )
        output.with_suffix(".metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
