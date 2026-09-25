# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Họ và tên | Trần Võ Hoàng Nguyên |
| MSSV | 2A202602551 |
| Khóa/Lớp | K4 |
| Tên nhóm | G36 (`K4-L3-DAY10-G36-DataPipeline`) |
| Vai trò chính | Corruption + Reporting (thành viên #5) |
| Repository | [điền link repo nhóm khi push] |
| Ngày hoàn thành | 2026-09-25 (phần code Corruption + Reporting) |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------- |
| Data corruption (6 dạng) | `src/ingestion/corruption.py` :: `corrupt_clean_dataframe` | clean dataframe (16 cột) + đường dẫn log | corrupted dataframe + `data/results/corruption_log.json` | Hoàn thành |
| Reporting (baseline + comparison) | `src/observability/reporting.py` :: `generate_phase1_report`, `generate_corruption_report` | dict `metrics` / `quality` / `freshness` + đường dẫn | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Hoàn thành ở mức hàm; output số liệu thật chờ pipeline chạy |

Tôi chỉ nhận ownership cho hai file trên. Quan hệ phụ thuộc: corruption nhận clean df từ Minh (`cleaning.py`) và trả df đã bẩn để Tuân re-index/evaluate; reporting tiêu thụ metrics của Tùng (`metrics.py`), quality/freshness của Đức Anh (`quality.py`), và được Tuân gọi trong `pipelines/*`.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Viết self-check offline | Cả nhóm (kiểm chứng contract sớm) | `tests/verify_corruption_reporting.py` — PASS 15/15, không cần API key |
| Viết tài liệu bàn giao | Tuân / Minh / Tùng / Đức Anh (tích hợp) | `HANDOFF_Nguyen.md` — contract input/output + snippet gọi hàm cho từng người |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File / hàm / artifact | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| 6 dạng corruption (drop latest, blank summary, inject noise, truncate title, stale date, duplicate rows) | `corruption.py::corrupt_clean_dataframe` | corrupted df + `corruption_log.json` (6 entry) | `tests/verify_corruption_reporting.py` |
| Rebuild `text_for_embedding` + `summary_chars` sau khi mutate | `corruption.py` | df sẵn sàng đưa thẳng vào index | self-check kiểm cột bắt đầu bằng `Title:` |
| Báo cáo Phase 1 (baseline) | `reporting.py::generate_phase1_report` | `phase1_report.md` | self-check sinh file mẫu |
| Báo cáo so sánh 3 trạng thái | `reporting.py::generate_corruption_report` | `corruption_report.md` (bảng + phân tích) | self-check sinh file mẫu |

Bằng chứng cụ thể: self-check offline chạy ngày 2026-09-25 in `ALL CHECKS PASSED` (15/15). Các file mẫu nằm ở `data/_selfcheck/` (đặt riêng, KHÔNG ghi đè artifact thật của pipeline).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Mô phỏng "silent data corruption" — dữ liệu hỏng âm thầm làm giảm chất lượng RAG mà không ném lỗi runtime — rồi sinh báo cáo đối sánh 3 trạng thái để chứng minh khả năng observability & self-healing của pipeline.

### Cách triển khai
- **Corruption**: làm trên bản copy sâu của df, dùng seed cố định `CORRUPTION_SEED = 20260925`. Áp tuần tự 6 dạng lỗi, mỗi dạng ghi 1 entry log (`type, description, params, affected_paper_ids, affected_count`). Cuối cùng rebuild `summary_chars` và `text_for_embedding` (format 5 dòng Title/Authors/Published/Categories/Summary) cho mọi dòng.
- **Reporting**: 2 hàm dựng markdown bằng `core.utils.write_text`, mọi truy cập dict dùng `.get()` phòng thủ (không crash khi thiếu key). Báo cáo so sánh tự tính cột Delta (Corrupt/Repair) + đoạn phân tích Silent Failure / Self-Healing.
- Đường dẫn lấy từ `settings.paths.*`, không hardcode.

### Input, output và contract
| Hàm | Input | Output |
| --- | --- | --- |
| `corrupt_clean_dataframe(df, output_log_path)` | clean df (đủ cột `paper_id, title, summary, published, age_days, …, text_for_embedding`) + path log | corrupted df + `data/results/corruption_log.json` |
| `generate_phase1_report(report_path, source_summary, metrics, quality, freshness)` | 4 dict + path | `data/reports/phase1_report.md` |
| `generate_corruption_report(report_path, baseline_metrics, corrupted_metrics, repaired_metrics, corrupted_quality, repaired_quality, corrupted_freshness, repaired_freshness)` | 7 dict + path | `data/reports/corruption_report.md` |

### Cách xác minh
```bash
PYTHONUTF8=1 .venv/Scripts/python.exe tests/verify_corruption_reporting.py
```
- Kết quả mong đợi: in `ALL CHECKS PASSED`.
- Kết quả thực tế (2026-09-25): `ALL CHECKS PASSED` (15/15).
- Artifact đối chiếu: `data/_selfcheck/corruption_log_sample.json`, `phase1_report_sample.md`, `corruption_report_sample.md` — **là dữ liệu mock để kiểm thử logic render, KHÔNG phải số liệu pipeline thật.**

## 5. Quyết định kỹ thuật quan trọng

- **Bối cảnh & ràng buộc**: báo cáo so sánh chỉ có ý nghĩa nếu bước corruption tái lập được — cùng input phải cho cùng kết quả để 3 trạng thái baseline/corrupted/repaired đối chiếu nhất quán và debug được.
- **Các phương án cân nhắc**: (a) corruption ngẫu nhiên không seed — đơn giản nhưng mỗi lần chạy ra tập dòng khác nhau, không tái lập; (b) corruption có seed cố định.
- **Lựa chọn & lý do**: chọn (b) — hằng số `CORRUPTION_SEED = 20260925`. Chạy lại luôn ra cùng tập dòng bị ảnh hưởng → báo cáo tái lập, dễ chấm và dễ đối chiếu giữa các lần chạy.
- **Bằng chứng**: self-check có case kiểm tra tính deterministic → PASS.

Quyết định phụ: ghi file mẫu của self-check vào `data/_selfcheck/` thay vì `data/reports/` thật, để số liệu mock không bị nhầm là artifact pipeline thực.

## 6. Lỗi/blocker đã xử lý

- **Triệu chứng**: khi in log tiếng Việt trên Windows, script dừng với `UnicodeEncodeError` (codec `charmap`/cp1252).
- **Nguyên nhân gốc**: console mặc định của Windows dùng codepage cp1252, không mã hóa được ký tự tiếng Việt.
- **Cách xử lý**: đặt biến môi trường `PYTHONUTF8=1` khi chạy và gọi `sys.stdout.reconfigure(encoding="utf-8")` trong script self-check.
- **Xác minh**: self-check chạy sạch, không còn lỗi encoding.

Blocker phát hiện thêm (đã né, chưa gây lỗi): bảng phân công `PhanCongNhiemVu.md` ghi SAI path `src/corruption/` và `src/reporting/`; path thật là `src/ingestion/corruption.py` và `src/observability/reporting.py` (khớp `__init__.py` re-export). Đã viết đúng vào stub có sẵn, không tạo thư mục sai.

## 7. Hiểu biết luồng end-to-end

- **Dữ liệu vào từ đâu, ra ở đâu?** Nguồn: Crossref REST API → `crossref.py` (Minh) lấy raw về `data/raw/`; `cleaning.py` chuẩn hóa thành clean df; index/embedding (Tuân) → ChromaDB; evaluation (Tùng) sinh metrics; quality/freshness (Đức Anh) kiểm dữ liệu; corruption + reporting (tôi) sinh dữ liệu bẩn + báo cáo. Output cuối: 2 file markdown trong `data/reports/` + `corruption_log.json`.
- **Phần của tôi nhận gì / trả gì?** Nhận clean df (từ cleaning) + các dict metrics/quality/freshness (từ evaluation & observability); trả corrupted df + log corruption + 2 báo cáo markdown.
- **Nếu phần của tôi sai thì ảnh hưởng ai?** Corruption sai → index/evaluation trên dữ liệu bẩn sai theo → báo cáo so sánh mất ý nghĩa; report sai → cả nhóm mất bằng chứng observability để nộp.
- **Quality Gate liên quan thế nào?** Corruption cố ý phá tính duy nhất `paper_id` (bước duplicate) + tạo summary trống/lỗi thời → GX quality gate của Đức Anh phải FAIL ở trạng thái corrupted và PASS lại sau repair. Đây là hành vi mong muốn.
- **Vì sao cần đo baseline → corrupted → repaired?** Để định lượng "silent failure" (metric tụt khi dữ liệu bẩn mà không có lỗi runtime) và chứng minh cơ chế self-healing hồi phục metric sau khi repair từ raw snapshot.

## 8. Phân tích kết quả

> **Trạng thái: CHỜ PIPELINE CHẠY THẬT.** Bảng số liệu 3 trạng thái dưới đây chưa điền được vì cần chạy full pipeline (index của Tuân + evaluation của Tùng + quality/freshness của Đức Anh + API key cho LLM judge). Phần code của tôi (corruption + reporting) đã sẵn sàng tiêu thụ số liệu này.

| Metric | Baseline | Corrupted | Repaired | Delta Corrupt | Delta Repair |
| --- | --- | --- | --- | --- | --- |
| Retrieval Hit Rate | — | — | — | — | — |
| Mean Token F1 | — | — | — | — | — |
| Judge Accuracy | — | — | — | — | — |
| Mean Judge Score | — | — | — | — | — |

| Trạng thái | Quality Gate | is_fresh | Stale rows |
| --- | --- | --- | --- |
| Corrupted | — (kỳ vọng FAIL) | — | — |
| Repaired | — (kỳ vọng PASS) | — | — |

**Lưu ý trung thực**: self-check của tôi có sinh báo cáo mẫu với số liệu *mock* (vd baseline hit rate 0.90 → corrupted 0.40 → repaired 0.88) **chỉ để kiểm thử logic render bảng và đoạn phân tích**, KHÔNG phải kết quả đo thật. Kết luận về Silent Failure / Self-Healing sẽ chỉ điền sau khi có số liệu pipeline thật.

## 9. Điều học được

- **Data observability**: đo baseline → corrupted → repaired là cách định lượng "silent failure" mà không cần lỗi runtime; báo cáo đối sánh là bằng chứng khách quan cho chất lượng dữ liệu.
- **Reproducibility**: seed cố định giúp corruption tái lập, báo cáo nhất quán giữa các lần chạy.
- **Contract-first / làm độc lập**: bám tên cột df và tên key dict như một hợp đồng giúp tôi viết + test xong phần mình mà không phải chờ module của đồng đội.
- **Điều làm khác nếu làm lại**: chốt shape của `source_summary` với Tuân sớm hơn thay vì để hàm chấp nhận "mọi dict"; và tách sẵn fixture clean-df dùng chung để self-check gần dữ liệu thật hơn.

## 10. Tự đánh giá & cam kết

- [x] Báo cáo phản ánh đúng phần việc tôi trực tiếp làm (`corruption.py` + `reporting.py` + self-check + handoff).
- [x] Tôi giải thích được luồng dữ liệu end-to-end và vị trí phần mình trong đó.
- [x] Tôi KHÔNG ghi "đã chạy thành công" cho phần chưa kiểm chứng — số liệu 3 trạng thái (§8) được đánh dấu rõ là *chờ pipeline chạy thật*.
- [x] Mọi kết luận đều có artifact để đối chiếu; phần chưa có số liệu được để trống trung thực, không bịa.

Người viết: **Trần Võ Hoàng Nguyên** — MSSV **2A202602551** — Ngày **2026-09-25**.
