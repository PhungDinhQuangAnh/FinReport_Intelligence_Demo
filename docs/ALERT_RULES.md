# FinReport Gold — RuleScore bằng nhau & Severity 6 tầng (v1.1)

Đây là **quy tắc nội bộ thử nghiệm (heuristic)**, không phải chuẩn nghề nghiệp hoặc ngưỡng do BTC bắt buộc. Dữ liệu BTC là giả lập.

## 1. Mười bốn rule nhị phân

Mỗi rule `r_i ∈ {0,1}`: phát hiện đúng điều kiện => 1, không phát hiện => 0. Các điều kiện gốc kích hoạt 14 rule được giữ nguyên trong `finreport/alerts.py`.

| STT | Rule ID | Đóng góp nếu kích hoạt |
|---:|---|---:|
| 01 | `CFO_NEGATIVE` | 1/14 ≈ 0,071429 |
| 02 | `PROFIT_CASH_DIVERGENCE` | 1/14 ≈ 0,071429 |
| 03 | `CFO_WEAKNESS` | 1/14 ≈ 0,071429 |
| 04 | `LIQUIDITY_PRESSURE` | 1/14 ≈ 0,071429 |
| 05 | `WORKING_CAPITAL_PRESSURE` | 1/14 ≈ 0,071429 |
| 06 | `RECEIVABLES_RISK` | 1/14 ≈ 0,071429 |
| 07 | `INVENTORY_RISK` | 1/14 ≈ 0,071429 |
| 08 | `LEVERAGE_RISK` | 1/14 ≈ 0,071429 |
| 09 | `DEBT_EXPANSION` | 1/14 ≈ 0,071429 |
| 10 | `INTEREST_BURDEN` | 1/14 ≈ 0,071429 |
| 11 | `GROSS_MARGIN_DECLINE` | 1/14 ≈ 0,071429 |
| 12 | `PROFITABILITY_PRESSURE` | 1/14 ≈ 0,071429 |
| 13 | `NEGATIVE_FCF` | 1/14 ≈ 0,071429 |
| 14 | `DISTRESS_LOSS` | 1/14 ≈ 0,071429 |

`RuleScore = (r1 + ... + r14)/14`. Ví dụ 5 rule => `5/14 = 0.357142857...`.

`RiskScore = min(1, 0.88 * RuleScore + 0.12 * AnomalyScore)`, lấy **số chưa làm tròn** để đối chiếu ngưỡng, chỉ làm tròn 4 chữ số ở output.

Trong `alerts_detail_gold.csv`, cột `rule_contribution` thể hiện `1/14`; cột `severity_weight` cũ được **giữ làm bí danh tương thích**, nhưng không còn mang ý nghĩa trọng số riêng từng luật. Các cột `activated_rule_count`, `total_rule_count`, `recovery_conditions_met` và `recovery_condition_checks` xuất trong `analysis_full_gold.csv`.

## 2. Thứ tự phân loại Severity — điều kiện đầu tiên đúng sẽ thắng

| Ưu tiên | Severity | overall_health | Điều kiện |
|---|---|---|---|
| 01 | CRITICAL | HIGH_RISK | `RiskScore >= 0.68` hoặc 1 trong 3 tổ hợp khủng hoảng cũ |
| 02 | LOW | RECOVERING | Đủ **8/8 điều kiện phục hồi**, nếu chưa CRITICAL |
| 03 | HIGH | HIGH_RISK | `gross_margin_change_pp <= -3` **và** `net_margin_pct < 8` |
| 04 | HIGH | HIGH_RISK/WATCH | `RiskScore >= 0.25` hoặc `AnomalyScore >= 0.50` |
| 05 | MEDIUM | WATCH | Có >= 1 rule hoặc `AnomalyScore >= 0.28` |
| 06 | LOW | HEALTHY | Không có điều kiện nào phía trên |

**Ba tổ hợp CRITICAL được giữ từ mã nguồn cũ:**

1. Net Margin < 0, CFO < 0 và Interest Coverage < 1.
2. Tăng trưởng nợ > 25%, Debt/Assets > 30% và Interest Coverage < 4.
3. CFO < 0, Interest Coverage < 2 và (DSO > 90 hoặc Inventory Days > 120).

**Ghi chú:** Trạng thái `RECOVERING` nằm ở trường **`predicted_overall_health`**, không phải severity thứ năm; severity phải thuộc LOW/MEDIUM/HIGH/CRITICAL theo schema BTC. Dù đạt 8 điều kiện, một trường hợp CRITICAL vẫn là CRITICAL.

## 3. Tám điều kiện RECOVERING: đề xuất cần nhóm duyệt

Yêu cầu của nhóm mới chỉ ghi *“đủ 8 điều kiện phục hồi”*, **chưa nêu 8 điều kiện cụ thể**. Vì mã nguồn ban đầu cũng chưa có bộ điều kiện phục hồi, bản cập nhật tạm dùng **bộ định nghĩa minh bạch sau đây**. Đây là đề xuất triển khai, có thể thay đổi tại `RECOVERY_CRITERIA` trong `finreport/alerts.py` trước khi nộp chính thức.

| STT | Trường dữ liệu tính toán | Điều kiện để đạt |
|---:|---|---|
| 1 | `revenue_growth_pct` | >= 0% (doanh thu không giảm) |
| 2 | `gross_margin_change_pp` | >= 0 điểm % (Gross Margin không giảm) |
| 3 | `net_margin_pct` | >= 8% |
| 4 | `cfo_vnd_mn` | > 0 triệu VND |
| 5 | `cfo_to_net_income_x` | >= 0,8 lần |
| 6 | `current_ratio_x` | >= 1,5 lần |
| 7 | `interest_coverage_x` | >= 4 lần |
| 8 | `total_debt_growth_pct` | <= 0% (nợ không tăng) |

Cần **đủ 8 điều kiện đồng thời**. Điều kiện không có dữ liệu (NA) được coi là **không đạt**; ví dụ 2021 thiếu tăng trưởng năm trước. `recovery_condition_checks` lưu từng check dạng `ten_dieu_kien=0/1` để audit.

## 4. Ví dụ

- 5/14 rule => RuleScore = 0,3571. Nếu Anomaly = 0,40, `R = 0,88 × (5/14) + 0,12 × 0,40 = 0,362286...`, chưa tới 0,68 nhưng đạt HIGH do R >= 0,25, trừ khi rơi vào một ưu tiên trước đó.
- 0 rule, Anomaly = 0,30 và không đủ 8 điều kiện => MEDIUM (mức Anomaly >= 0,28).
- 0 rule, Anomaly = 0,80 và đủ 8 điều kiện => LOW/RECOVERING, vì ưu tiên 02 đứng trước HIGH theo đề xuất của nhóm (đây là lựa chọn nghiệp vụ cần nêu rõ).

## 5. Các ranh giới chưa được kiểm định thống kê

- Trọng số 0,88/0,12 cũng là heuristic, tách biệt với lựa chọn **chia đều 14 rule**.
- Các nhãn công khai phục vụ hậu kiểm, **không dùng để học trọng số hoặc threshold**; không suy diễn hiệu năng tương lai.
- What-if `scenario_risk_proxy` chỉ kiểm 7 dấu hiệu trên tổng số 14, **không phải** full `RiskScore` (thiếu benchmark, anomaly mới và logic tất cả rule).
- `docs/reference/DeThi2026_BangC_FINREPORT_INTELLIGENCE.pdf` là đề gốc; ngưỡng 0,68 và 8 điều kiện phục hồi là logic do nhóm lựa chọn.
