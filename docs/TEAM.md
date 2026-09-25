# Phân công nhóm G36 — Day 10 Data Pipeline

- **Repository:** https://github.com/tuanfptu/K4-L3-DAY10-G36-DataPipeline
- **Báo cáo nhóm:** [report/group_report.md](../report/group_report.md)
- **Demo HTML:** [giao diện](../demo/index.html) · [kiến trúc hệ thống](../demo/architecture.html)

| Thành viên | MSSV | Vai trò | File phụ trách chính | Báo cáo cá nhân |
|---|---|---|---|---|
| Hà Mạnh Tuân | 2A202602982 | Trưởng nhóm, tích hợp pipeline và tự phục hồi | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/*`, `demo/*` | [Báo cáo Tuân](../report/2A202602982_HaManhTuan.md) |
| Ninh Quang Minh | 2A202602432 | Nền tảng dữ liệu | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `data/raw/*` | [Báo cáo Minh](../report/2A202602432_NinhQuangMinh.md) |
| Đỗ Thanh Tùng | 2A202602845 | RAG và đánh giá | `src/evaluation/testset.py`, `src/evaluation/metrics.py`, `src/retrieval/qa.py`; kiểm tra `src/retrieval/index.py` | [Báo cáo Tùng](../report/2A202602845_DoThanhTung.md) |
| Phạm Đức Anh | 2A202602994 | Data Observability và dashboard | `src/observability/quality.py`, `dashboard/app.py` | [Báo cáo Đức Anh](../report/2A202602994_PhamDucAnh.md) |
| Trần Võ Hoàng Nguyên | 2A202602551 | Tiêm lỗi và báo cáo | `src/ingestion/corruption.py`, `src/observability/reporting.py` | [Báo cáo Nguyên](<../report/2A202602551_Hoang Nguyen.md>) |

## Luồng tích hợp và bàn giao

1. Minh cung cấp snapshot Crossref ADAS, schema bản ghi và 24 bản ghi đã làm sạch.
2. Tùng cung cấp bộ 10 câu hỏi dùng chung cho cả ba trạng thái cùng hàm lập chỉ mục, truy vấn và đo metrics.
3. Đức Anh cung cấp Quality Gate Great Expectations 1.x, Freshness SLA và dashboard; Nguyên cung cấp sáu dạng corruption và hàm tạo báo cáo.
4. Tuân điều phối baseline → corruption → repair từ raw, chạy đối chiếu và dựng demo HTML theo template.

## Bằng chứng chạy tích hợp

Hai entrypoint là `python script/run_phase1.py` và `python script/run_corruption_flow.py`. Cấu hình offline đã dùng: `HF_HUB_OFFLINE=1`, `LLM_PROVIDER=mock`, `JUDGE_MODE=heuristic`. Với 24 bài báo ADAS và cùng 10 câu hỏi, retrieval hit rate đạt **1.000 → 0.800 → 1.000**; Quality Gate và freshness lần lượt **PASS → FAIL → PASS**. Dữ liệu lỗi có 21 bản ghi; phục hồi từ raw trở lại 24 bản ghi.

Đối chiếu [metrics](../data/results/baseline_metrics.json), [log tiêm lỗi](../data/results/corruption_log.json), [báo cáo chất lượng baseline](../data/quality/baseline_quality_report.json), [báo cáo chất lượng corrupted](../data/quality/corrupted_quality_report.json) và [báo cáo so sánh](../data/reports/corruption_report.md). [Manifest embedding](../data/embeddings/papers_embeddings.json) ghi nhận MiniLM đã có trong cache offline; phần judge dùng heuristic và Ragas được bỏ qua. Các báo cáo cá nhân của thành viên có thể mô tả lượt thử riêng ở giai đoạn trước khi tích hợp, nên số liệu chung chính thức nằm trong các artifact tích hợp ở trên.
