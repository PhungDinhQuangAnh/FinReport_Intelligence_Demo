# FINREPORT_INTELLIGENCE_GOLD

**Festival Chuyển đổi số 2026 · Vòng sơ khảo Bảng C · Case 3 – FinReport Intelligence**

Phiên bản Gold được xây dựng bằng **Python + Streamlit**, nằm hoàn toàn trong một thư mục dự án và sử dụng đúng Data Pack giả lập của BTC. Mục tiêu là đáp ứng đầy đủ Bronze, cộng các năng lực Gold: **Calculate → Verify → Explain**, tự kiểm tra phép tính, explainability, confidence, audit trail, what-if/scenario và Financial Analyst Assistant có human-in-the-loop.

> Dữ liệu và tên doanh nghiệp đều giả lập. Kết quả chỉ hỗ trợ phân tích, không phải kết luận kiểm toán, kết luận gian lận hay khuyến nghị đầu tư.

## 1. Chạy dự án

Yêu cầu Python 3.10+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.build_outputs
python -m pytest -q
python -m streamlit run app.py
```

Streamlit thường mở tại `http://localhost:8501`.

## 2. Gold khác Bronze ở đâu?

| Năng lực | Gold implementation |
|---|---|
| Calculate | Tính ratio, trend, cash flow, working capital, leverage và profitability trên 60 company-year |
| Verify | Lớp `verification.py` tính lại độc lập 6 công thức lõi cho từng company-year; kiểm tra evidence trước khi Explain |
| Explain | Mỗi cảnh báo có rule, lý do, derived metrics, file/trường/năm nguồn và lời giải thích ngắn |
| Confidence | Confidence heuristic bị giảm nếu verification/evidence không đạt; không trình bày như xác suất thống kê |
| Audit trail | Run ID, input fingerprint SHA-256, model version và từng stage được ghi vào CSV + JSONL |
| Benchmark | Median + percentile theo cùng phân ngành, cùng năm |
| Anomaly | Robust Z-score dùng median + MAD, không đọc nhãn mẫu công khai |
| Health score | 5 chiều: profitability, liquidity, cash quality, leverage, working capital |
| Alert | Rule + peer context + anomaly support + escalation logic |
| What-if | Thay Revenue, COGS, CFO, AR, Inventory, Debt, Interest Expense và xem các chỉ tiêu thay đổi |
| Analyst Assistant | Trợ lý deterministic trả lời một số intent tài chính, luôn kèm evidence + confidence |
| Human-in-the-loop | Người dùng ACCEPT / REJECT / NEEDS_REVIEW và ghi chú; lưu vào `outputs/human_reviews.csv` |

## 3. Kết quả kiểm thử hiện tại

Khi chạy trên Data Pack đóng gói trong dự án:

- 60 company-year, 12 doanh nghiệp, 2021–2025.
- Calculation Accuracy: **413/414 = 99,76%** trên mẫu chỉ tiêu công khai.
- Numerical QA Accuracy: **30/30 = 100%** trên câu hỏi mẫu công khai.
- Independent Calculate Verification: **60/60 PASS**.
- Evidence Traceability: **484/484 = 100%** trên các lượt tham chiếu bằng chứng đã sinh.
- High/Critical Alert Recall: **100,00%** trên 18 nhãn mẫu công khai; Precision **92,31%**, F1 **96,00%**; exact severity **17/18 = 94,44%**. Đây là hậu kiểm mẫu, không phải dữ liệu ẩn.

KPI cảnh báo chỉ là hậu kiểm trên mẫu public, **không dùng để huấn luyện/hard-code** và không bảo đảm kết quả trên test ẩn.

**Lưu ý về QA:** Numerical QA Accuracy 100% là **30/30 câu mẫu BTC**, *không phải* độ chính xác của Financial Analyst Assistant với câu hỏi tự do. Trong mục **Mô phỏng & trợ lý → Financial Analyst Assistant**, ứng dụng tách **Hỏi tự do (rule-based)** và **30 câu QA mẫu BTC**. Câu hỏi CFO C007/2025 (Q002) nay cũng được hỗ trợ ở phần hỏi tự do với kết quả **−20.564 triệu VND** và bằng chứng `cashflow.csv`. Câu hỏi ngoài phạm vi được đánh dấu rõ **Chưa hỗ trợ**.

## 3A. Quy tắc chấm điểm bình quân 14 rule

- **RuleScore = tổng số rule kích hoạt / 14** (ví dụ 5/14 = 0,3571); bỏ hoàn toàn việc ưu tiên trọng số khác nhau trong các rule.
- **RiskScore = min(1, 0,88 × RuleScore + 0,12 × AnomalyScore)**.
- **CRITICAL ≥ 0,68**, hoặc tổ hợp khủng hoảng. Sau đó lần lượt: 8 điều kiện **LOW/RECOVERING** → HIGH khi Gross Margin giảm ≥ 3 điểm % và Net Margin < 8% → HIGH theo ngưỡng 0,25/0,50 → MEDIUM theo rule/Anomaly 0,28 → LOW mặc định.
- Bộ **8 điều kiện phục hồi chưa được người dùng định nghĩa chi tiết**; nhóm cần rà soát **8 điều kiện MVP đề xuất** trong `docs/ALERT_RULES.md` trước khi dùng kết quả bảo vệ.
- Các con số KPI phần trên đã được **chạy lại trên phiên bản mới**. Không dùng KPI của phiên bản weight cũ.

