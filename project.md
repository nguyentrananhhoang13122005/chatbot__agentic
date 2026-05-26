# PRODUCT REQUIREMENTS DOCUMENT (PRD) & BUSINESS ANALYSIS
**Tên dự án:** UniSearch AI — Hệ thống Chatbot Tư vấn Tuyển sinh Đại học (Agentic AI)

---

## 1. TỔNG QUAN DỰ ÁN (EXECUTIVE SUMMARY)
UniSearch AI là một trợ lý ảo thông minh hỗ trợ học sinh lớp 12 trong quá trình tra cứu điểm chuẩn và định hướng chọn ngành, chọn trường. Khác với các hệ thống RAG chatbot truyền thống dễ gặp tình trạng ảo giác (hallucination) với các con số, UniSearch AI ứng dụng kiến trúc **Agentic Workflow** kết hợp với **Hybrid Search Engine** (BM25 + Fuzzy Matching) trên nền tảng cơ sở dữ liệu **SQLite** tốc độ cao. Hệ thống vừa đảm bảo tính chính xác tuyệt đối (100%) khi tra cứu số liệu, vừa có khả năng phân tích năng lực chuyên sâu (đọc CV, tính điểm tổ hợp theo quy chế 2026).

## 2. CHÂN DUNG NGƯỜI DÙNG (USER PERSONAS)
* **Học sinh lớp 12:** Đang cần định hướng ngành nghề, đã có điểm thi nhưng không biết đỗ trường nào, cần biết chi tiết tổ hợp môn lợi thế nhất của bản thân để tối ưu cơ hội trúng tuyển.
* **Phụ huynh:** Cần tra cứu nhanh điểm chuẩn, theo dõi lịch sử tra cứu của con cái thông qua tính năng lưu lịch sử (History/Session).

## 3. CÁC KỊCH BẢN SỬ DỤNG CHÍNH (USE CASES)

### Use case 1: Tra cứu thông tin tuyển sinh cơ bản (Zero-Hallucination Q&A)
* **User Story:** "Tôi muốn hỏi điểm chuẩn năm 2025 của ngành Khoa học máy tính trường Đại học Bách Khoa Hà Nội."
* **Hành động của hệ thống:** Unified Analyzer (Router) nhận diện ý định và trích xuất thực thể (Tên trường, Ngành, Năm) -> Chuyển đến Agent Khuyến nghị -> Hybrid Matcher tìm kiếm trong SQLite DB (tốc độ O(log N)) -> Trả ra con số chính xác tuyệt đối theo thời gian thực (Streaming).

### Use case 2: Tính toán Tổ hợp Khối thi & Gợi ý trường đỗ
* **User Story:** "Tôi được Toán 9, Lý 8, Hóa 7.5 và thuộc Khu vực 1. Hãy tính xem tôi có thể đỗ những trường nào."
* **Hành động của hệ thống:** Module Score Calculator tính toán tất cả các tổ hợp (từ A00 đến các khối năng khiếu), áp dụng luật cộng điểm ưu tiên theo Quy chế Bộ GD&ĐT 2026 (giảm trừ nếu >= 22.5), cảnh báo nếu có Điểm Liệt -> Lọc DB các ngành có điểm chuẩn thấp hơn tổng điểm -> Trả về danh sách phù hợp.

### Use case 3: Phân tích CV và Định hướng chuyên sâu (Resume Parsing)
* **User Story:** "Tôi tải file CV hoạt động ngoại khóa của tôi lên, bot hãy phân tích xem tôi hợp với ngành Marketing hay Logistics."
* **Hành động của hệ thống:** Nhận diện có file PDF -> Sử dụng OCR Engine (EasyOCR + PyMuPDF) bóc tách văn bản -> Counselor Agent đánh giá kỹ năng mềm/cứng so với yêu cầu ngành -> Đưa ra nhận xét Ưu/Nhược điểm.

### Use case 4: Quản lý Phiên trò chuyện (Session & Auth Management)
* **User Story:** "Là một người dùng đã đăng nhập, tôi muốn xem lại các trường đại học mình đã hỏi từ tuần trước."
* **Hành động của hệ thống:** Truy xuất DB `chat_history.db` -> Liệt kê lịch sử chat theo User ID, hỗ trợ bookmark, tự động sinh tiêu đề (Auto-title) và quản lý phiên.

## 4. YÊU CẦU CHỨC NĂNG (FUNCTIONAL REQUIREMENTS)
1. **Module Input:** Nhận văn bản và tài liệu đính kèm (PDF, Ảnh học bạ).
2. **Unified Analyzer:** Sử dụng LLM để gộp bước phân loại ý định (Intent) và trích xuất thực thể (NER) vào 1 lần gọi API duy nhất.
3. **Data Engine:** Cơ sở dữ liệu SQLite đa bảng (`admissions.db`, `chat_history.db`, `auth.db`) có Indexing cho phép truy vấn tốc độ cao và cô lập dữ liệu (Data Isolation).
4. **Authentication:** Đăng nhập/Đăng ký tài khoản, phân quyền lưu trữ lịch sử cá nhân hóa.
5. **Score Calculator:** Thuật toán tính tổ hợp môn, tính điểm ưu tiên (KV, UT) và chặn điểm liệt theo chuẩn Bộ GD&ĐT 2026.
6. **Giao diện UI/UX:** Cung cấp trải nghiệm mượt mà với hiệu ứng Streaming text, hệ thống màu sắc theo Design System (Riso) và tích hợp Dark Mode.

## 5. YÊU CẦU PHI CHỨC NĂNG (NON-FUNCTIONAL)
* **Độ chính xác (Accuracy):** Không được phép ảo giác (0% Hallucination) với các dữ liệu điểm chuẩn. Hệ thống phải truy xuất trực tiếp 1-1 từ Database.
* **Độ ổn định (Resilience):** Hệ thống tích hợp Fallback Model Chain (chuyển đổi mô hình LLM tự động nếu API OpenRouter gặp sự cố).
* **Hiệu suất (Performance):** Truy xuất CSDL điểm chuẩn đạt tốc độ mili-giây (ms) thông qua SQLite Indexing. Giao diện Streaming phản hồi ngay lập tức dưới 1s.
* **Bảo mật (Security):** Mật khẩu người dùng được mã hóa. File `.env` và cơ sở dữ liệu `auth.db` được bảo vệ độc lập, không public mã nguồn nhạy cảm.

## 6. TIÊU CHUẨN KIỂM THỬ (TESTING & QUALITY ASSURANCE)
* **Unit Tests:** Đạt độ phủ mã (Code Coverage) > 90% cho các module trọng yếu (như Auth).
* **Gold Test Suite:** Có riêng bộ test cases chuẩn (Gold Tests) để kiểm thử độc lập độ chính xác của LLM Pipeline.