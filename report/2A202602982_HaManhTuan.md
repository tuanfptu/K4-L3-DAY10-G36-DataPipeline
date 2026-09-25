# Báo cáo cá nhân — Hà Mạnh Tuân

## 1. Thông tin cá nhân

| Mục | Nội dung |
| --- | --- |
| Họ và tên | Hà Mạnh Tuân |
| MSSV | 2A202602982 |
| Khóa/Lớp | K4-L3-DAY10 |
| Nhóm | G36 |
| Vai trò | Trưởng nhóm; Pipeline Integrator + Self-Healing |
| Repository | https://github.com/tuanfptu/K4-L3-DAY10-G36-DataPipeline |
| Ngày chạy tích hợp | 2026-09-25 |

## 2. Phạm vi công việc và phần bàn giao

| Phần việc | File chính | Input | Output/bằng chứng |
| --- | --- | --- | --- |
| Orchestration baseline | `src/pipelines/phase1.py`, `script/run_phase1.py` | Crossref snapshot/API và các module của nhóm | 24 clean rows, quality/freshness, Chroma baseline, 10 QA, metrics, phase1 report |
| Corruption và self-healing | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Clean baseline, raw records, sáu phép corruption của Nguyên | Corrupted/repaired datasets, ba collection, quality/freshness, comparison report |
| Tích hợp backend retrieval | `src/retrieval/embeddings.py`, `src/retrieval/llm.py`; chỉnh manifest trong `src/retrieval/index.py` | MiniLM/LLM provider khả dụng theo môi trường | Backend embedding thực tế được ghi vào manifest; mock/heuristic cho demo offline |
| Demo theo yêu cầu | `demo/index.html`, `demo/architecture.html`, `script/build_demo.py` | JSON artifacts đã chạy thật | Demo HTML/CSS/JavaScript tự chứa, có trang kiến trúc chữ lớn |
| Tổng hợp tài liệu | `README.md`, `docs/TEAM.md`, `report/group_report.md`, báo cáo này | Kết quả từ toàn bộ module | Hướng dẫn chạy, phân công và bằng chứng có thể kiểm tra |

Ownership của các module ingestion, cleaning, test set, metrics, quality, corruption và reporting thuộc các thành viên được ghi trong báo cáo nhóm. Phần tôi là ghép contract giữa các module, chạy kiểm thử end-to-end, sửa lỗi tích hợp cần thiết và xác nhận kết quả cuối.

## 3. Kiến trúc tích hợp tôi triển khai

```text
Crossref snapshot -> raw records -> cleaning -> quality/freshness
  -> MiniLM + Chroma baseline -> 10 QA -> baseline report
  -> sáu corruption đồng thời -> quality/freshness + Chroma corrupted -> metrics
  -> đọc lại raw records -> cleaning -> Chroma repaired -> metrics
  -> comparison report -> build_demo.py -> demo HTML + trang kiến trúc
```

`phase1.py` gọi source/cleaning của Minh, test set và index/evaluation của Tùng, quality/freshness của Đức Anh, reporting của Nguyên. `corruption_flow.py` sử dụng lại một test set cho ba trạng thái và chỉ nhận repair là thành công khi dữ liệu đã làm sạch lại từ raw vượt quality gate. Vì repair lấy từ `data/raw/crossref_records.json`, dữ liệu bẩn không được che bằng cách sửa metric hay ghi đè kết quả đánh giá.

## 4. Cách chạy và kết quả đã xác minh

Lần chạy lưu trong repository dùng snapshot Crossref 24 DOI ADAS, `LLM_PROVIDER=mock`, `JUDGE_MODE=heuristic`, `top_k=4`, MiniLM `sentence-transformers/all-MiniLM-L6-v2` có sẵn trong cache, Great Expectations 1.x. Không dùng API key. Trong môi trường Python đã cài `pyproject.toml`:

```powershell
$env:PYTHONPATH='src'
$env:LLM_PROVIDER='mock'
$env:JUDGE_MODE='heuristic'
$env:REFRESH_SOURCE='0'
$env:REFRESH_TEST_SET='0'
python script/run_phase1.py
python script/run_corruption_flow.py
python script/build_demo.py
python -m pytest tests/test_evaluation.py -q
```

Kết quả thực tế ngày 2026-09-25: baseline in `24 documents; hit rate 1.000; quality True`; corruption flow in `1.000 / 0.800 / 1.000`; test evaluation đạt **7/7**. Raw và clean cùng có 24 dòng; corrupted 21 dòng; repaired 24 dòng. Ba manifest ở `data/embeddings/` ghi MiniLM; judge của từng state có `judge_llm_count=0`, `judge_fallback_count=10`; Ragas được ghi `skipped`.

## 5. Quyết định kỹ thuật quan trọng

**Dùng raw snapshot làm điểm phục hồi.** Corruption được áp trên bản sao clean và ghi log theo seed `20260925`. Nếu sửa bản corrupted tại chỗ, có thể bỏ sót noise hoặc title bị cắt do các expectation hiện tại chưa phát hiện. Tôi cho pipeline đọc lại raw records, chạy cleaning, quality, index và evaluation cho collection repaired. Bằng chứng: chất lượng `PASS → FAIL → PASS`, 24 → 21 → 24 dòng, hit rate `1.000 → 0.800 → 1.000`; clean và repaired đều truy về cùng bộ raw DOI.

