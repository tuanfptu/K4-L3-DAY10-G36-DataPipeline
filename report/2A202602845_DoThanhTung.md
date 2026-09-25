# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo phần RAG + Evaluation của nhóm G36, ghi theo kết quả chạy thực tế ngày 25/09/2026. Mã nguồn và bản nháp báo cáo được chuẩn bị với sự hỗ trợ của Claude Code; Tùng tự rà soát, chạy lại lệnh xác minh và chịu trách nhiệm giải thích từng phần. Metrics corrupted/repaired chính thức **chưa có** vì phụ thuộc module của thành viên khác (xem mục 6 và 8).

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đỗ Thanh Tùng |
| MSSV               | 2A202602845 |
| Email              | thanhtung.30082020@gmail.com |
| Khóa/Lớp         | K4 |
| Tên nhóm         | G36 |
| Vai trò chính    | RAG + Evaluation — test set, retrieval/QA, metrics |
| Repository         | https://github.com/tuanfptu/K4-L3-DAY10-G36-DataPipeline |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------- |
| Bộ đề benchmark | `src/evaluation/testset.py` — `build_test_set`, `load_or_build_test_set` | Clean DataFrame 24 dòng của Minh | `data/eval/test_set.json` (10 câu) | Hoàn thành |
| Chấm điểm RAG | `src/evaluation/metrics.py` — `evaluate_pipeline`, `_judge_answer`, `_build_judge_llm` | Index Chroma + test set | `*_metrics.json`, `*_answers.json` cho 3 trạng thái | Hoàn thành phần code; baseline đã chạy thử; corrupted/repaired chờ tích hợp |
| Kiểm tra vector index | `src/retrieval/index.py` — `_build_documents` | Clean/corrupted DataFrame | Collection Chroma `papers-baseline/corrupted/repaired` | Hoàn thành (đã kiểm tra, sửa metadata) |
| Kiểm tra QA | `src/retrieval/qa.py` — `answer_question` | Câu hỏi + index | `AnswerResult` | Hoàn thành (đã kiểm tra, không cần sửa) |
| Test tự động | `tests/test_evaluation.py` | Clean data | 7 test pytest | Hoàn thành |

Output của tôi được dùng bởi: **Tuân** gọi `load_or_build_test_set` và `evaluate_pipeline` trong `phase1.py` / `corruption_flow.py`; **Nguyên** đọc 3 file metrics để viết `corruption_report.md`; **Đức Anh** có thể hiển thị metrics trên dashboard. Tôi nhận từ **Minh** schema clean (`paper_id`, `title`, `summary`, `published`, `authors_joined`, `categories_joined`, `text_for_embedding`).

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Cài môi trường, xử lý Smart App Control chặn DLL, chọn model Gemini còn hoạt động | Cả nhóm / `.env.example` | `.env.example` đổi `LLM_MODEL` sang `gemini-3.5-flash-lite` (bản `gemini-2.5-flash` mặc định trả 404 với key mới) |
| Rà dữ liệu clean trước khi làm test set | Minh / `cleaning.py` | Phát hiện 4 summary còn tiền tố `Abstract`/`ABSTRACT` (dòng 8, 9, 19, 20) và khoảng trắng thừa trước dấu phẩy (`Prunario ,`); đã báo lại, không tự sửa file của Minh |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Sinh 10 câu hỏi cố định, phủ 4 dạng | `testset.py`, `data/eval/test_set.json` | 3 summary / 3 authors / 2 date / 2 categories, 10 paper khác nhau | Lệnh Bước 5 Guide; md5 giống nhau sau 2 lần chạy |
| Khóa một bộ đề cho 3 trạng thái | `load_or_build_test_set` | Đọc lại file đã có, chỉ build lại khi `REFRESH_TEST_SET=1` | `test_load_or_build_reuses_existing_file` |
| Sửa judge âm thầm rơi về heuristic | `metrics.py` | Thêm `judge_llm_count`, `judge_fallback_count`, `judge_source`; ngắt gọi LLM sau lỗi đầu tiên; `JUDGE_MODE=heuristic` | Lượt chấm thử: 10/10 câu `source = llm`, 26,7 s |
| Chroma nhận dữ liệu corrupted có giá trị rỗng | `index.py::_build_documents` | Metadata ép về `str`, `None/NaN` → `""` | `test_evaluation_detects_corrupted_answers` |
| Kiểm chứng bộ chấm phát hiện dữ liệu hỏng | `tests/test_evaluation.py` | 7 test | `pytest tests/test_evaluation.py` → `7 passed in 27.28s` |

