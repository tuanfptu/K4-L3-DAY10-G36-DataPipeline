"""Offline self-check cho phan Corruption + Reporting (Nguyen, G36).

Chay (khong can API key / LLM / ChromaDB):
    PYTHONUTF8=1 .venv/Scripts/python.exe tests/verify_corruption_reporting.py

Script nay dung clean-df fixture xay tu data/raw/crossref_records.json + cac dict
metric/quality/freshness gia lap de chung minh 2 ham cua Nguyen chay dung, KHONG
phu thuoc phan viec cua Minh/Tung/Duc Anh.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

# Cho phep import package trong src/ ke ca khi chua `pip install -e .`.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # tranh loi cp1252 tren Windows

import pandas as pd

from core.utils import compact_join, read_json
from ingestion.corruption import corrupt_clean_dataframe
from observability.reporting import generate_corruption_report, generate_phase1_report

OUT_DIR = ROOT / "data" / "_selfcheck"
FAILURES: list[str] = []


def check(name: str, condition: bool) -> None:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    if not condition:
        FAILURES.append(name)


def build_fixture_clean_df() -> pd.DataFrame:
    """Mo phong toi thieu build_clean_dataframe de co df 16 cot cho test."""
    records = read_json(ROOT / "data" / "raw" / "crossref_records.json")
    today = datetime.now(timezone.utc).date()
    rows: list[dict] = []
    for rec in records:
        published = rec.get("published", "")
        try:
            age_days = (today - datetime.fromisoformat(published).date()).days
        except ValueError:
            age_days = 0
        summary = rec.get("summary", "")
        authors_joined = compact_join(rec.get("authors", []))
        categories_joined = compact_join(rec.get("categories", []))
        row = dict(rec)
        row.update({
            "age_days": age_days,
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": len(summary),
            "text_for_embedding": (
                f"Title: {rec.get('title', '')}\n"
                f"Authors: {authors_joined}\n"
                f"Published: {published}\n"
                f"Categories: {categories_joined}\n"
                f"Summary: {summary}"
            ),
        })
        rows.append(row)
    return pd.DataFrame(rows)

def main() -> int:
    clean = build_fixture_clean_df()
    n_clean = len(clean)

    log_path = OUT_DIR / "corruption_log_sample.json"
    corrupted = corrupt_clean_dataframe(clean, log_path)

    print("--- Corruption checks ---")
    required_cols = {"paper_id", "title", "summary", "published", "age_days",
                     "authors_joined", "categories_joined", "summary_chars", "text_for_embedding"}
    check("Clean df fixture co du cot bat buoc", required_cols.issubset(clean.columns))
    check("So dong thay doi sau corruption", len(corrupted) != n_clean)
    check("Co it nhat 1 summary rong", (corrupted["summary"].astype(str).str.len() == 0).any())
    check("Co title < 8 ky tu", (corrupted["title"].astype(str).str.len() < 8).any())
    check("Co paper_id trung lap (duplicate rows)", bool(corrupted["paper_id"].duplicated().any()))
    check("text_for_embedding da rebuild (bat dau 'Title:')",
          corrupted["text_for_embedding"].astype(str).str.startswith("Title:").all())
    check("summary_chars khop len(summary)",
          (corrupted["summary_chars"] == corrupted["summary"].astype(str).str.len()).all())

    log = read_json(log_path)
    check("Log co dung 6 buoc corruption", len(log.get("corruptions", [])) == 6)
    types = {c.get("type") for c in log.get("corruptions", [])}
    expected = {"drop_latest_records", "blank_summary", "inject_noise",
                "truncate_title", "stale_date", "duplicate_rows"}
    check("Log co du 6 loai loi dung ten", types == expected)

    corrupted2 = corrupt_clean_dataframe(clean, OUT_DIR / "corruption_log_sample2.json")
    stable = [c for c in corrupted.columns if c not in ("authors", "categories")]
    check("Corruption tai lap duoc (deterministic)", corrupted[stable].equals(corrupted2[stable]))
    print("--- Reporting checks ---")
    baseline_metrics = {"samples": 10, "retrieval_hit_rate": 0.90, "mean_token_f1": 0.72,
                        "judge_accuracy": 0.80, "mean_judge_score": 4.2, "ragas": {"skipped": "demo"}}
    corrupted_metrics = {"samples": 10, "retrieval_hit_rate": 0.40, "mean_token_f1": 0.33,
                        "judge_accuracy": 0.40, "mean_judge_score": 2.1}
    repaired_metrics = {"samples": 10, "retrieval_hit_rate": 0.88, "mean_token_f1": 0.70,
                        "judge_accuracy": 0.80, "mean_judge_score": 4.1}
    quality_pass = {"success": True, "evaluated_expectations": 12, "successful_expectations": 12}
    quality_fail = {"success": False, "evaluated_expectations": 12, "successful_expectations": 7}
    fresh_ok = {"latest_published": "2026-06-12", "oldest_published": "2026-01-05",
                "stale_rows": 1, "total_rows": 24, "is_fresh": True}
    fresh_bad = {"latest_published": "2025-06-12", "oldest_published": "2024-01-05",
                "stale_rows": 9, "total_rows": 21, "is_fresh": False}
    source_summary = {"source_api": "Crossref REST API",
                      "source_query": "agentic retrieval augmented generation", "record_count": 24}

    phase1_path = OUT_DIR / "phase1_report_sample.md"
    generate_phase1_report(phase1_path, source_summary, baseline_metrics, quality_pass, fresh_ok)
    check("phase1 report duoc tao", phase1_path.exists())
    p1 = phase1_path.read_text(encoding="utf-8")
    check("phase1 report co bang metrics + freshness",
          "Retrieval Hit Rate" in p1 and "Freshness" in p1 and "Crossref REST API" in p1)

    corr_path = OUT_DIR / "corruption_report_sample.md"
    generate_corruption_report(corr_path, baseline_metrics, corrupted_metrics, repaired_metrics,
                               quality_fail, quality_pass, fresh_bad, fresh_ok)
    check("corruption report duoc tao", corr_path.exists())
    cr = corr_path.read_text(encoding="utf-8")
    check("corruption report co du 3 trang thai",
          all(x in cr for x in ("Baseline", "Corrupted", "Repaired")))
    check("corruption report co phan tich Silent Failure + Self-Healing",
          "Silent Failure" in cr and "Self-Healing" in cr)

    print()
    if FAILURES:
        print(f"FAILED {len(FAILURES)} check(s): {FAILURES}")
        return 1
    print("ALL CHECKS PASSED")
    print(f"Sample outputs: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


