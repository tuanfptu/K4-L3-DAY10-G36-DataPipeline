"""Embed pipeline artifacts into the standalone HTML demo."""
from __future__ import annotations
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]

def read(name):
    path = root / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None

path = root / 'demo' / 'index.html'
html = path.read_text(encoding='utf-8')
start = html.index('const DATA=') + len('const DATA=')
end = html.index('\nconst fmt', start)
quality = [read(f'data/quality/{name}_quality_report.json') for name in ('baseline', 'corrupted', 'repaired')]
embedding = read('data/embeddings/papers_embeddings.json') or {}
metrics = [read(f'data/results/{name}_metrics.json') for name in ('baseline', 'corrupted', 'repaired')]
corruption_log = read('data/results/corruption_log.json') or {}
scenarios = [
    {'type': item['type'], 'paper_ids': item.get('affected_paper_ids', [])}
    for item in corruption_log.get('corruptions', [])
]
engine = ('Great Expectations 1.x' if 'gx_success' in (quality[0] or {})
          else (quality[0] or {}).get('engine', 'chưa rõ'))
judge = ('heuristic' if (metrics[0] or {}).get('judge_fallback_count') == (metrics[0] or {}).get('samples')
         else 'xem judge_llm_count trong metrics')
payload = {
    'documents': len(read('data/clean/papers_clean.json') or []),
    'baseline': metrics[0], 'corrupted': metrics[1], 'repaired': metrics[2],
    'quality': quality,
    'freshness': [read(f'data/quality/{name}') for name in ('freshness_report.json', 'corrupted_freshness_report.json', 'repaired_freshness_report.json')],
    'scenarios': scenarios,
    'note': f"Quality: {engine}. Embedding: {embedding.get('embedding_model', 'chưa rõ')}. Judge: {judge}. Ragas: xem metrics.",
}
html = html[:start] + json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c') + ';' + html[end:]
path.write_text(html, encoding='utf-8')
architecture_path = root / 'demo' / 'architecture.html'
architecture = architecture_path.read_text(encoding='utf-8')
for state, metric in zip(('baseline', 'corrupted', 'repaired'), metrics):
    if metric:
        pattern = rf'(<article class="lane {state}">.*?<div class="result">)Hit rate: [^<]*(</div>)'
        architecture = re.sub(pattern, lambda match: match[1] + f"Hit rate: {metric['retrieval_hit_rate']:.3f}" + match[2], architecture, count=1, flags=re.S)
architecture_path.write_text(architecture, encoding='utf-8')
print('Updated demo/index.html')
