from __future__ import annotations
from core.config import load_settings
from core.utils import now_utc, write_csv, write_json, read_json
from ingestion.crossref import fetch_source_records
from ingestion.cleaning import build_clean_dataframe
from evaluation.testset import build_test_set
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report

def main() -> None:
    settings = load_settings(); paths = settings.paths
    raw = fetch_source_records(settings)
    clean = build_clean_dataframe(raw, now_utc())
    write_csv(clean, paths.clean_csv); write_json(paths.clean_json, clean.to_dict(orient='records'))
    quality = run_data_quality_checks(clean, settings, 'baseline')
    freshness = build_freshness_report(clean, settings, paths.freshness_report)
    if not quality['success']: raise RuntimeError('Baseline quality gate failed')
    if not paths.eval_testset.exists() or settings.refresh_test_set: build_test_set(clean, paths.eval_testset)
    index = LocalEmbeddingIndex.build(clean, settings, paths.embeddings_json)
    metrics = evaluate_pipeline(settings, index, paths.eval_testset, paths.baseline_metrics, paths.baseline_answers).summary
    generate_phase1_report(paths.baseline_report, {'source': settings.source_api, 'raw_records': len(raw), 'clean_records': len(clean)}, metrics, quality, freshness)
    print(f"Baseline: {len(clean)} documents; hit rate {metrics['retrieval_hit_rate']:.3f}; quality {quality['success']}")

if __name__ == '__main__': main()
