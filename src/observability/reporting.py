from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import normalize_whitespace, now_utc, write_text

_METRIC_ROWS = (
    ("retrieval_hit_rate", "Retrieval Hit Rate"),
    ("mean_token_f1", "Mean Token F1"),
    ("judge_accuracy", "Judge Accuracy"),
    ("mean_judge_score", "Mean Judge Score"),
)


def _clean(value: Any) -> str:
    if value is None:
        return "N/A"
    return normalize_whitespace(str(value))


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    if isinstance(value, int):
        return str(value)
    return _clean(value)


def _num(source: Any, key: str):
    if not isinstance(source, dict):
        return None
    value = source.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _delta(base, other, digits: int = 4) -> str:
    if base is None or other is None:
        return "N/A"
    return f"{other - base:+.{digits}f}"


def _scalar_bullets(source: Any) -> list[str]:
    if not isinstance(source, dict) or not source:
        return ["- (khong co du lieu)"]
    lines: list[str] = []
    for key, value in source.items():
        if value is None or isinstance(value, (str, int, float, bool)):
            lines.append(f"- **{key}**: {_fmt(value)}")
    return lines or ["- (khong co truong scalar)"]

def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase (Phase 1)."""
    source_summary = source_summary or {}
    metrics = metrics or {}
    quality = quality or {}
    freshness = freshness or {}

    lines: list[str] = [
        "# Phase 1 - Baseline Pipeline Report",
        "",
        f"_Generated (UTC): {now_utc().isoformat()}_",
        "",
        "## 1. Nguon du lieu",
        *_scalar_bullets(source_summary),
        "",
        "## 2. Retrieval & Evaluation Metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Samples | {_fmt(metrics.get('samples'))} |",
    ]
    for key, label in _METRIC_ROWS:
        lines.append(f"| {label} | {_fmt(metrics.get(key))} |")

    lines += [
        "",
        "## 3. Data Quality Gate",
        f"- **Ket qua tong the**: {'PASS' if quality.get('success') else 'FAIL'}",
        *_scalar_bullets({k: v for k, v in quality.items() if k != "success"}),
        "",
        "## 4. Freshness (SLA <= 180 ngay)",
        f"- **Latest published**: {_clean(freshness.get('latest_published'))}",
        f"- **Oldest published**: {_clean(freshness.get('oldest_published'))}",
        f"- **Stale rows**: {_fmt(freshness.get('stale_rows'))} / {_fmt(freshness.get('total_rows'))}",
        f"- **Du lieu con tuoi (is_fresh)**: {_fmt(freshness.get('is_fresh'))}",
        "",
    ]
    write_text(Path(report_path), "\n".join(lines))


def _analysis_lines(baseline: dict, corrupted: dict, repaired: dict) -> list[str]:
    drops, recoveries = [], []
    for key, _label in _METRIC_ROWS:
        b, c, r = _num(baseline, key), _num(corrupted, key), _num(repaired, key)
        if b is not None and c is not None:
            drops.append(c - b)
        if c is not None and r is not None:
            recoveries.append(r - c)
    out: list[str] = []
    if drops:
        avg = sum(drops) / len(drops)
        out.append(
            f"- **Silent Failure**: sau khi tiem loi, cac metric trung binh thay doi {avg:+.4f} "
            "so voi baseline -> du lieu ban lam giam chat luong RAG ma khong nem loi runtime."
        )
    else:
        out.append("- **Silent Failure**: chua du du lieu metric de danh gia.")
    if recoveries:
        avg = sum(recoveries) / len(recoveries)
        out.append(
            f"- **Self-Healing**: sau khi phuc hoi tu raw snapshot, metric trung binh thay doi {avg:+.4f} "
            "so voi trang thai corrupted -> minh chung co che tu phuc hoi hoat dong."
        )
    else:
        out.append("- **Self-Healing**: chua du du lieu metric de danh gia.")
    return out


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Viet markdown report so sanh baseline / corrupted / repaired."""
    baseline_metrics = baseline_metrics or {}
    corrupted_metrics = corrupted_metrics or {}
    repaired_metrics = repaired_metrics or {}
    corrupted_quality = corrupted_quality or {}
    repaired_quality = repaired_quality or {}
    corrupted_freshness = corrupted_freshness or {}
    repaired_freshness = repaired_freshness or {}

    lines: list[str] = [
        "# Corruption vs Repair - Comparison Report",
        "",
        f"_Generated (UTC): {now_utc().isoformat()}_",
        "",
        "So sanh 3 trang thai: **Baseline** (sach) -> **Corrupted** (tiem loi) -> **Repaired** (phuc hoi).",
        "",
        "## 1. Retrieval & Evaluation Metrics",
        "",
        "| Metric | Baseline | Corrupted | Repaired | Delta Corrupt | Delta Repair |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| Samples | {_fmt(baseline_metrics.get('samples'))} | {_fmt(corrupted_metrics.get('samples'))}"
        f" | {_fmt(repaired_metrics.get('samples'))} | - | - |",
    ]
    for key, label in _METRIC_ROWS:
        b, c, r = _num(baseline_metrics, key), _num(corrupted_metrics, key), _num(repaired_metrics, key)
        lines.append(
            f"| {label} | {_fmt(b)} | {_fmt(c)} | {_fmt(r)} | {_delta(b, c)} | {_delta(c, r)} |"
        )
    lines += [
        "",
        "## 2. Data Quality Gate",
        "",
        "| State | Gate |",
        "| --- | --- |",
        f"| Corrupted | {'PASS' if corrupted_quality.get('success') else 'FAIL'} |",
        f"| Repaired | {'PASS' if repaired_quality.get('success') else 'FAIL'} |",
        "",
        "## 3. Freshness",
        "",
        "| State | is_fresh | Stale rows | Latest published | Oldest published |",
        "| --- | --- | --- | --- | --- |",
        f"| Corrupted | {_fmt(corrupted_freshness.get('is_fresh'))} |"
        f" {_fmt(corrupted_freshness.get('stale_rows'))} / {_fmt(corrupted_freshness.get('total_rows'))} |"
        f" {_clean(corrupted_freshness.get('latest_published'))} |"
        f" {_clean(corrupted_freshness.get('oldest_published'))} |",
        f"| Repaired | {_fmt(repaired_freshness.get('is_fresh'))} |"
        f" {_fmt(repaired_freshness.get('stale_rows'))} / {_fmt(repaired_freshness.get('total_rows'))} |"
        f" {_clean(repaired_freshness.get('latest_published'))} |"
        f" {_clean(repaired_freshness.get('oldest_published'))} |",
        "",
        "## 4. Phan tich",
        "",
        *_analysis_lines(baseline_metrics, corrupted_metrics, repaired_metrics),
        "",
    ]
    write_text(Path(report_path), "\n".join(lines))



