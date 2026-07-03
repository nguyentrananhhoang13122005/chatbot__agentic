# PRODUCT REQUIREMENTS DOCUMENT (PRD) & BỐI CẢNH DỰ ÁN
**Tên dự án:** UniSearch AI — Hệ thống AI Phân tích & Gợi ý Tuyển sinh Đại học

---

## 1. TỔNG QUAN DỰ ÁN (EXECUTIVE SUMMARY)
UniSearch AI là hệ thống ứng dụng trí tuệ nhân tạo hỗ trợ học sinh trung học phổ thông trong quá trình xét điểm và định hướng chọn ngành, chọn trường Đại học. Nhằm khắc phục tình trạng ảo giác (hallucination) thường gặp ở các LLM khi xử lý số liệu, UniSearch AI áp dụng kiến trúc tách biệt rõ ràng giữa tầng logic tính toán (tính tổ hợp điểm, cộng điểm ưu tiên theo quy chế Bộ GD&ĐT) và tầng tư vấn AI (phân tích cơ hội đỗ). Hệ thống vận hành dựa trên kiến trúc dữ liệu lai (Hybrid) kết hợp truy vấn SQLite tốc độ cao và In-memory Pandas DataFrames, đi kèm công cụ tìm kiếm kết hợp (BM25 + Fuzzy Matching) để hiểu chính xác truy vấn trường học của người dùng.

## 2. CHÂN DUNG NGƯỜI DÙNG (USER PERSONAS)
* **Học sinh THPT:** Đã có điểm thi (hoặc điểm trung bình học bạ) nhưng gặp khó khăn trong việc định vị bản thân. Cần một công cụ tự động tính điểm xét tuyển có tính ưu tiên, gợi ý tổ hợp có lợi thế nhất, và tra cứu/so sánh với điểm chuẩn các năm trước.
* **Phụ huynh:** Cần công cụ tra cứu nhanh thông tin tuyển sinh, đề án tuyển sinh, và học phí của các trường đại học thay vì tra cứu thủ công qua nhiều trang web khác nhau.

## 3. CÁC KỊCH BẢN SỬ DỤNG CHÍNH (USE CASES)

### Use case 1: Tính toán Tổ hợp Khối thi & Điểm ưu tiên
* **Hành động:** Người dùng nhập điểm thi THPT, điểm học bạ, điểm ngoại ngữ (IELTS/TOEFL) và năng khiếu qua giao diện Streamlit (hoặc custom component `transcript_editor`). Hệ thống tính toán mọi tổ hợp, áp dụng thuật toán cộng điểm ưu tiên tự động giảm trừ nếu tổng điểm >= 22.5 (chuẩn quy chế 2026), và cảnh báo các tổ hợp có điểm liệt hoặc không đủ điều kiện tối thiểu. Sau đó hiển thị danh sách các tổ hợp điểm cao nhất.

### Use case 2: Đánh giá cơ hội trúng tuyển (Match Maker)
* **Hành động:** Hệ thống đối chiếu điểm tổ hợp mạnh nhất với CSDL điểm chuẩn. Với tính năng xét điểm thi, hệ thống sử dụng truy vấn SQLite tốc độ cao; với xét học bạ, sử dụng Pandas filtering. Kết quả được phân thành 3 nhóm cơ hội: An Toàn, Vừa Sức, và Thử Thách dựa trên độ chênh lệch (Delta). Cuối cùng, LLM tạo luồng (streaming) nhận xét chi tiết về cơ hội đỗ và giải thích số liệu.

### Use case 3: Tra cứu Đề án Tuyển sinh bằng AI (Recommender)
* **Hành động:** Người dùng đặt câu hỏi tự nhiên (vd: "Điểm chuẩn Bách Khoa ngành IT là bao nhiêu?"). Recommender Agent sử dụng Hybrid Matcher (BM25, Token Overlap) để map đúng trường. Sau đó truy xuất văn bản từ Đề án Tuyển sinh (DATS) hoặc Cơ sở dữ liệu cấu trúc (Verified DB) và nhúng vào ngữ cảnh cho LLM. LLM sẽ trả lời chính xác dựa trên tài liệu, không được phép suy diễn.

