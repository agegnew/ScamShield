import csv
import json

from scripts import batch


def test_reads_txt_skipping_blanks_and_comments(tmp_path):
    path = tmp_path / "urls.txt"
    path.write_text("# judges' list\nhttps://www.rta.ae/\n\ntamm-fines-pay.xyz/pay\n", encoding="utf-8")
    assert batch.read_input(path) == [("https://www.rta.ae/", None), ("tamm-fines-pay.xyz/pay", None)]


def test_reads_csv_url_and_label_columns(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text("id,URL,Label\n1,https://a.example/,phishing\n2,https://b.example/,legit\n3,,1\n", encoding="utf-8")
    assert batch.read_input(path) == [("https://a.example/", 1), ("https://b.example/", 0)]


def test_reads_csv_without_header(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text("https://a.example/\nhttps://b.example/\n", encoding="utf-8")
    assert [u for u, _ in batch.read_input(path)] == ["https://a.example/", "https://b.example/"]


def test_writes_bilingual_csv_and_metrics(tmp_path):
    path = tmp_path / "urls.csv"
    path.write_text(
        "url,label\nhttps://www.tamm.abudhabi/en/fines,0\nhttps://tamm-fines-pay.xyz/pay,1\nftp://bad,1\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.csv"
    assert batch.main([str(path), "-o", str(out), "--no-feeds"]) == 0

    assert out.read_bytes().startswith(b"\xef\xbb\xbf")  # BOM: Excel shows the Arabic
    rows = list(csv.DictReader(out.open(encoding="utf-8-sig")))
    assert [r["verdict"] for r in rows] == ["LEGIT", rows[1]["verdict"], ""]
    assert rows[1]["flagged"] == "1" and rows[1]["brand_target"] == "tamm"
    assert rows[1]["reasons_en"] and rows[1]["reasons_ar"]
    assert "scheme" in rows[2]["error"]

    summary = json.loads(out.with_suffix(".metrics.json").read_text(encoding="utf-8"))
    assert (summary["tp"], summary["tn"], summary["n"]) == (1, 1, 2)
