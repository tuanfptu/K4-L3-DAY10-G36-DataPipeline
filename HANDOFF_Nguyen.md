# HANDOFF — Phần Corruption + Reporting (Nguyên · Nhóm G36)

> **Tác giả:** Nguyên (thành viên #5 — *Corruption + Reporting*)
> **Ngày:** 2026-09-25
> **Trạng thái:** ✅ Code xong, self-check offline PASS 15/15. Chưa commit/push (chờ Nguyên duyệt).
> **Mục đích:** để cả người **và AI-agent** của các thành viên khác đọc là ráp được phần của Nguyên vào pipeline.

---

## TL;DR (30 giây)
- Đã hiện thực **3 hàm** trong 2 file stub có sẵn: `corrupt_clean_dataframe`, `generate_phase1_report`, `generate_corruption_report`.
- **KHÔNG** đổi chữ ký hàm, **KHÔNG** tạo thư mục mới (`src/corruption/`, `src/reporting/` là path SAI trong bảng phân công — path thật là `src/ingestion/` và `src/observability/`).
- Dùng đường dẫn từ `settings.paths.*`, không hardcode.
- **Không đụng file của ai khác.** Chỉ cần gọi đúng chữ ký là ráp được.
- Kiểm chứng ngay (offline, không cần API key):
  ```bash
  PYTHONUTF8=1 .venv/Scripts/python.exe tests/verify_corruption_reporting.py   # -> ALL CHECKS PASSED
  ```

---

## 1. Files đã tác động

| File | Loại | Nội dung |
| --- | --- | --- |
| `src/ingestion/corruption.py` | Hoàn thiện stub | `corrupt_clean_dataframe()` — 6 loại corruption + rebuild `text_for_embedding` + ghi `corruption_log.json` |
| `src/observability/reporting.py` | Hoàn thiện stub | `generate_phase1_report()` + `generate_corruption_report()` — sinh 2 file markdown |
| `tests/verify_corruption_reporting.py` | Mới | Self-check offline, dựng clean-df fixture từ `data/raw/` + dict mock để test 3 hàm không cần đồng đội |
| `HANDOFF_Nguyen.md` | Mới | File này |

Không sửa: `pipelines/*`, `script/*`, `crossref.py`, `cleaning.py`, `quality.py`, `evaluation/*`, `core/*`, các `__init__.py` (re-export sẵn đã trỏ đúng).

## 2. Contract — gọi 3 hàm thế nào

### 2.1 `corrupt_clean_dataframe(df, output_log_path) -> pd.DataFrame`
- **Input `df`**: clean dataframe (output của `build_clean_dataframe` của Minh). Cần các cột:
  `paper_id, title, summary, published, age_days, authors_joined, categories_joined, summary_chars, text_for_embedding`
  (giữ nguyên toàn bộ cột khác — hàm chỉ mutate, không bỏ cột).
- **Input `output_log_path`**: nơi ghi log JSON → truyền `settings.paths.corruption_log`.
- **Output**: dataframe đã bẩn (số dòng thay đổi do drop + duplicate). `text_for_embedding` và `summary_chars` được **rebuild lại toàn bộ** sau khi mutate → an toàn để đưa thẳng vào `LocalEmbeddingIndex.build(...)`.
- **Deterministic**: seed cố định `CORRUPTION_SEED = 20260925` → chạy lại ra y hệt (dễ tái lập báo cáo).

### 2.2 `generate_phase1_report(report_path, source_summary, metrics, quality, freshness) -> None`
- Ghi markdown ra `report_path` → truyền `settings.paths.baseline_report` (`data/reports/phase1_report.md`).
- **Key được đọc** (đều dùng `.get()`, thiếu key không crash):
  - `metrics`: `samples, retrieval_hit_rate, mean_token_f1, judge_accuracy, mean_judge_score` (khớp `evaluate_pipeline().summary` của Tùng).
  - `quality`: `success` (bool) — các key scalar khác tự động in thêm.
  - `freshness`: `latest_published, oldest_published, stale_rows, total_rows, is_fresh` (khớp `build_freshness_report` của Đức Anh).
  - `source_summary`: dict tùy ý (mọi key scalar được in dạng bullet) — gợi ý: `source_api, source_query, record_count`.

### 2.3 `generate_corruption_report(report_path, baseline_metrics, corrupted_metrics, repaired_metrics, corrupted_quality, repaired_quality, corrupted_freshness, repaired_freshness) -> None`
- Ghi markdown ra `report_path` → truyền `settings.paths.comparison_report` (`data/reports/corruption_report.md`).
- 3 dict metrics dùng cùng key như 2.2; 2 dict quality đọc `success`; 2 dict freshness đọc như 2.2.
- Tự tính cột chênh lệch (Delta Corrupt / Delta Repair) + đoạn phân tích Silent Failure & Self-Healing.

## 3. Chi tiết 6 loại corruption + format log

Thứ tự áp dụng và tham số mặc định (tính trên số dòng còn lại sau khi drop):

| # | type | Tác động | Mặc định |
| --- | --- | --- | --- |
| 1 | `drop_latest_records` | Bỏ các bản ghi `published` mới nhất (missing records) | ~20% dòng |
| 2 | `blank_summary` | `summary = ""` (empty abstract) | ~15% dòng |
| 3 | `inject_noise` | Chèn chuỗi ký tự rác vào `summary` | ~15% dòng |
| 4 | `truncate_title` | Cắt `title` còn 5 ký tự (< 8) | ~15% dòng |
| 5 | `stale_date` | Lùi `published` 365 ngày, `age_days += 365` | ~20% dòng |
| 6 | `duplicate_rows` | Nhân bản dòng → phá tính duy nhất `paper_id` | ~10% dòng |

Sau 6 bước: rebuild `summary_chars = len(summary)` và `text_for_embedding` (format 5 dòng `Title/Authors/Published/Categories/Summary`) cho **mọi** dòng.

**Format `corruption_log.json`** (ghi bằng `core.utils.write_json`):
```json
{
  "seed": 20260925,
  "generated_at": "<UTC ISO>",
  "input_rows": 24,
  "output_rows": 21,
  "corruptions": [
    {"step": 1, "type": "drop_latest_records", "description": "...",
     "params": {"ratio": 0.2, "dropped": 5},
     "affected_paper_ids": ["..."], "affected_count": 5}
    // ... đủ 6 entry
  ]
}
```

## 4. Hướng dẫn tích hợp theo từng thành viên

### 🔗 Tuân (Pipeline Integrator) — người gọi chính
Trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`:
```python
from ingestion.corruption import corrupt_clean_dataframe
from observability.reporting import generate_corruption_report, generate_phase1_report

# --- Phase 1 (baseline) ---
generate_phase1_report(
    settings.paths.baseline_report,
    source_summary,        # dict tùy ý (source_api, source_query, record_count)
    baseline_metrics,      # = evaluate_pipeline(...).summary  (của Tùng)
    baseline_quality,      # = run_data_quality_checks(...)     (của Đức Anh)
    baseline_freshness,    # = build_freshness_report(...)      (của Đức Anh)
)

# --- Corruption + Self-Healing flow ---
corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
# lưu corrupted_df -> rebuild index -> evaluate => corrupted_metrics
# repair từ raw snapshot -> evaluate => repaired_metrics
generate_corruption_report(
    settings.paths.comparison_report,
    baseline_metrics, corrupted_metrics, repaired_metrics,
    corrupted_quality, repaired_quality,
    corrupted_freshness, repaired_freshness,
)
```
Lưu ý: `corrupt_clean_dataframe` trả df đã rebuild `text_for_embedding` → đưa thẳng vào `LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)`.

### 🔗 Minh (Data Foundation) — nhà cung cấp `df`
Corruption cần clean df có đủ cột: `paper_id, title, summary, published, age_days, authors_joined, categories_joined, summary_chars, text_for_embedding`. Giữ đúng tên cột này là phần của Nguyên chạy được, không cần đổi gì thêm.

### 🔗 Tùng (Evaluation) — nhà cung cấp `metrics`
Report đọc đúng 5 key trong `evaluate_pipeline().summary`: `samples, retrieval_hit_rate, mean_token_f1, judge_accuracy, mean_judge_score`. Đã khớp — không cần đổi.

### 🔗 Đức Anh (Observability) — nhà cung cấp `quality` + `freshness`
Report đọc `quality["success"]` và freshness `{latest_published, oldest_published, stale_rows, total_rows, is_fresh}`. Đã khớp `build_freshness_report`. Các key scalar phụ trong `quality` sẽ được in thêm tự động.

## 5. Chạy self-check (offline, không cần API key)
```bash
cd K4-L3-DAY10-G36-DataPipeline
PYTHONUTF8=1 .venv/Scripts/python.exe tests/verify_corruption_reporting.py
```
- Kỳ vọng: in `ALL CHECKS PASSED` (15/15).
- Sinh file mẫu trong `data/_selfcheck/` (KHÔNG ghi đè artifact thật của pipeline):
  `corruption_log_sample.json`, `phase1_report_sample.md`, `corruption_report_sample.md`.
- `PYTHONUTF8=1` là bắt buộc trên Windows (console cp1252 sẽ lỗi với text tiếng Việt).

## 6. Prompt mẫu cho AI-agent của thành viên khác
> "Đọc file `HANDOFF_Nguyen.md` ở gốc repo. Phần Corruption + Reporting của Nguyên đã xong ở `src/ingestion/corruption.py` và `src/observability/reporting.py`. Dựa vào mục *Contract* (§2) và *Hướng dẫn tích hợp* (§4), hãy giúp tôi gọi 3 hàm đó tại phần việc của tôi (ví dụ `pipelines/corruption_flow.py`), truyền đúng `settings.paths.*` và đúng các key dict metrics/quality/freshness. Không được đổi chữ ký các hàm của Nguyên."

## 7. Giả định & lưu ý
- `source_summary` (tham số `generate_phase1_report`) chưa được chốt shape ở `phase1.py`; hàm chấp nhận **mọi dict** và in các key scalar → Tuân truyền gì cũng an toàn, gợi ý `source_api / source_query / record_count`.
- Corruption cố ý phá `paper_id` uniqueness (bước 6) để Quality Gate (GX) của Đức Anh bắt được — đây là hành vi mong muốn, không phải bug.
- Chưa commit/push: theo nguyên tắc nhóm, mỗi người checkout nhánh riêng (vd `feature/nguyen-corruption-reporting`) và tự nộp link repo. Nguyên tự quyết thời điểm commit.
- Báo cáo cá nhân `report/<MSSV>_<HoTen>.md` chưa đụng tới (ngoài phạm vi phần code này).



