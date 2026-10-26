# Từ điển công thức tài chính — Gold

**Đơn vị:** các trường `_vnd_mn` tính bằng **triệu VND**. `*_pct` trả kết quả % (nhân 100); `*_x` tính theo lần; `*_days` tính theo ngày.

| Chỉ tiêu | Công thức | Quy ước |
|---|---|---|
| Revenue Growth (%) | (Revenue_t / Revenue_(t-1) − 1) × 100 | 2021 = NA |
| Gross Margin (%) | Gross Profit / Revenue × 100 | |
| Operating Margin (%) | Operating Profit / Revenue × 100 | |
| Net Margin (%) | Net Income / Revenue × 100 | |
| Current Ratio (lần) | Total Current Assets / Total Current Liabilities | |
| Quick Ratio (lần) | (Cash + Accounts Receivable) / Total Current Liabilities | Không cộng Inventory |
| Total Debt | Short-term Debt + Long-term Debt | Không thay bằng Total Liabilities |
| Debt/Assets (%) | Total Debt / Total Assets × 100 | |
| Debt/Equity (lần) | Total Debt / Total Equity | |
| ROA (%) | Net Income / Average Total Assets × 100 | Bình quân t và t−1; 2021 = NA |
| ROE (%) | Net Income / Average Total Equity × 100 | Bình quân t và t−1; 2021 = NA |
| CFO | Net Cash from Operating Activities | Giữ dấu nguồn |
| CFO Margin (%) | CFO / Revenue × 100 | |
| CFO / Net Income (lần) | CFO / Net Income | Nếu Net Income = 0 ⇒ NA |
| Free Cash Flow | CFO + Capital Expenditure | CAPEX âm trong nguồn |
| DSO (ngày) | Average Accounts Receivable / Revenue × 365 | 2021 = NA |
| Inventory Days (ngày) | Average Inventory / COGS × 365 | 2021 = NA |
| DPO (ngày) | Average Accounts Payable / COGS × 365 | 2021 = NA |
| Interest Coverage (lần) | Operating Profit / Interest Expense | |
| Working Capital | Total Current Assets − Total Current Liabilities | |
| Accounts Receivable Growth (%) | (AR_t / AR_(t−1) − 1) × 100 | 2021 = NA |
| Inventory Growth (%) | (Inventory_t / Inventory_(t−1) − 1) × 100 | 2021 = NA |
| Total Debt Growth (%) | (Debt_t / Debt_(t−1) − 1) × 100 | 2021 = NA |
| Gross Margin Change (điểm %) | GM_t − GM_(t−1) | 2021 = NA |

**Chia cho 0:** kết quả = NA (không thay bằng 0, không để vô cực). Trong CSV NaN được ghi ô trống.

**Benchmark:** Group theo `(subindustry, fiscal_year)`; lấy `median(metric)`, `delta = value − median`, và `% rank` trong nhóm. Nhóm hiện gồm 12 doanh nghiệp giả lập mỗi năm.

**Năm 2021:** không tự tạo hoặc suy đoán 2020, áp dụng trực tiếp hướng dẫn BTC.

## Đối chiếu

Kết quả được so sánh với `data/samples/financial_metrics_sample.csv` (18 dòng). Sai số cho phép tương ứng nửa đơn vị chữ số cuối của mẫu (vd 2 chữ số thập phân ±0.005). Chỉ tiêu `revenue_growth_pct` của C009/2022 chênh ranh giới làm tròn 0.000003 quá ngưỡng này; đã đưa vào `outputs/kpi_report.json` để minh bạch, không sửa công thức.
