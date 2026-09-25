# Corruption vs Repair - Comparison Report

_Generated (UTC): 2026-09-25T10:12:00.726386+00:00_

So sanh 3 trang thai: **Baseline** (sach) -> **Corrupted** (tiem loi) -> **Repaired** (phuc hoi).

## 1. Retrieval & Evaluation Metrics

| Metric | Baseline | Corrupted | Repaired | Delta Corrupt | Delta Repair |
| --- | --- | --- | --- | --- | --- |
| Samples | 10 | 10 | 10 | - | - |
| Retrieval Hit Rate | 1.0000 | 0.8000 | 1.0000 | -0.2000 | +0.2000 |
| Mean Token F1 | 1.0000 | 0.7267 | 1.0000 | -0.2733 | +0.2733 |
| Judge Accuracy | 1.0000 | 0.7000 | 1.0000 | -0.3000 | +0.3000 |
| Mean Judge Score | 5.0000 | 3.8000 | 5.0000 | -1.2000 | +1.2000 |

## 2. Data Quality Gate

| State | Gate |
| --- | --- |
| Corrupted | FAIL |
| Repaired | PASS |

## 3. Freshness

| State | is_fresh | Stale rows | Latest published | Oldest published |
| --- | --- | --- | --- | --- |
| Corrupted | false | 7 / 21 | 2026-08-10 | 2025-04-04 |
| Repaired | true | 0 / 24 | 2026-09-24 | 2026-04-04 |

## 4. Phan tich

- **Silent Failure**: sau khi tiem loi, cac metric trung binh thay doi -0.4933 so voi baseline -> du lieu ban lam giam chat luong RAG ma khong nem loi runtime.
- **Self-Healing**: sau khi phuc hoi tu raw snapshot, metric trung binh thay doi +0.4933 so voi trang thai corrupted -> minh chung co che tu phuc hoi hoat dong.