Output cụ thể: `data/eval/test_set.json` là bộ đề duy nhất cho cả baseline, corrupted và repaired. Mỗi câu có `ground_truth_doc_ids` là DOI của bài báo, nên có thể đo retrieval (bài đúng có nằm trong top-k không) tách biệt với chất lượng câu trả lời (Token F1, LLM judge).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần một "đề thi có đáp án" cố định để đo xem RAG trả lời đúng hay sai trên từng trạng thái dữ liệu. Nếu đề thay đổi giữa các lần chạy, hoặc bị sinh lại từ dữ liệu đã hỏng, thì đáp án cũng hỏng theo và phép so sánh baseline/corrupted/repaired mất ý nghĩa. Ngoài ra, điểm judge phải phản ánh đúng việc LLM có thật sự chấm hay không.

### Cách triển khai

1. **Câu hỏi khớp với cách QA trả lời.** `qa.py::_extract_answer` chọn trường trả lời theo từ khóa trong câu hỏi (`who authored`, `when was`, `what categories`, còn lại là summary) và tra cứu chính xác theo tiêu đề đặt trong dấu nháy đơn. Vì vậy mỗi dạng câu hỏi dùng một mẫu cố định chứa đúng từ khóa đó, và `ground_truth` lấy đúng trường tương ứng: `first_sentence(summary)`, `authors_joined`, `published`, `categories_joined`.
2. **Lọc paper hợp lệ.** Bỏ dòng thiếu trường, trùng `paper_id`, hoặc title chứa `'` (vì regex `'([^']+)'` sẽ cắt sai title). Câu đầu của summary phải dài ít nhất 30 ký tự.
3. **Chọn 10 paper trải đều theo ngày xuất bản**, không dùng random: sắp theo `published` giảm dần, lấy vị trí `round(i·(n−1)/9)` với `i = 0..9`. Với 24 bài, các vị trí được chọn là 0, 3, 5, 8, 10, 13, 15, 18, 20, 23. Bộ đề vì thế có cả bài mới nhất (bị ảnh hưởng khi corruption xóa 20% bài mới) lẫn bài cũ.
4. **Xoay vòng dạng câu hỏi** summary → authors → date → categories, ra tỉ lệ 3/3/2/2.
5. **Judge:** tạo LLM một lần cho mỗi lượt chấm. Nếu lỗi (hết quota, mất mạng) thì ghi `judge_source = "heuristic"` và dừng gọi LLM cho các câu còn lại. Summary ghi số câu chấm bằng LLM và số câu chấm bằng heuristic.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Clean DataFrame có các cột `paper_id, title, summary, published, authors_joined, categories_joined`; `Settings.paths.eval_testset` |
| Output                         | List 10 dict `{id, question_type, question, ground_truth, ground_truth_doc_ids}` ghi ra `data/eval/test_set.json`; metrics gồm `samples, retrieval_hit_rate, mean_token_f1, judge_accuracy, mean_judge_score, judge_llm_count, judge_fallback_count, ragas` |
| Module phụ thuộc             | `ingestion/cleaning.py` (schema), `retrieval/index.py`, `retrieval/qa.py`, `retrieval/llm.py`, `core/utils.py` |
| Module sử dụng output        | `pipelines/phase1.py`, `pipelines/corruption_flow.py`, `observability/reporting.py` |
| Điều kiện lỗi cần xử lý | Dưới 10 paper hợp lệ → `ValueError`; thiếu cột → `ValueError`; file test set thiếu trường → `ValueError`; LLM hết quota → heuristic có đánh dấu; metadata `None/NaN` trong dữ liệu corrupted → chuỗi rỗng |

Chữ ký `build_test_set(df, output_path)` và `evaluate_pipeline(...)` giữ nguyên để không làm hỏng module khác. Các key metric cũ giữ nguyên, chỉ thêm key mới.

