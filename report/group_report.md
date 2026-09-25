# Báo cáo nhóm G36 — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Mục | Nội dung |
| --- | --- |
| Khóa/Lớp | K4-L3-DAY10 |
| Nhóm | G36 |
| Repository | https://github.com/tuanfptu/K4-L3-DAY10-G36-DataPipeline |
| Ngày hoàn thành và chạy tích hợp | 2026-09-25 |
| Chủ đề dữ liệu | 24 bài báo Crossref liên quan kiểm thử ADAS và sinh kịch bản lái xe tự động |

### Thành viên và phân công

| Thành viên | MSSV | Vai trò | Mã nguồn và sản phẩm chính |
| --- | --- | --- | --- |
| Hà Mạnh Tuân | 2A202602982 | Trưởng nhóm, tích hợp pipeline và self-healing | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/run_*.py`, demo HTML, báo cáo tích hợp |
| Ninh Quang Minh | 2A202602432 | Data Foundation | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, 24 DOI, raw và clean |
| Đỗ Thanh Tùng | 2A202602845 | RAG và Evaluation | `src/evaluation/testset.py`, `src/evaluation/metrics.py`, `src/retrieval/index.py`, `src/retrieval/qa.py` |
| Phạm Đức Anh | 2A202602994 | Data Observability và Dashboard | `src/observability/quality.py`, `dashboard/app.py`, quality/freshness reports |
| Trần Võ Hoàng Nguyên | 2A202602551 | Corruption và Reporting | `src/ingestion/corruption.py`, `src/observability/reporting.py`, corruption log và báo cáo so sánh |

## 2. Tóm tắt kết quả

Nhóm đã tích hợp luồng dữ liệu end-to-end từ bộ 24 DOI ADAS được tuyển chọn, dùng bản chụp phản hồi Crossref để chạy lặp lại, chuẩn hóa thành 24 bản ghi sạch, xây ba collection ChromaDB và đánh giá trên cùng bộ 10 câu hỏi. Quality Gate chạy bằng Great Expectations 1.x. Ở trạng thái baseline, 6/6 expectation đạt, không có bản ghi quá 180 ngày, retrieval hit rate và token F1 đều bằng 1.000. Sáu lỗi được tiêm cùng một lần chạy: xóa bản ghi mới, làm trống summary, chèn noise, cắt title, làm cũ ngày xuất bản và nhân bản dòng. Dữ liệu corrupted còn 21 dòng; hai expectation bị lỗi, 7/21 dòng stale, retrieval hit rate giảm còn 0.800 và token F1 còn 0.7267. Pipeline repair đọc lại raw records, làm sạch và index lại; 24 dòng, quality/freshness và các metric trở về baseline. Demo trình bày số liệu bằng HTML/CSS/JavaScript độc lập, gồm trang kiến trúc lớn, không dùng Streamlit cho phần trình diễn được yêu cầu. Lần chạy này dùng MiniLM có sẵn trong cache và heuristic judge; Ragas chưa chạy. Bộ câu hỏi có tra cứu title chính xác nên đây là phép kiểm tích hợp có giới hạn, chưa đại diện cho truy vấn mở.

## 3. Kiến trúc và luồng dữ liệu

```text
24 DOI ADAS -> Crossref snapshot/API -> raw records
  -> cleaning + 16 cột chuẩn -> quality/freshness gate
  -> MiniLM embeddings -> ChromaDB collection baseline
  -> 10 QA cố định -> baseline metrics/report
  -> tiêm đồng thời 6 lỗi -> quality/freshness + collection corrupted -> metrics
  -> đọc lại raw records -> cleaning + collection repaired -> metrics
  -> comparison report + demo HTML độc lập
