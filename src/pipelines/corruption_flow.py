from __future__ import annotations
import pandas as pd
from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_corruption_report

def main() -> None:
    settings = load_settings(); paths = settings.paths
    if not paths.baseline_metrics.exists():
        from pipelines.phase1 import main as baseline_main
        baseline_main()
    baseline = read_json(paths.baseline_metrics)
    clean = pd.read_json(paths.clean_json)
    corrupted = corrupt_clean_dataframe(clean, paths.corruption_log)
    write_csv(corrupted, paths.corrupted_clean_csv); write_json(paths.corrupted_clean_json, corrupted.to_dict(orient='records'))
    bad_quality = run_data_quality_checks(corrupted, settings, 'corrupted')
    bad_freshness = build_freshness_report(corrupted, settings, paths.quality_dir / 'corrupted_freshness_report.json')
    bad_index = LocalEmbeddingIndex.build(corrupted, settings, paths.corrupted_embeddings_json)
    bad_metrics = evaluate_pipeline(settings, bad_index, paths.eval_testset, paths.corrupted_metrics, paths.corrupted_answers).summary
    repaired = build_clean_dataframe(load_raw_records(paths.raw_records_json), now_utc())
    write_csv(repaired, paths.repaired_clean_csv); write_json(paths.repaired_clean_json, repaired.to_dict(orient='records'))
    repaired_quality = run_data_quality_checks(repaired, settings, 'repaired')
    repaired_freshness = build_freshness_report(repaired, settings, paths.quality_dir / 'repaired_freshness_report.json')
    if not repaired_quality['success']: raise RuntimeError('Repair quality gate failed')
    repaired_index = LocalEmbeddingIndex.build(repaired, settings, paths.repaired_embeddings_json)
    repaired_metrics = evaluate_pipeline(settings, repaired_index, paths.eval_testset, paths.repaired_metrics, paths.repaired_answers).summary
    generate_corruption_report(paths.comparison_report, baseline, bad_metrics, repaired_metrics, bad_quality, repaired_quality, bad_freshness, repaired_freshness)
    print(f"Baseline / corrupted / repaired hit rate: {baseline['retrieval_hit_rate']:.3f} / {bad_metrics['retrieval_hit_rate']:.3f} / {repaired_metrics['retrieval_hit_rate']:.3f}")

if __name__ == '__main__': main()