### Cách xác minh

```bash
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
python -m pytest tests/test_evaluation.py -q
```

- **Kết quả mong đợi:** in `Sinh được 10 câu hỏi test`; tất cả test pass.
- **Kết quả thực tế:** `Tín hiệu hoàn thành: Sinh được 10 câu hỏi test`; md5 `751677c6ddfac9e1bdf450e290cf1924` giống nhau sau 2 lần chạy; `7 passed in 27.28s`.
- **Artifact/log:** `data/eval/test_set.json`, `tests/test_evaluation.py`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** chọn 10 paper nào trong 24 bài để làm đề.
- **Các phương án đã cân nhắc:** (a) `df.sample(10)` ngẫu nhiên; (b) 10 bài mới nhất (`head(10)`); (c) 10 bài trải đều theo thời gian, cố định.
- **Phương án đã chọn:** (c).
- **Lý do:** (a) mỗi lần chạy ra đề khác nên không tái lập được, trừ khi cố định seed, và vẫn phụ thuộc thứ tự dòng. (b) quá nhạy với lỗi "drop latest": 5/10 câu mất tài liệu cùng lúc nên hit rate sụp, che mất tác động của các lỗi khác. (c) tái lập được, không phụ thuộc thứ tự dòng đầu vào, và vẫn có 2 bài thuộc nhóm 20% mới nhất nên lỗi drop latest vẫn đo được.
- **Bằng chứng quyết định phù hợp:** `test_build_test_set_is_deterministic` xáo trộn DataFrame vẫn ra cùng bộ đề. Trong kịch bản kiểm thử xóa 5 bài mới nhất, hit rate giảm từ 1.00 còn 0.80, đúng bằng 2/10 câu bị ảnh hưởng.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** lượt chấm baseline đầu tiên cho `judge_accuracy = 1.0`, `mean_judge_score = 5` nhưng mất 427 giây, và cả 10 câu có `reasoning = "Fallback heuristic judge used because the LLM evaluator was unavailable."`. Lỗi gốc khi gọi trực tiếp: `GoogleRateLimitError ... 429 RESOURCE_EXHAUSTED ... quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier ... limit: 20, model: gemini-3.8-flash`.
- **Lệnh hoặc bước tái hiện:** gọi `build_llm(s).with_structured_output(JudgeVerdict).invoke(...)` 3 lần liên tiếp sau khi đã dùng hết quota ngày.
- **Nguyên nhân gốc:** free tier giới hạn 20 request/ngày cho mỗi model, trong khi một lần chạy đủ 3 trạng thái cần 30 lần gọi judge. Code cũ bắt mọi exception rồi trả heuristic mà không đánh dấu, và tạo LLM mới cho từng câu nên mỗi câu phải chờ retry khoảng 40 giây. Kết quả là metrics trông như "LLM chấm 5/5" nhưng thực chất là heuristic: đúng kiểu silent failure mà bài lab cảnh báo, và nếu ghi vào báo cáo sẽ thành sai số liệu.
- **Cách xử lý:** (1) đổi model sang `gemini-3.5-flash-lite` (quota riêng theo model); (2) `metrics.py` ghi `judge_source` cho từng câu và `judge_llm_count` / `judge_fallback_count` trong summary; (3) sau lỗi đầu tiên thì dừng gọi LLM; (4) thêm `JUDGE_MODE=heuristic` để cả ba trạng thái được chấm cùng một cách khi cần.
- **Cách xác minh sau khi sửa:** chạy lại baseline, được `judge_llm_count = 10`, `judge_fallback_count = 0`, hết 26,7 giây.
- **Điều học được:** một metric chỉ đáng tin khi biết nó được tạo ra bằng cách nào. Chỗ `except Exception` nuốt lỗi cần để lại dấu vết trong artifact.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Từ Crossref đến vector index:** `crossref.py` lấy metadata 24 DOI (hoặc đọc snapshot khi mất mạng) và lưu nguyên response vào `data/raw/`. `cleaning.py` bỏ thẻ JATS/HTML, chuẩn hóa text, tính `age_days`, khử trùng theo `paper_id` và ghép `text_for_embedding` 5 dòng. `index.py` mã hóa `text_for_embedding` bằng `all-MiniLM-L6-v2` (vector đã chuẩn hóa) và nạp vào collection Chroma dùng khoảng cách cosine, kèm metadata để QA lấy câu trả lời.
2. **Vai trò của test set và ground-truth doc IDs:** mỗi câu có `ground_truth_doc_ids`. `retrieval_hit_rate` đo tỉ lệ câu mà DOI đúng nằm trong top-k tài liệu retrieve được, tức là đo phần tìm kiếm. `mean_token_f1` so từ giữa câu trả lời và `ground_truth`, còn LLM judge chấm độ đúng về nghĩa, tức là đo phần trả lời. Tách hai loại metric giúp biết lỗi nằm ở tìm kiếm hay ở nội dung.
3. **Quality checks khác freshness:** GX kiểm tra cấu trúc và tính hợp lệ của từng batch (số dòng, null, unique `paper_id`, độ dài summary). Freshness đo độ cũ của cả kho (tỉ lệ bài có `age_days > 180` vượt 25% thì `is_fresh = False`). Dữ liệu có thể qua GX mà vẫn cũ, ví dụ lỗi stale date không vi phạm schema nào.
4. **Vì sao dùng cùng test set:** muốn quy chênh lệch metric cho dữ liệu thì chỉ được thay đổi dữ liệu. Nếu đổi câu hỏi hoặc sinh lại đáp án từ dữ liệu hỏng, chênh lệch sẽ lẫn cả độ khó của đề, hoặc bị che mất vì đáp án hỏng khớp với câu trả lời hỏng. `load_or_build_test_set` khóa bộ đề sinh từ clean data.
5. **Repair thành công khi:** trên `repaired_metrics.json` với cùng test set, `retrieval_hit_rate` và `mean_token_f1` trở về bằng baseline; `quality` của dữ liệu repaired pass lại; freshness trở về như baseline; và chạy repair lần hai vẫn ra cùng kết quả (idempotent).