**Ghi provenance backend và giữ artifact chạy lại được.** Index manifest lưu tên embedding backend thực tế và đường dẫn Chroma tương đối với project khi có thể. Máy không có MiniLM cache có thể dùng hashing fallback; khi đó phải báo lại backend và không dùng số liệu MiniLM hiện tại. Chroma SQLite/HNSW là dữ liệu nhị phân máy cục bộ, được tái tạo khi chạy pipeline và không cần đưa lên Git.

**Demo là HTML độc lập.** `script/build_demo.py` nhúng metrics, quality, freshness, sáu corruption và thông tin backend vào `demo/index.html`; cập nhật hit rate trên `demo/architecture.html`. Người xem mở HTML trực tiếp, không cần Streamlit, server hay CDN cho demo yêu cầu. Dashboard Streamlit của Đức Anh vẫn được giữ như sản phẩm riêng của nhóm.

## 6. Lỗi tích hợp đã xử lý

1. Khi ghép các module, đường dẫn manifest Chroma tuyệt đối theo máy khiến artifact khó mang sang môi trường khác. Tôi ghi đường dẫn tương đối trong project, còn path ở thư mục tạm phục vụ test vẫn dùng đường dẫn tuyệt đối. Test evaluation sau chỉnh sửa đạt 7/7.
2. Luồng quality ghi freshness của cả ba trạng thái vào cùng file baseline, làm mất bằng chứng ban đầu. Tôi tách file corrupted/repaired freshness để demo và báo cáo đọc đúng từng trạng thái.
3. Tỷ lệ `stale_date` cũ không vượt ngưỡng 25%, nên kịch bản lỗi thời gian không chứng minh được SLA fail. Tôi chỉnh tỷ lệ lên 35% theo logic của corruption; thực tế 7/21 dòng stale = 33.33%, vượt giới hạn.
4. `build_demo.py` ban đầu đọc key khác schema thực tế của GX và corruption log. Tôi ánh xạ `gx_success`, `affected_paper_ids` và cập nhật số liệu trong trang kiến trúc từ JSON hiện có.

## 7. Phân tích ba trạng thái

| Tín hiệu | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Số dòng | 24 | 21 | 24 |
| Retrieval hit rate @4 | 1.000 | 0.800 | 1.000 |
| Mean token F1 | 1.000 | 0.7267 | 1.000 |
| Heuristic judge accuracy | 1.000 | 0.700 | 1.000 |
| Heuristic mean judge score /5 | 5.000 | 3.800 | 5.000 |
| GX expectations đạt | 6/6 | 4/6 | 6/6 |
| Stale records | 0/24 | 7/21 | 0/24 |
| Quality Gate | PASS | FAIL | PASS |

Corruption log ghi sáu dạng lỗi theo thứ tự: `drop_latest_records` 5 DOI, `blank_summary` 3, `inject_noise` 3, `truncate_title` 3, `stale_date` 7, `duplicate_rows` 2. GX phát hiện summary ngắn và DOI trùng; freshness phát hiện tỷ lệ bản ghi cũ. Các dạng lỗi được áp đồng thời nên không thể gán riêng 0.200 hit rate giảm cho một lỗi. Bộ hỏi gồm title nguyên văn; QA có nhánh lookup title chính xác nên baseline 1.000 chứng minh tích hợp và phục hồi trên benchmark này, chưa chứng minh retrieval ngữ nghĩa tổng quát.

## 8. Hiểu biết end-to-end và bàn giao

`paper_id` là DOI duy nhất nối raw → clean → index → ground truth; `text_for_embedding` là chuỗi năm dòng từ metadata. Quality gate kiểm shape, null, uniqueness và summary; freshness kiểm tỷ lệ `age_days > 180`. Evaluation tính hit khi `ground_truth_doc_ids` xuất hiện trong top-4 và token F1 từ câu trả lời so với ground truth. Ba collection được tách để tránh dữ liệu corrupted ghi đè baseline. Report chỉ là đầu ra sau khi đo lại, không được dùng để “sửa” kết quả.

Tôi đã bàn giao lệnh tái hiện trong `README.md`, số liệu gốc trong `data/results/`, provenance trong `data/embeddings/`, quality/freshness trong `data/quality/`, và hai trang demo. Không đưa secret vào báo cáo. Các báo cáo cá nhân của bốn thành viên khác được giữ theo nội dung họ đã bàn giao.

## 9. Giới hạn và hướng cải thiện

- 10 câu hỏi nhỏ và có exact title; cần thêm câu hỏi paraphrase không chứa title và đo retrieval độc lập với lookup.
- Judge chỉ là heuristic, không phải đánh giá LLM; Ragas chưa chạy. Chạy lại với LLM judge/Ragas khi có quota và lưu provenance từng lần.
- GX chưa bắt title quá ngắn hoặc noise, dù toàn bộ corrupted quality vẫn fail do hai lỗi khác. Bổ sung expectation và ablation từng corruption.
- Snapshot Crossref giúp tái lập, nhưng refresh nguồn có thể đổi tập dữ liệu; cần version hóa metadata nguồn nếu mở rộng thí nghiệm.

## 10. Cam kết

Các số liệu trong báo cáo lấy từ artifact chạy tích hợp ngày 2026-09-25, không thay thế bằng số giả. Tôi ghi rõ MiniLM cache, heuristic judge, Ragas skipped và giới hạn của benchmark để người đọc phân biệt kết quả đã chứng minh với phần chưa kiểm thử.
