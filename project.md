# PRODUCT REQUIREMENTS DOCUMENT (PRD) & BUSINESS ANALYSIS
**Tên dự án:** UniSearch AI — Hệ thống AI Phân tích & Gợi ý Tuyển sinh Đại học

---

## 1. TỔNG QUAN DỰ ÁN (EXECUTIVE SUMMARY)
UniSearch AI là một hệ thống ứng dụng trí tuệ nhân tạo (Agentic AI) hỗ trợ học sinh lớp 12 trong quá trình xét điểm và định hướng chọn ngành, chọn trường. Khác với các hệ thống AI thông thường dễ gặp tình trạng ảo giác (hallucination) với các con số, UniSearch AI tách biệt tầng tính toán và tầng AI: kết hợp **Hybrid Search Engine** (BM25 + Fuzzy Matching) trên nền tảng **SQLite** tốc độ cao cùng **OCR Engine** để đọc học bạ. Hệ thống đảm bảo tính chính xác tuyệt đối (100%) khi áp dụng quy chế cộng điểm ưu tiên 2026 của Bộ GD&ĐT, đồng thời dùng LLM để phân tích và đánh giá cơ hội đỗ của học sinh vào các trường đại học một cách chi tiết.

## 2. CHÂN DUNG NGƯỜI DÙNG (USER PERSONAS)
* **Học sinh lớp 12:** Đã có điểm thi (hoặc học bạ) nhưng không biết với mức điểm đó có thể đỗ những trường nào, cần một công cụ tự động tính điểm tổ hợp lợi thế nhất và tra cứu so sánh với điểm chuẩn các năm trước.
* **Phụ huynh:** Cần tra cứu nhanh, kiểm tra xem con cái có cơ hội đỗ vào trường mong muốn hay không mà không cần phải tự mày mò các bảng điểm chuẩn khổng lồ.

## 3. CÁC KỊCH BẢN SỬ DỤNG CHÍNH (USE CASES)

### Use case 1: Tính toán Tổ hợp Khối thi & Điểm ưu tiên
* **User Story:** "Tôi được Toán 9, Lý 8, Hóa 7.5 và thuộc Khu vực 1. Hãy tính xem tôi được tổng cộng bao nhiêu điểm và có lợi thế nhất ở tổ hợp nào."
* **Hành động của hệ thống:** Module `Score Calculator` tiếp nhận điểm, tự động tính toán tất cả các tổ hợp (từ A00 đến các khối năng khiếu), áp dụng luật cộng điểm ưu tiên theo Quy chế Bộ GD&ĐT 2026 (giảm trừ nếu >= 22.5), cảnh báo nếu có Điểm Liệt. Sau đó hiển thị danh sách 3 tổ hợp cao điểm nhất của học sinh.

### Use case 2: Đánh giá cơ hội trúng tuyển (Match Maker)
* **User Story:** "Với điểm tổ hợp A00 của tôi là 25.5, tôi có thể đỗ ngành Khoa học Máy tính ở những trường nào tại Hà Nội?"
* **Hành động của hệ thống:** Sau khi tính điểm, hệ thống đối chiếu với CSDL SQLite điểm chuẩn của các trường. Tính toán khoảng cách (Delta) giữa điểm của học sinh và điểm chuẩn năm trước, phân loại vào các nhóm cơ hội (Safe - An toàn, Target - Mục tiêu, Reach - Thử thách). LLM sau đó sẽ viết một bản phân tích chi tiết giải thích cho học sinh hiểu về cơ hội của mình.

### Use case 3: Tự động trích xuất điểm Học bạ bằng AI (OCR)
* **User Story:** "Tôi có ảnh chụp học bạ hoặc file PDF bảng điểm, hệ thống có thể tự đọc điểm thay vì tôi phải gõ tay từng môn không?"
* **Hành động của hệ thống:** Nhận diện có file ảnh/PDF -> Sử dụng OCR Engine (EasyOCR kết hợp xử lý ảnh OpenCV) bóc tách văn bản -> Sử dụng Counselor Agent (LLM) để dọn dẹp các ký tự OCR rác, map tên môn học bị lỗi font về chuẩn và trích xuất điểm các môn một cách tự động -> Đưa dữ liệu vào máy tính điểm.

## 4. YÊU CẦU CHỨC NĂNG (FUNCTIONAL REQUIREMENTS)
1. **Module Input:** Form nhập điểm thủ công trực quan, hỗ trợ điểm thi THPT, Chứng chỉ IELTS/TOEFL, điểm học bạ, và các môn năng khiếu. Hỗ trợ tính năng upload file ảnh/PDF để AI tự đọc điểm.
2. **Score Calculator:** Thuật toán tính tổ hợp môn, tính điểm ưu tiên (Khu vực, Đối tượng) và chặn điểm liệt tuân thủ nghiêm ngặt chuẩn quy định tuyển sinh của Bộ GD&ĐT (bao gồm công thức giảm trừ ưu tiên cho mức điểm cao).
3. **Data Engine:** Cơ sở dữ liệu SQLite (`admissions.db`) được tối ưu hóa Indexing cho phép truy vấn tốc độ cao (millisecond), tiết kiệm RAM so với việc load toàn bộ pandas DataFrame trên server.
4. **Admission Evaluator:** Thuật toán so sánh, xếp hạng các trường đại học dựa trên điểm số của người dùng, lọc theo tỉnh thành/ngành học.
5. **Giao diện UI/UX:** Cung cấp trải nghiệm mượt mà với Streamlit, hiển thị bảng dữ liệu rõ ràng, có hiệu ứng Streaming text khi AI đưa ra nhận xét, và hệ thống Dark/Light mode chuẩn mực.

## 5. YÊU CẦU PHI CHỨC NĂNG (NON-FUNCTIONAL)
* **Độ chính xác (Accuracy):** Không được phép ảo giác (0% Hallucination) với các con số điểm thi và điểm chuẩn. Tầng Data Logic và tầng LLM phải tách biệt hoàn toàn. AI chỉ đóng vai trò "đọc" dữ liệu chuẩn từ DB để nhận xét, không được tự suy đoán điểm chuẩn.
* **Độ ổn định (Resilience):** Hệ thống OCR và API LLM phải có khả năng Retry tự động khi gặp lỗi kết nối (sử dụng thư viện `tenacity`).
* **Hiệu suất (Performance):** Quá trình tra cứu và tính toán tổ hợp phải diễn ra ngay lập tức dưới 1 giây. Việc xử lý OCR hình ảnh được tối ưu bằng OpenCV để giảm tải trước khi đưa vào mô hình nhận diện.
* **Tối ưu Server Deploy:** Docker image sử dụng bản PyTorch CPU-only để tiết kiệm dung lượng, giới hạn RAM chạy trong `docker-compose.yml` để chống sập server (OOM).

## 6. TIÊU CHUẨN KIỂM THỬ (TESTING & QUALITY ASSURANCE)
* **Unit Tests (Pytest):** Đảm bảo tính đúng đắn 100% của các bộ công cụ tính toán điểm ưu tiên, lọc tổ hợp. Bất kỳ sự thay đổi nào về công thức của Bộ GD&ĐT đều phải được cập nhật test case trước (TDD).
* **Cross-browser Compatibility:** Giao diện Streamlit hoạt động hoàn hảo trên cả trình duyệt Desktop và Mobile, hỗ trợ dark-mode native.