## 4. Cấu trúc thư mục

```text
FinReport_Intelligence_Demo/
├── app.py
├── README.md
├── requirements.txt
├── .streamlit/config.toml
├── finreport/
│   ├── config.py
│   ├── data.py
│   ├── metrics.py
│   ├── benchmark.py
│   ├── anomaly.py
│   ├── health.py
│   ├── alerts.py
│   ├── verification.py
│   ├── explain.py
│   ├── provenance.py
│   ├── qa.py
│   ├── scenario.py
│   ├── assistant.py
│   ├── review.py
│   ├── audit.py
│   ├── evaluation.py
│   └── pipeline.py
├── data/
│   ├── raw/                 # 5 CSV gốc BTC
│   ├── metadata/            # data dictionary + manifest
│   ├── samples/             # public metrics/scenarios/questions/answers
│   └── templates/           # schema output BTC
├── outputs/
│   ├── analysis_full_gold.csv
│   ├── financial_metrics_gold.csv
│   ├── alerts_detail_gold.csv
│   ├── verification_detail.csv
│   ├── audit_trail.csv
│   ├── audit_trail.jsonl
│   ├── human_reviews.csv
│   ├── submission_output_Case3.csv
│   ├── qa_submission_Case3.csv
│   ├── validation_report.json
│   └── kpi_report_gold.json
├── scripts/
│   └── build_outputs.py
├── tests/
│   └── test_gold.py
└── docs/
    ├── ARCHITECTURE.md
    ├── GOLD_CHECKLIST.md
    ├── ALERT_RULES.md
    ├── METRIC_FORMULAS.md
    ├── SCENARIO_GUIDE.md
    ├── ASSISTANT_GUIDE.md
    ├── LIMITATIONS.md
    ├── DEMO_SCRIPT.md
    └── reference/
```

## 5. Pipeline

```text
Data Load
  ↓
Validate + SHA-256 + accounting reconciliation
  ↓
Calculate Metrics
  ↓
Trend + Peer Benchmark
  ↓
Robust Anomaly + Health Score
  ↓
Multi-signal Alerts
  ↓
VERIFY calculations + evidence
  ↓
EXPLAIN + confidence
  ↓
Numerical QA + KPI evaluation
  ↓
Audit Trail
  ↓
Streamlit / CSV outputs / Human Review / What-if
```

## 6. Giao diện Web

| Màn hình | Nội dung chính | Cách demo đề xuất |
|---|---|---|
| **1. Tổng quan điều hành** | 4 KPI ngành, xếp hạng rủi ro, cơ cấu severity, danh sách ưu tiên | Chọn năm 2025, xem top risk |
| **2. Hồ sơ doanh nghiệp** | 5 năm trend/peer median, health score 5 chiều, CFO vs lợi nhuận, bảng tỷ số và nguồn | Chọn doanh nghiệp muốn phân tích |
| **3. So sánh cùng ngành** | Benchmark theo metric, trung vị, percentile, robust anomaly | Chọn biên LN gộp hoặc DSO |
| **4. Cảnh báo & truy vết** | Gold explanation, rule evidence, Verify, confidence, human review | Mở một rule để xem file/trường/năm |
| **5. Mô phỏng & trợ lý** | 8 giả định What-if, so sánh before/after, trợ lý QA luật kèm evidence | Thử CFO giảm 20%, hỏi câu ví dụ |
| **6. Chất lượng & xuất dữ liệu** | Accuracy, Recall, Traceability, Verification, Audit và tải CSV | Mở KPI; tải output BTC |

Sử dụng bộ lọc **Năm tài chính** và **Doanh nghiệp phân tích** ở thanh bên. Chúng tác động đến cả 6 màn hình; benchmark vẫn được tính trên toàn bộ doanh nghiệp cùng ngành/cùng năm để giữ đúng ý nghĩa thống kê.

Xem `docs/UI_GUIDE.md` để biết thao tác demo, cấu trúc giao diện và điểm cần lưu ý.

## 7. Quy ước quan trọng

- Đơn vị số liệu: **triệu VND**.
- CAPEX là số âm; `FCF = CFO + CAPEX`.
- Chỉ tiêu cần số dư đầu kỳ / tăng trưởng không tự sinh 2020; 2021 để N/A khi không đủ dữ liệu.
- Benchmark luôn theo **cùng phân ngành + cùng năm**, tránh future leakage.
- Anomaly và alert engine không đọc `financial_scenarios_sample.csv` để ra dự đoán.
- Confidence là **heuristic reliability score**, không phải xác suất đã hiệu chuẩn.
- What-if là mô phỏng giả định, không phải forecast đã được huấn luyện.
- Public labels chỉ dùng trong `evaluation.py` để hậu kiểm chất lượng sau khi pipeline dự đoán.

## 8. Tài liệu nên đọc

- `docs/GOLD_CHECKLIST.md`: đối chiếu từng tiêu chí Gold của BTC.
- `docs/ARCHITECTURE.md`: kiến trúc và vai trò từng module.
- `docs/ALERT_RULES.md`: các luật cảnh báo và escalation.
- `docs/SCENARIO_GUIDE.md`: cách dùng What-if.
- `docs/ASSISTANT_GUIDE.md`: câu hỏi trợ lý hỗ trợ.
- `docs/LIMITATIONS.md`: giới hạn và rủi ro đạo đức.
- `docs/DEMO_SCRIPT.md`: kịch bản demo ngắn trước hội đồng.
