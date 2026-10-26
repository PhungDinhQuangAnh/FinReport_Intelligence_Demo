# Hướng dẫn giao diện FinReport Intelligence

## 1. Thay đổi giao diện

- Layout: Sidebar (điều hướng và bộ lọc) + hero banner + KPI cards + biểu đồ/bảng + insight/bằng chứng.
- 6 màn hình thay 7 tab ngang, ưu tiên thứ tự ra quyết định: Quan sát → Điều tra → So sánh → Xác minh cảnh báo → Mô phỏng → Kiểm chứng đầu ra.
- Màu: Navy (#142846), Blue (#2873EB), Teal (#0C9F91), Amber (#E9A23B), Red (#E65363).
- Các text giải thích tiếng Việt, tên metric có chú thích đơn vị. Dữ liệu nguồn vẫn giữ nguyên tên trường và định dạng file.
- Biểu đồ Plotly đồng bộ về theme, font, thang trục và chú giải; doanh nghiệp đang chọn được tô nổi bật trong biểu đồ benchmark.

## 2. Cách chạy

Từ thư mục `FINREPORT_INTELLIGENCE_Gold`:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Mở URL mà Streamlit hiển thị (thông thường là `http://localhost:8501`). Trên máy Windows có thể dùng `run_app.bat` và trên macOS/Linux dùng `bash run_app.sh`.

## 3. Demo trước giám khảo (đề xuất)

1. **Tổng quan điều hành** – Năm 2025: đọc 4 thẻ KPI, xem 12 doanh nghiệp và bảng ưu tiên.
2. **Hồ sơ doanh nghiệp** – chọn C012/2025: health score, CFO, xu hướng các chỉ tiêu, so với trung vị ngành.
3. **So sánh cùng ngành** – chọn Gross Margin hoặc DSO; giải thích median, percentile và anomaly score.
4. **Cảnh báo & truy vết** – chọn C012/2025: mở một rule, xem reason, derived metrics và file:field:company:year=value, thử lưu review (nếu có quyền ghi file).
5. **Mô phỏng & trợ lý** – điều chỉnh doanh thu/CFO và đối chiếu các chỉ tiêu; đặt câu `giải thích rủi ro C012 2025`.
6. **Chất lượng & xuất dữ liệu** – nêu Calculation Accuracy, Numerical QA Accuracy, Recall, Traceability, verification, audit; tải file output BTC.

## 4. Lưu ý tính đúng đắn

- Không thay đổi thuật toán trong `finreport/`; giao diện chỉ hiển thị output từ `build(save=False)`.
- Tất cả dữ liệu doanh nghiệp/ticker là dữ liệu giả lập của Ban Tổ chức.
- Benchmark theo cùng năm/cùng ngành; percentile cao không có nghĩa là lành mạnh với mọi chỉ tiêu.
- 2021 có thể thiếu chỉ tiêu cần số dư 2020; hiển thị N/A, không tự bịa dữ liệu.
- Confidence là heuristic và KPI public sample không khẳng định hiệu quả trên test ẩn.
- What-if là mô phỏng, không phải dự báo tài chính.
- Các thao tác review có ghi file `outputs/human_reviews.csv` theo cơ chế cũ của dự án.

## 5. Tùy biến giao diện

- Bộ màu: hằng `NAVY`, `BLUE`, `TEAL`, `AMBER`, `RED` đầu file `app.py` và `.streamlit/config.toml`.
- Menu: `NAV_ITEMS` + `PAGE_META`.
- Chỉ tiêu tài chính: `METRIC_LABELS` và `METRIC_SECTIONS`.
- Thành phần dùng lại: `card`, `section`, `callout`, `chart_style`, `plot`, `format_table`.
- Cấu trúc dữ liệu/logic tính không nằm trong CSS/HTML; xem `finreport/` nếu cần bổ sung chỉ tiêu.

## 6. Kiểm thử khi thay đổi

```bash
python -m py_compile app.py
python -m pytest -q
python -m streamlit run app.py
```

Nếu lần đầu mở ứng dụng bị lỗi thiếu thư viện, cài `requirements.txt` rồi chạy lại.

## 7. Cập nhật QA và trợ lý (26/10/2026)

- Ở **Mô phỏng & trợ lý → Financial Analyst Assistant**, chọn **Hỏi tự do** để nhập câu hỏi company-year theo những nhóm chỉ tiêu được hỗ trợ; chọn **30 câu QA mẫu BTC** để xem kết quả bộ kiểm thử công khai. Mặc định bộ mẫu mở **Q002 (CFO C007/2025)**.
- **Numerical QA Accuracy 100%** chỉ là 30/30 câu công khai đã kiểm thử, không phải độ chính xác của hỏi tự do. Bên **Chất lượng & xuất dữ liệu** đã ghi rõ giới hạn này.
- Sửa lỗi trước đây: câu `CFO (lưu chuyển tiền thuần từ hoạt động kinh doanh) của C007 năm 2025 là bao nhiêu triệu VND?` nay trả lời **−20.564 triệu VND**, có evidence nguồn, thay vì câu hướng dẫn chung.
- Nếu câu hỏi chưa hỗ trợ hoặc thiếu dữ liệu, hệ thống hiển thị cảnh báo riêng, không hiển thị thanh 50% confidence giả.
- Các logic Numeric QA/benchmark/cảnh báo không bị thay đổi trong cập nhật giao diện này.

## Phiên bản Equal14 v1.1

Trên màn hình **Cảnh báo & truy vết**: RuleScore là **số rule kích hoạt / 14**; mỗi rule đều đóng góp `1/14`, không còn hiển thị trọng số riêng. Ngưỡng CRITICAL bằng **0,68**. Chi tiết **8 điều kiện phục hồi** (đang là đề xuất) được hiển thị để kiểm tra. What-if chỉ dùng 7 rule proxy nên không được so trực tiếp với Risk Score đầy đủ. Xem `docs/ALERT_RULES.md`.
