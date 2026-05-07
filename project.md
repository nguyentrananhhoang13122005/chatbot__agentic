# PROJECT BUSINESS ANALYSIS (BA)
**Tên dự án:** Hệ thống Chatbot Tư vấn Tuyển sinh Đại học (Multi-Agent)

## 1. TỔNG QUAN DỰ ÁN (OVERVIEW)
Xây dựng một trợ lý ảo (Chatbot) thông minh hỗ trợ học sinh lớp 12 trong quá trình chọn trường, chọn ngành thi đại học. Khác với các chatbot RAG thông thường chỉ trả lời dựa trên tài liệu, hệ thống này ứng dụng mô hình **Agentic Routing** (Đa đại lý) để vừa có thể tra cứu thông tin số liệu chính xác (điểm chuẩn, chỉ tiêu), vừa có thể đóng vai chuyên gia tư vấn phân tích hồ sơ năng lực (CV) của học sinh.

## 2. CHÂN DUNG NGƯỜI DÙNG (USER PERSONAS)
*   **Học sinh lớp 12:** Đang mông lung về chọn ngành, đã có điểm thi nhưng không biết đỗ trường nào, hoặc có hồ sơ ngoại khóa nhưng không biết hợp văn hóa trường nào.
*   **Phụ huynh (Mở rộng):** Cần tra cứu nhanh mức học phí, điểm chuẩn các trường định hướng cho con.

## 3. CÁC KỊCH BẢN SỬ DỤNG CHÍNH (USE CASES / USER STORIES)

### Use case 1: Tra cứu thông tin tuyển sinh cơ bản (Q&A)
*   **User Story:** "Là một học sinh, tôi muốn hỏi điểm chuẩn năm 2023 của ngành Khoa học máy tính trường Bách Khoa để xem mình có với tới không."
*   **Hành động của Bot:** Router phân loại câu hỏi -> Chuyển đến Agent Khuyến nghị (RAG) -> Truy xuất Database -> Trả ra con số chính xác.

### Use case 2: Gợi ý trường dựa trên điểm số (Recommendation)
*   **User Story:** "Là một học sinh được 24 điểm khối A00, tôi muốn biết mình có thể đậu những ngành nào ở trường ĐHQG HN."
*   **Hành động của Bot:** Nhận diện điểm số và khối thi trong câu nói -> Lọc trong DB các ngành khối A00 có điểm sàn <= 24 -> Liệt kê danh sách phù hợp.

### Use case 3: Phân tích CV và Định hướng chuyên sâu (Resume Parsing & Counseling)
*   **User Story:** "Là một học sinh năng nổ hoạt động ngoại khóa, tôi tải file CV của tôi lên và muốn bot tư vấn xem tôi hợp với ngành Marketing hay ngành Quản trị nhân sự hơn."
*   **Hành động của Bot:** Router nhận diện có file đính kèm -> Chuyển file cho Agent Tư vấn -> Đọc file PDF trích xuất text -> LLM đánh giá kỹ năng mềm/cứng trong CV so với yêu cầu của ngành -> Đưa ra nhận xét Ưu/Nhược điểm và lời khuyên.

## 4. YÊU CẦU CHỨC NĂNG (FUNCTIONAL REQUIREMENTS)
1. **Module Input:** Nhận được cả Text (tin nhắn) và File (PDF CV).
2. **Module Routing:** Tự động phân loại ý định người dùng (Intent Classification).
3. **Module DB Query:** Kết nối và truy vấn được dữ liệu từ file CSDL (CSV/Excel).
4. **Module Document Parser:** Có khả năng đọc và hiểu chữ cái có trong file PDF.
5. **Giao diện UI:** Giao diện trực quan tích hợp khung chat và nút upload file (Streamlit).

## 5. YÊU CẦU PHI CHỨC NĂNG (NON-FUNCTIONAL)
*   **Độ chính xác:** Dữ liệu tra cứu điểm chuẩn phải chính xác 100%, không được ảo giác (Hallucination).
*   **Thời gian phản hồi:** Dưới 5 giây cho câu hỏi thường và dưới 15 giây cho tác vụ phân tích file CV.