## 4. KIẾN TRÚC & YÊU CẦU CHỨC NĂNG (ARCHITECTURE & FUNCTIONAL REQUIREMENTS)
1. **Frontend (Streamlit):** Cung cấp UI trực quan tại `ui/pages/`. Cho phép nhập điểm chi tiết, quản lý phiên chat (`chat_db.py`), và hiển thị phân tích. (Đã tích hợp xác thực qua `auth.py`).
2. **Backend API (FastAPI):** Expose REST endpoints tại `api/routers/` (mặc dù UI nội bộ hiện tại có thể gọi trực tiếp hàm Python để tối ưu tốc độ, API vẫn đóng vai trò quan trọng cho tích hợp ngoại vi).
3. **Core Agents (`agents/`):**
   - `match_maker.py`: Tính toán Delta, phân lớp nhóm cơ hội (Tier), và sinh nhận xét tổng quan.
   - `recommender.py`: Đóng vai trò search engine, trích xuất chunk dữ liệu (Structural & Recursive chunking) từ DATS và gọi LLM trả lời câu hỏi QA.
   - `counselor.py`: Hỗ trợ phân tích thế mạnh dựa trên học bạ.
4. **Data Engine (`data/` & `utils/`):** 
   - **Hybrid Database:** Sử dụng SQLite (`admissions.db`) cho tra cứu điểm thi, kết hợp với Pandas DataFrames (load file CSV) cho các phương thức khác.
   - **ETL Pipelines (`etl_pdf_to_db.py`):** Xử lý offline các file PDF Đề án tuyển sinh. Sử dụng `PyMuPDF` để lấy text và `EasyOCR` như giải pháp dự phòng cho PDF scan.

## 5. YÊU CẦU PHI CHỨC NĂNG (NON-FUNCTIONAL)
* **Độ chính xác (Accuracy):** Không được phép ảo giác (0% Hallucination). Tầng Data Logic cung cấp dữ liệu cứng (hard-data), LLM chỉ làm nhiệm vụ tổng hợp và diễn đạt lại text.
* **Smart Source Routing:** Hệ thống Recommender phải biết định tuyến câu hỏi: câu hỏi về học phí/phương thức sẽ lấy từ DATS; câu hỏi so sánh điểm chuẩn lấy từ Verified DB.
* **Tối ưu Hiệu suất:** Áp dụng kiến trúc Pipeline SQLite để khắc phục rào cản OOM (Out Of Memory) của pandas DataFrame khi tra cứu danh mục quy mô lớn. 
* **Quản lý lịch sử:** Chat history và lịch sử tra cứu trường được lưu trữ bền vững vào `chat_history.db`.

## 6. THỰC TRẠNG HIỆN TẠI VÀ ĐỊNH HƯỚNG PHÁT TRIỂN
* **Thực trạng OCR:** Hiện tại OCR (EasyOCR/PyMuPDF) chỉ được sử dụng ở tầng **Offline ETL Pipelines** để parse Đề án Tuyển Sinh (DATS) của các trường đại học thành dữ liệu text cho LLM. Chưa có tính năng "Upload ảnh học bạ để AI đọc điểm" trên UI (người dùng đang tự nhập qua form UI).
* **Thực trạng Database:** Đang trong quá trình chuyển đổi (migration) từ Full-Pandas In-Memory sang SQLite. Các luồng `exam-only` đã chạy qua SQLite, trong khi luồng `transcript` và `mixed` vẫn sử dụng fallback Pandas legacy (`_find_top_k_schools_legacy`).
* **Định hướng:** Hoàn thiện giao diện Upload ảnh/PDF học bạ; và hoàn thiện đồng bộ 100% tầng truy vấn điểm chuẩn sang SQLite để giảm thiểu RAM.