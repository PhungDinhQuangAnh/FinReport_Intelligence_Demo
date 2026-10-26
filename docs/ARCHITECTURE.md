# Kiến trúc Gold

## 1. Nguyên tắc

Dữ liệu nguồn được coi là read-only. Pipeline tạo output mới, không sửa CSV của BTC. Mọi nhận xét rủi ro chỉ xuất hiện **sau** bước Verify.

## 2. Luồng xử lý

`Load → Validate → Calculate → Benchmark → Anomaly → Health → Alert → Verify → Explain → QA → Audit → UI/Export`

### Load + Validate
`data.py` kiểm tra file tồn tại, khóa company-year, dữ liệu thiếu, cờ synthetic, đơn vị, SHA-256 và các phương trình đối chiếu báo cáo.

### Calculate
`metrics.py` tính chỉ tiêu tài chính. Các chỉ tiêu cần t-1 để N/A ở 2021.

### Benchmark + Anomaly
`benchmark.py` chỉ dùng peer cùng năm; `anomaly.py` dùng median + MAD để giảm nhạy với outlier.

### Health
`health.py` tổng hợp percentile thành 5 dimension score và Financial Health Score 0–100.

### Alert
`alerts.py` tạo nhiều signal độc lập, risk score, severity, primary scenario và raw evidence.

### Verify
`verification.py` tính lại độc lập 6 công thức lõi và xác minh alert có evidence. Confidence bị giảm nếu Verify không đạt.

### Explain
`explain.py` chỉ dùng các trường đã tính/đã Verify để tạo nhận xét ngắn, tránh sinh nội dung không có dữ liệu hỗ trợ.

### What-if + Assistant + Human review
Ba chức năng này phục vụ quyết định và demo Gold, nhưng đều tách khỏi dữ liệu nguồn và không ghi đè kết quả pipeline.
