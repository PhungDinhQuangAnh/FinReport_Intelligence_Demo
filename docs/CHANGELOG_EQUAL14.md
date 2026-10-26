# Thay đổi v1.1 — Equal14 / Severity 0.68

- Bản gốc để so sánh: `FINREPORT_INTELLIGENCE_Gold_QA_Fixed.zip`.
- `finreport/alerts.py`: thay tổng trọng số bằng `len(flags)/14` (r_i nhị phân), lưu `activated_rule_count`, tách 8 điều kiện RECOVERING, sắp thứ tự Severity.
- `finreport/config.py`: ngưỡng Critical từ 0.62 -> 0.68; model version 1.1.0.
- `app.py`: hiển thị RuleScore n/14, 8 điều kiện và thay nhãn trọng số riêng.
- `finreport/scenario.py`: scenario risk proxy tính số tín hiệu rút gọn/14, **không** bằng full Gold RiskScore.
- `tests/test_gold.py`: thêm test 14 rule, ví dụ 5/14, 8/8 recovery, biên ngưỡng và thứ tự ưu tiên.
- `outputs/*`: xây dựng lại trên 60 company-year theo logic mới; `docs/ALERT_RULES.md` giải thích toàn bộ.
- Cảnh báo nghiệp vụ: 8 điều kiện RECOVERING được **đề xuất để triển khai**, chưa phải đặc tả đã được người dùng xác nhận.
