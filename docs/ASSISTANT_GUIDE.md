# Financial Analyst Assistant – Hỏi đáp và kiểm thử mẫu

Có **hai cơ chế khác nhau** được trình bày riêng trong `Mô phỏng & trợ lý → Financial Analyst Assistant`:

1. **Hỏi tự do (rule-based)** gọi `finreport.assistant.answer_user_query()`: hiểu một số từ khóa/nhóm chỉ tiêu và tra đúng company-year từ `analysis`. Có thể hỏi CFO, doanh thu, nợ phải trả, biên lợi nhuận, FCF, tỷ số thanh khoản, tăng trưởng, benchmark, rủi ro và một số phép so sánh. Không dùng LLM hoặc gọi API. Trả về câu trả lời, dấu vết file:field:company:year và confidence heuristic cho câu *đã hỗ trợ*.
2. **30 câu QA mẫu BTC** gọi dữ liệu đầu ra từ `finreport.qa.answer_questions()` đã được pipeline tính toán theo `questions_sample.csv`; kiểm thử so với `answer_key_sample.csv` chỉ thực hiện trong `evaluation.evaluate_qa()` sau khi tính toán, không dùng đáp án mẫu làm đầu vào. Cho phép mở từng câu công khai và kiểm tra đáp án, phương pháp, file/trường nguồn.

## Cách hiểu KPI

`Numerical QA Accuracy = 30/30 = 100%` **chỉ là độ chính xác trên 30 câu mẫu công khai**, không đo độ chính xác của trợ lý hỏi tự do và không đại diện test ẩn. Nếu câu hỏi vượt quá phạm vi parser, trợ lý trả **Chưa hỗ trợ** với `confidence=0`, không giả vờ trả lời.

## Các câu demo

- `CFO (lưu chuyển tiền thuần từ hoạt động kinh doanh) của C007 năm 2025 là bao nhiêu triệu VND?` → **-20.564 triệu VND**, từ `cashflow.csv:net_cash_from_operating_activities_vnd_mn:C007:2025`.
- `doanh thu C006 2025`
- `Current Ratio của C007 năm 2025 bằng bao nhiêu?`
- `Free Cash Flow của C004 năm 2025`
- `giải thích rủi ro C007 2025`
- `so sánh C005 2025 với ngành`
- `top 5 rủi ro 2025`
- `Mô tả xu hướng doanh thu và CFO của C002 giai đoạn 2023-2025`

Không yêu cầu trợ lý phân tích pháp luật, dự đoán gian lận, tạo số liệu ngoài Data Pack hoặc giả lập rằng đây là một mô hình ngôn ngữ tổng quát. Confidence heuristic không phải xác suất thống kê đã hiệu chuẩn.
