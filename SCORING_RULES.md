# TÀI LIỆU QUY TẮC VÀ CƠ CHẾ TÍNH ĐIỂM (SCORING RULES)
**Dự án:** Agentic University Admission Chatbot
**Cập nhật lần cuối:** 2026-05-21

Tài liệu này mô tả chi tiết các quy tắc nghiệp vụ, công thức toán học và cơ chế nội suy ẩn được sử dụng trong lõi tính toán (`score_calculator.py` và `match_maker.py`) của dự án. Mọi logic đều được thiết kế tuân thủ nghiêm ngặt **Quy chế Tuyển sinh Đại học hiện hành của Bộ GD&ĐT**.

---

## 1. Hệ thống Thang điểm và Bộ lọc
Hệ thống xử lý hai thang điểm chính dựa trên phương thức thi THPT và Học bạ.

- **Thang điểm 30 (Tiêu chuẩn):** Điểm tối đa 3 môn = 30. Dành cho phần lớn các khối ngành thông thường (Kỹ thuật, Kinh tế, CNTT...).
- **Thang điểm 40 (Nhân hệ số 2):** Điểm tối đa 3 môn + 1 môn nhân đôi = 40. Dành cho các khối ngành đặc thù (Ngôn ngữ, Nghệ thuật, Kiến trúc...).
- **Loại trừ Thang 1200 (ĐGNL):** Hệ thống có bộ lọc cứng `Điểm chuẩn <= 40`. Mọi kết quả có điểm chuẩn > 40 (chủ yếu là phương thức xét Đánh giá năng lực của ĐHQG) sẽ bị loại bỏ khỏi luồng tính toán để tránh sai số so khớp.

---

## 2. Công thức Điểm Ưu Tiên (Priority Bonus)
Hệ thống hỗ trợ cộng điểm ưu tiên Khu vực (KV) và Đối tượng (UT). 
**Lưu ý:** Điểm ưu tiên KHÔNG CỘNG CHẾT mà áp dụng cơ chế "trượt giảm dần" theo quy định của Bộ để đảm bảo công bằng cho nhóm điểm cao.

### 2.1 Đối với Thang điểm 30
- **Tổng thô (Raw Total):** Tổng điểm 3 môn cấu thành tổ hợp.
- **Nếu Tổng thô < 22.5:** `Điểm ƯT thực tế = Điểm ƯT gốc`.
- **Nếu Tổng thô >= 22.5:**
  `Điểm ƯT thực tế = [(30 - Tổng thô) / 7.5] * Điểm ƯT gốc`
- **Điểm tổng (Total 30) = Tổng thô + Điểm ƯT thực tế**

### 2.2 Đối với Thang điểm 40
Điểm ưu tiên phải được nội suy sang thang 40.
- **Tổng thô (Raw 40):** Tổng điểm 3 môn + Điểm môn cao nhất.
- **Mức ƯT tối đa (Thang 40):** `Điểm ƯT gốc * (4/3)`.
- **Nếu Tổng thô < 30:** `Điểm ƯT thực tế = Mức ƯT tối đa (Thang 40)`.
- **Nếu Tổng thô >= 30:**
  `Điểm ƯT thực tế = [(40 - Tổng thô) / 10] * Mức ƯT tối đa (Thang 40)`
- **Điểm tổng (Total 40) = Tổng thô (Raw 40) + Điểm ƯT thực tế**

---

## 3. Cơ chế Nội suy Thang 40 (Rule-based Inference)
Do dữ liệu đầu vào (Database) không có cột phân biệt rạch ròi trường nào dùng thang 30, trường nào dùng thang 40, hệ thống sử dụng **Rule-based Heuristics** để nhận diện:

1. **Dấu hiệu định lượng:** Nếu `Điểm chuẩn > 30` -> Chắc chắn là Thang 40.
2. **Dấu hiệu định tính (Từ khóa):** Nếu `Điểm chuẩn <= 30` nhưng tên ngành học chứa một trong các từ khóa đặc thù:
   - *Nhóm Ngôn ngữ:* `"ngôn ngữ"`, `"sư phạm tiếng"`
   - *Nhóm Nghệ thuật / Kiến trúc:* `"kiến trúc"`, `"mỹ thuật"`, `"thiết kế đồ họa"`, `"thiết kế nội thất"`, `"thiết kế thời trang"`, `"thiết kế mỹ thuật"`, `"thiết kế công nghiệp"`
   - *Nhóm Năng khiếu khác:* `"mầm non"`, `"âm nhạc"`, `"thanh nhạc"`, `"thể dục"`, `"thể thao"`
   -> Hệ thống sẽ kích hoạt cờ `is_scale_40 = True` và áp dụng toán học của Thang 40. 

> *Lưu ý: Các từ khóa đã được cô lập (ví dụ dùng "sư phạm tiếng" thay vì "tiếng") nhằm tránh nhận diện nhầm các ngành học bình thường nhưng được giảng dạy bằng tiếng Anh.*

---

## 4. Cơ chế Đối sánh và Khuyên dùng (Delta Matching)
Sự phù hợp của một ngành học được quyết định bởi chỉ số **Delta (Độ lệch)**:
`Delta = Tổng điểm của thí sinh (cùng thang điểm) - Điểm chuẩn của trường`

- Hệ thống chỉ lấy các trường có **Delta >= -2.0** (Tức là thiếu tối đa 2 điểm so với điểm chuẩn năm ngoái). 
- Thuật toán ưu tiên hiển thị các trường có Delta tiệm cận 0 hoặc dương.

---

## 5. Cơ chế Báo Động Đỏ: Kiểm soát Điểm Liệt (Paralyzing Score)
Theo quy chế, điểm thi `<= 1.0` bị coi là "Điểm liệt".
- Khi tính toán mọi tổ hợp, hệ thống sẽ quét từng môn thành phần. Nếu tồn tại môn `<= 1.0`, tổ hợp đó bị gắn cờ `has_diem_liet = True`.
- **Fail-safe Logic:** Mọi tổ hợp dính điểm liệt sẽ **bị chặn (block) hoàn toàn** khỏi quá trình match Delta. Hệ thống trả về danh sách rỗng (Empty DataFrame) cho tổ hợp này để không tạo ra ảo tưởng "Đỗ đại học" cho thí sinh đã rớt tốt nghiệp.
- Giao diện UI đổi sang trạng thái Báo động Đỏ thẫm kèm cảnh báo rõ ràng.

---

## 6. Tiêu chuẩn Làm tròn Toán học (Rounding Precision)
- Mọi phép tính tổng điểm (`raw_total`, `adjusted_bonus`, `total`, `delta`) đều được áp dụng hàm `round(..., 2)`.
- Hệ thống hỗ trợ tính toán và hiển thị độ chính xác tuyệt đối đến **2 chữ số thập phân** (VD: `27.25`), tuân thủ 100% quy định làm tròn của Bộ GD&ĐT, loại bỏ rủi ro sai số do quy tắc làm tròn chẵn (round-half-to-even) của máy tính.
