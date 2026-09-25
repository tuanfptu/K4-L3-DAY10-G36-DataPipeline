# Phân công nhóm — Day 10 Data Pipeline

- **Nhóm:** G36
- **Repository:** https://github.com/tuanfptu/K4-L3-DAY10-G36-DataPipeline
- **Thông tin còn cần nhóm điền:** họ tên đầy đủ, MSSV, email và link báo cáo cá nhân. Bảng dưới đây ghi phân công, không xác nhận phần việc đã hoàn thành.

| Người | Vai trò | File phụ trách chính | Đầu ra cần bàn giao |
|---|---|---|---|
| Tuân | Pipeline Integrator + Self-Healing | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/*` | Chạy end-to-end hai lệnh, tự phục hồi từ raw |
| Minh | Data Foundation | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `data/raw/*`, `data/clean/*` | 24 raw records → 24 clean records chuẩn |
| Tùng | RAG + Evaluation | `src/evaluation/testset.py`, `src/retrieval/index.py` (kiểm tra), `src/retrieval/qa.py`, `src/evaluation/metrics.py` | 10 QA và metrics baseline/corrupted/repaired |
| Đức Anh | Data Observability + Dashboard | `src/observability/quality.py`, `dashboard/app.py` | GX, freshness, dashboard |
| Nguyên | Corruption + Reporting | `src/ingestion/corruption.py`, `src/observability/reporting.py` | 6 dạng corruption và comparison report |

## Điểm giao tiếp giữa các phần việc

1. Minh bàn giao schema `PaperRecord`, clean DataFrame và đường dẫn raw/clean cho Tuân, Tùng, Đức Anh, Nguyên.
2. Tùng chốt cấu trúc test set và cùng một bộ 10 câu hỏi cho cả ba trạng thái đánh giá.
3. Đức Anh kiểm tra quality/freshness trước khi Tuân nạp index; Nguyên tạo bản corrupted và báo cáo đối chiếu.
4. Tuân ghép hai luồng, chạy lại từ raw, đối chiếu artifacts với metrics và chuẩn bị demo.

Mỗi người tự điền phần đóng góp **đã thực hiện thật** và báo cáo cá nhân theo `report/individual_report.md`, rồi tự kiểm tra commit trên nhánh mặc định và nộp link repo qua LMS.

# Cá nhân

Thông tin bên dưới chờ từng thành viên tự điền sau khi làm phần việc của mình.

| Người | Họ tên đầy đủ | MSSV | Email | Báo cáo cá nhân |
|---|---|---|---|---|
| Tuân |  |  |  |  |
| Minh | Ninh Quang Minh | 2A202602432 | minhnq.chc@gmail.com | `report/2A202602432_NinhQuangMinh.md` |
| Tùng | Đỗ Thanh Tùng | 2A202602845 | thanhtung.30082020@gmail.com | `report/2A202602845_DoThanhTung.md` |
| Đức Anh |  |  |  |  |
| Nguyên |  |  |  |  |

## Tuân-[MSSV]

- Công việc đã hoàn thành và bằng chứng: _chưa tự khai_.

## NinhQuangMinh-2A202602432

- Vai trò: Data Foundation — `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, raw và clean artifacts.
- Kết quả kỹ thuật đã kiểm: 24 DOI ADAS → 24 `PaperRecord` → 24 dòng clean, DOI duy nhất; lệnh kiểm Bước 2 in `Đã tải 24 bài báo`.
- Bằng chứng và giới hạn: `data/raw/adas_selected_dois.json`, `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`; chi tiết trong `report/2A202602432_NinhQuangMinh.md`. Minh cần tự xác nhận phần giải thích, kết quả tích hợp và commit trước khi nộp.

## DoThanhTung-2A202602845

- Vai trò: RAG + Evaluation — `src/evaluation/testset.py`, `src/evaluation/metrics.py`, kiểm tra `src/retrieval/index.py` và `src/retrieval/qa.py`.
- Đã hoàn thành: `build_test_set` sinh 10 câu hỏi cố định (3 summary, 3 authors, 2 date, 2 categories) vào `data/eval/test_set.json`, chạy lại cho cùng md5; thêm `load_or_build_test_set` để ba trạng thái dùng chung một bộ đề; sửa judge trong `metrics.py` để không âm thầm rơi về heuristic khi hết quota (ghi `judge_llm_count` / `judge_fallback_count`, hỗ trợ `JUDGE_MODE=heuristic`); `index.py` ép metadata về chuỗi để Chroma nhận được dữ liệu corrupted có `None`/`NaN`; 7 test pytest trong `tests/test_evaluation.py`.
- Bằng chứng: lệnh Bước 5 in `Sinh được 10 câu hỏi test`; `pytest tests/test_evaluation.py` → `7 passed`; lượt chấm thử baseline bằng module (ngoài pipeline chính thức) cho hit rate 1.0, token F1 1.0, judge accuracy 1.0 với 10/10 câu chấm bởi `gemini-3.5-flash-lite`. Chi tiết trong `report/2A202602845_DoThanhTung.md`.
- Chưa xong: metrics corrupted/repaired chính thức chờ `corruption.py` (Nguyên) và `corruption_flow.py` / `phase1.py` (Tuân).

## Đức Anh-[MSSV]

- Công việc đã hoàn thành và bằng chứng: _chưa tự khai_.

## Nguyên-[MSSV]

- Công việc đã hoàn thành và bằng chứng: _chưa tự khai_.