```

| Khối | Input | Xử lý | Output | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | 24 DOI trong `adas_selected_dois.json` | Parse response Crossref; retry/backoff khi refresh; bảo toàn snapshot hợp lệ | `data/raw/crossref_response.json`, `crossref_records.json` | Minh |
| Cleaning | 24 `PaperRecord` | Chuẩn hóa text, ngày, tác giả, category; loại bản ghi thiếu trường; khử trùng DOI | `data/clean/papers_clean.csv/json` | Minh |
| Index/RAG | Clean DataFrame | MiniLM 384 chiều, Chroma cosine; tra cứu title chính xác nếu câu hỏi chứa title | Ba manifests trong `data/embeddings/`, ba collection ở `data/chroma/` | Tùng, Tuân tích hợp |
| Evaluation | Một test set 10 QA | Hit@4, token F1, judge accuracy/score | `data/eval/test_set.json`, `data/results/*_metrics.json` | Tùng |
| Observability | DataFrame của từng trạng thái | 6 GX expectations và freshness SLA | `data/quality/*.json` | Đức Anh |
| Corruption/report | Clean, metrics, quality | 6 phép mutate cố định seed; markdown báo cáo | `data/results/corruption_log.json`, `data/reports/*.md` | Nguyên |
| Orchestration/demo | Các module và artifact trên | Gọi đúng thứ tự; repair từ raw; nhúng JSON vào HTML | `src/pipelines/*`, `demo/index.html`, `demo/architecture.html` | Tuân |

## 4. Cách tái hiện kết quả

Môi trường: Python 3.11–3.13, các dependency trong `pyproject.toml`; không cần API key cho chế độ mock. Lần chạy lưu artifact dùng `LLM_PROVIDER=mock`, `JUDGE_MODE=heuristic`, `REFRESH_SOURCE=0`, `REFRESH_TEST_SET=0`, MiniLM `sentence-transformers/all-MiniLM-L6-v2` đã có trong cache, `top_k=4`, ngưỡng stale 180 ngày, giới hạn stale 25%, seed corruption `20260925`. Nếu model chưa có trong cache, cần tải một lần để tái hiện đúng backend MiniLM; fallback hashing có thể cho số khác. Bật `REFRESH_SOURCE=1` sẽ gọi Crossref và có thể đổi snapshot.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
$env:PYTHONPATH='src'
$env:LLM_PROVIDER='mock'
$env:JUDGE_MODE='heuristic'
$env:REFRESH_SOURCE='0'
$env:REFRESH_TEST_SET='0'
.venv\Scripts\python.exe script/run_phase1.py
.venv\Scripts\python.exe script/run_corruption_flow.py
.venv\Scripts\python.exe script/build_demo.py
Start-Process demo/index.html
```

Ngày 2026-09-25, hai lệnh pipeline hoàn thành: baseline in `24 documents; hit rate 1.000; quality True`; corruption flow in `1.000 / 0.800 / 1.000`. `python -m pytest tests/test_evaluation.py -q` đạt 7/7. Trang `demo/architecture.html` có thể mở trực tiếp hoặc qua nút “Kiến trúc hệ thống” trong demo.

## 5. Ingestion, cleaning và data contract

Nguồn là bộ 24 DOI Crossref ADAS được ghi trong `data/raw/adas_selected_dois.json`, tuyển chọn ngày 2026-09-25. Lần chạy này dùng bản chụp `data/raw/crossref_response.json` có đủ 24 DOI, không phụ thuộc mạng. Khi yêu cầu refresh, client có retry cho HTTP 429/5xx và chỉ ghi response mới khi toàn bộ DOI đạt điều kiện. Parser yêu cầu DOI, title, abstract tối thiểu 30 ký tự, author và ngày xuất bản; category lấy từ Crossref subject hoặc suy luận theo title/abstract và được đánh dấu provenance.

| Trường clean | Quy tắc và ý nghĩa |
| --- | --- |
| `paper_id` | DOI chữ thường, không rỗng, duy nhất; định danh và ground truth |
| `title`, `summary` | Bỏ HTML/JATS, chuẩn hóa khoảng trắng; summary tối thiểu 30 ký tự khi cleaning |
| `authors`, `categories` | Danh sách đã chuẩn hóa; thêm `authors_joined`, `categories_joined` để index |
| `published`, `updated`, `age_days` | Ngày ISO và tuổi bài báo theo ngày chạy |
| `summary_chars` | Độ dài summary sau cleaning, dùng đối chiếu |
| `text_for_embedding` | Ghép Title/Authors/Published/Categories/Summary theo 5 dòng |
| `abs_url`, `pdf_url`, `comment` | Liên kết và ghi chú nguồn/category |

Kết quả thực tế: 24 raw records → 24 clean rows, 16 cột, không mất DOI. DataFrame được khử trùng theo `paper_id` và sắp xếp theo ngày xuất bản. Bản raw là nguồn tin cậy dùng cho repair.

## 6. Evaluation setup

Test set `data/eval/test_set.json` có 10 câu hỏi, mỗi câu ứng với một DOI, chọn trải đều theo thời gian từ 24 bản ghi. Các loại câu hỏi: summary, authors, date, categories; mỗi item có `ground_truth` và `ground_truth_doc_ids`. Cùng file test set được dùng cho cả ba trạng thái, nên thay đổi metric gắn với thay đổi dữ liệu/index trong lần chạy. Retrieval dùng Chroma cosine, top-k = 4; QA ưu tiên lookup title chính xác nếu title xuất hiện trong câu hỏi, sau đó đọc metadata để trả lời. Judge của lần chạy là heuristic (`judge_llm_count=0`, `judge_fallback_count=10` ở từng trạng thái). Ragas được đánh dấu skipped trong JSON, không có điểm Ragas để báo cáo.

## 7. Kết quả baseline

| Artifact | Đường dẫn |
| --- | --- |
| Raw response và records | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` |
| Clean dataset | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` |
| Index manifest | `data/embeddings/papers_embeddings.json` |
| Test set | `data/eval/test_set.json` |
| Answers/metrics | `data/results/baseline_answers.json`, `baseline_metrics.json` |
| Quality/freshness | `data/quality/baseline_quality_report.json`, `freshness_report.json` |
| Pipeline report | `data/reports/phase1_report.md` |

Baseline gồm 24 bản ghi, 10/10 câu có ground-truth DOI trong top-4; retrieval hit rate 1.000, mean token F1 1.000, heuristic judge accuracy 1.000, mean judge score 5.000. Manifest ghi backend Chroma và embedding model MiniLM; SQLite/HNSW trong `data/chroma/` là file máy cục bộ, không cần commit vì chạy lại sẽ tái tạo được.

## 8. Data quality và freshness

Great Expectations 1.x dùng 6 expectations: số dòng trong [5, 5000], `paper_id` không null, `title` không null, `text_for_embedding` không null, `paper_id` duy nhất, `summary` dài tối thiểu 30. Baseline 6/6 đạt; corrupted 4/6 đạt vì DOI trùng và ba summary rỗng; repaired 6/6 đạt. Hiện chưa có expectation riêng bắt title ngắn hoặc noise trong nội dung; đây là khoảng trống kiểm tra cần bổ sung.

Freshness tính trên `age_days`: một dòng stale khi quá 180 ngày; dataset fail nếu tỷ lệ stale >25%. Baseline 0/24 (0%, PASS), corrupted 7/21 (33.33%, FAIL), repaired 0/24 (0%, PASS). Bản báo cáo freshness baseline được giữ riêng khỏi hai trạng thái còn lại. Ngày xuất bản mới nhất của baseline/repaired là 2026-09-24, corrupted là 2026-08-10.

## 9. Corruption scenarios và repair

| Lỗi tiêm, theo thứ tự | Số DOI/dòng bị tác động | Tín hiệu quan sát |
| --- | ---: | --- |
| `drop_latest_records` | 5 DOI bị bỏ | Clean còn thiếu bản ghi mới; hai ground-truth DOI trong bộ 10 câu không còn |
| `blank_summary` | 3 DOI | GX summary length fail |
| `inject_noise` | 3 DOI | Nội dung index bị nhiễu; chưa có expectation riêng |
| `truncate_title` | 3 DOI | Title bị cắt còn 5 ký tự; kiểm tra non-null chưa bắt |
| `stale_date` | 7 DOI | Freshness 33.33% > 25% |
| `duplicate_rows` | 2 DOI được nhân bản | GX uniqueness fail; số dòng sau cùng là 21 |

Chi tiết DOI và tham số nằm trong `data/results/corruption_log.json`; seed `20260925`. Các lỗi được áp tuần tự, vì thế số “bị tác động” trong từng bước không cộng thành số dòng cuối. Repair không sửa trực tiếp bản corrupted: đọc lại `data/raw/crossref_records.json`, gọi lại cleaning, xây collection `papers-repaired` và đánh giá lại bằng test set cũ. Điều này loại bỏ cả lỗi chưa được quality gate bắt và cho phép kiểm chứng trạng thái phục hồi.

## 10. So sánh baseline, corrupted và repaired

| Chỉ số | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Số dòng dữ liệu | 24 | 21 | 24 |
| Retrieval hit rate @4 | 1.000 | 0.800 | 1.000 |
| Mean token F1 | 1.000 | 0.7267 | 1.000 |
| Heuristic judge accuracy | 1.000 | 0.700 | 1.000 |
| Heuristic mean judge score /5 | 5.000 | 3.800 | 5.000 |
| GX expectations đạt | 6/6 | 4/6 | 6/6 |
| Freshness stale | 0/24 | 7/21 | 0/24 |
| Quality Gate | PASS | FAIL | PASS |

Corruption gây giảm 0.200 hit rate và 0.2733 token F1; repair phục hồi về baseline trong cùng benchmark. `data/reports/corruption_report.md` và các JSON tương ứng là bằng chứng máy đọc được. Vì sáu lỗi được tiêm đồng thời, kết quả tổng không chứng minh mức đóng góp riêng của từng lỗi.

## 11. Vấn đề tích hợp quan trọng

1. Năm module độc lập dùng chung contract `paper_id`, `text_for_embedding` và test set; pipeline điều phối theo thứ tự raw → clean → quality → index → evaluate → corrupt → repair.
2. Cần phân biệt “thành công của GX” và freshness; quality tổng hợp là PASS chỉ khi cả hai đạt. Báo cáo freshness ba trạng thái ghi tách file để tránh ghi đè bằng chứng baseline.
3. Offline snapshot, MiniLM cache, mock LLM và heuristic judge giúp chạy không cần API key. Manifest ghi backend embedding thực tế để có thể kiểm toán kết quả.
4. Demo `demo/index.html` nhúng các JSON đã sinh; `script/build_demo.py` cập nhật số liệu, log và trang `demo/architecture.html`. Dashboard Streamlit của Đức Anh vẫn là deliverable riêng; demo HTML đáp ứng yêu cầu trình bày không dùng Streamlit.

## 12. Giới hạn và hướng cải thiện

- Câu hỏi có title nguyên văn và hàm QA lookup title chính xác; 10/10 baseline chủ yếu là kiểm tra tích hợp, chưa đánh giá khả năng tìm kiếm ngữ nghĩa trên câu hỏi mở.
- Judge là heuristic, không phải LLM judge; Ragas chưa chạy. Cần thêm bộ hỏi độc lập, LLM judge có quota ổn định và báo riêng kết quả Ragas.
- 24 DOI được tuyển chọn thủ công trong phạm vi ADAS, không đại diện cho toàn bộ Crossref. Refresh nguồn có thể thay đổi dữ liệu và kết quả.
- Bổ sung expectation cho độ dài title và noise, rồi chạy ablation từng corruption để đo nguyên nhân riêng.
- Có thể thêm CI chạy hai pipeline trên snapshot và kiểm tra `PASS → FAIL → PASS` cùng tính toàn vẹn raw.

## 13. Checklist trước khi nộp

- [x] 24 raw và 24 clean records; test set 10 câu.
- [x] Chạy baseline và corruption/repair end-to-end; 7/7 test evaluation đạt.
- [x] Ba bộ metrics, quality, freshness, manifests, log sáu lỗi và hai báo cáo pipeline đã sinh.
- [x] Demo HTML độc lập và trang kiến trúc hệ thống chữ lớn, số liệu cập nhật từ artifact.
- [x] Báo cáo nhóm và báo cáo cá nhân Tuân có số liệu lần chạy thực tế; các báo cáo cá nhân thành viên được giữ nguyên theo phần họ bàn giao.
- [x] Không đưa API key hay Chroma DB nhị phân máy cục bộ vào repository.
