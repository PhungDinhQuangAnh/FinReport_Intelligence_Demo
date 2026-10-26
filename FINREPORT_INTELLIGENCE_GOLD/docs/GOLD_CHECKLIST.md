# Gold Checklist — FINREPORT_INTELLIGENCE_Gold

Theo đề BTC, Gold được cộng điểm cao khi có quy trình **Calculate → Verify → Explain** hoặc tương đương; tự kiểm tra phép tính trước khi nhận xét; explainability, confidence và audit trail; đồng thời có What-if/scenario hoặc Financial Analyst Assistant/human-in-the-loop.

| Yêu cầu | File/module | Trạng thái |
|---|---|---|
| Bronze: ratios | `metrics.py` | DONE |
| Bronze: trend | `metrics.py`, Streamlit Company 360 | DONE |
| Bronze: benchmark | `benchmark.py` | DONE |
| Bronze: alert | `alerts.py` | DONE |
| Bronze: dashboard + KPI | `app.py`, `evaluation.py` | DONE |
| Silver: health score | `health.py` | DONE |
| Silver: anomaly detection | `anomaly.py` | DONE |
| Silver: multi-signal | `alerts.py` | DONE |
| Silver: measured KPI | `kpi_report_gold.json` | DONE |
| Gold: Calculate → Verify → Explain | `pipeline.py`, `verification.py`, `explain.py` | DONE |
| Gold: self-check before comments | `verification.py` runs before `explain.py` | DONE |
| Gold: explainability | rule + reason + metric + raw evidence | DONE |
| Gold: confidence | `confidence` after verification penalty | DONE |
| Gold: audit trail | `audit.py`, CSV + JSONL | DONE |
| Gold: What-if/scenario | `scenario.py`, Streamlit tab 5 | DONE |
| Gold: Analyst Assistant | `assistant.py`, Streamlit tab 6 | DONE |
| Gold: human-in-the-loop | `review.py`, Streamlit ACCEPT/REJECT/NEEDS_REVIEW | DONE |

## Chứng minh bằng KPI

Public sample evaluation is used only after inference. Current run reports:

- Calculation Accuracy: 99.76%
- Numerical QA Accuracy: 100%
- Verify: 60/60 PASS
- Evidence Traceability: 100%
- High/Critical Recall: 100.00% (12/12 high-risk labels detected, public sample; equal14 v1.1)

Không tuyên bố các con số này là hiệu năng trên dữ liệu ẩn.