## 8. Phân tích kết quả

### Metrics chính

Cột Baseline là **lượt chấm thử bằng module của tôi** (index dựng trong thư mục tạm, gọi `evaluate_pipeline` trực tiếp), chưa phải output chính thức của `script/run_phase1.py`. Hai cột Corrupted/Repaired chưa có vì `corruption.py`, `phase1.py` và `corruption_flow.py` còn `NotImplementedError` tại thời điểm viết. Tôi không điền số cho các cột chưa chạy.

| Metric/signal          | Baseline (chạy thử) | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.00 | Chưa chạy | Chưa chạy | Tra cứu đúng theo title luôn đưa bài đúng lên đầu |
| `mean_token_f1`      | 1.00 | Chưa chạy | Chưa chạy | Câu trả lời trích nguyên trường nên khớp tuyệt đối trên dữ liệu sạch |
| `judge_accuracy`     | 1.00 | Chưa chạy | Chưa chạy | 10/10 câu do `gemini-3.5-flash-lite` chấm (`judge_fallback_count = 0`) |
| `mean_judge_score`   | 5.00 | Chưa chạy | Chưa chạy | Cần so với corrupted để thấy mức giảm |
| Quality checks         | Không thuộc phần tôi | Chưa chạy | Chưa chạy | Chờ `quality.py` của Đức Anh |
| Freshness status       | 0/24 bài > 180 ngày | Chưa chạy | Chưa chạy | Bài cũ nhất 174 ngày; khoảng 01/10/2026 sẽ vượt ngưỡng nhưng vẫn dưới mức 25% |

### Độ nhạy của bộ chấm (kịch bản kiểm thử, không phải metrics chính thức)

Để biết metric nào sẽ phản ứng khi Nguyên tiêm lỗi, tôi chạy từng lỗi riêng lẻ trên **toàn bộ** 24 dòng, dùng `JUDGE_MODE=heuristic` để không tốn quota. Có dựng lại `text_for_embedding` sau khi sửa dữ liệu như bước 7 của corruption.

| Kịch bản | hit rate | token F1 | judge acc | judge score |
|---|---:|---:|---:|---:|
| Clean | 1.00 | 1.000 | 1.00 | 5.00 |
| Xóa trắng summary | 1.00 | 0.700 | 0.70 | 3.80 |
| Lùi ngày xuất bản | 1.00 | 0.800 | 0.80 | 4.20 |
| Cắt title còn 7 ký tự | 1.00 | 0.974 | 1.00 | 4.80 |
| Xóa 5 bài mới nhất | 0.80 | 0.827 | 0.80 | 4.20 |
| Nhân đôi mọi dòng | 1.00 | 1.000 | 1.00 | 5.00 |

### Kết luận từ số liệu

1. **Corruption → signal → metric:** (dự kiến, chờ chạy chính thức) xóa trắng summary làm GX `ExpectColumnValueLengthsToBeBetween` fail, và mọi câu summary có F1 = 0 (0.700 = 7/10 câu còn đúng). Lùi ngày làm freshness xấu đi, câu date trả lời sai ngày nhưng GX không bắt được vì schema vẫn hợp lệ.
2. **Repair → signal → metric:** chưa có số liệu; sẽ điền sau khi `corruption_flow.py` chạy xong.

**Corruption nào ảnh hưởng rõ nhất và vì sao?** Trong kịch bản kiểm thử, **xóa bài mới nhất** là lỗi duy nhất làm giảm `retrieval_hit_rate`, vì tài liệu đúng không còn trong kho nên không có cách nào tìm thấy. **Xóa trắng summary** làm F1 giảm mạnh nhất (−0.30), vì 3/10 câu hỏi lấy đáp án trực tiếp từ summary.

**Kết quả nào khác với kỳ vọng ban đầu?**
- *Cắt title* gần như không ảnh hưởng (F1 0.974). Ban đầu tôi nghĩ tra cứu đúng theo title thất bại thì retrieval sẽ sụp. Kiểm tra lại thì thấy embedding vẫn chứa authors và summary nên tìm kiếm ngữ nghĩa vẫn đưa bài đúng lên top-4. Chỉ `eval_008` (categories) bị bài khác chiếm vị trí số 1, nên F1 còn 0.74.
- *Nhân đôi dòng* không làm metric nào giảm, vì hit rate chỉ hỏi "bài đúng có trong top-k không". Kiểm tra thêm thì thấy số tài liệu **khác nhau** trong top-4 giảm từ 4 xuống 2 ở cả 10/10 câu: một nửa ngữ cảnh đưa cho agent là bản sao. Lỗi này chỉ GX `ExpectColumnValuesToBeUnique` bắt được. Đây là ví dụ rõ nhất cho việc cần observability ở tầng dữ liệu chứ không chỉ nhìn metric của agent.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** bộ đề đánh giá cũng là một artifact dữ liệu cần lineage. Nó phải sinh từ clean baseline, cố định và được khóa lại; sinh lại từ dữ liệu hỏng sẽ xóa mất chính tín hiệu cần đo.
2. **Data quality/observability:** metric của agent không bắt được mọi lỗi (duplicate, title cắt ngắn gần như không làm giảm điểm), nên cần GX ở tầng dữ liệu. Ngược lại, bản thân evaluator cũng có thể lỗi âm thầm (judge rơi về heuristic), nên cũng phải được quan sát.
3. **Ảnh hưởng tới RAG agent:** cùng một lỗi dữ liệu tác động khác nhau lên từng metric. Hit rate chỉ phản ứng khi mất tài liệu, còn Token F1 và judge phản ứng khi nội dung sai. Cần nhiều loại metric để khoanh vùng lỗi.

### Nếu có thêm thời gian

Thêm metric **số tài liệu khác nhau trong top-k** (và vị trí của bài đúng, dạng MRR) vào `evaluate_pipeline`, để lỗi duplicate và title cắt ngắn hiện ra trên metric của agent thay vì chỉ ở GX. Cách đo: trên kịch bản "nhân đôi mọi dòng" đã thử, metric này phải giảm từ 4.0 xuống 2.0 trong khi hit rate vẫn là 1.0; sau repair phải về lại 4.0.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [ ] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [ ] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [ ] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [ ] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [ ] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đỗ Thanh Tùng
**Ngày xác nhận:** [YYYY-MM-DD — điền sau khi tự rà soát]
