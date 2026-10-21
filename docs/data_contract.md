# Data Contract — UniSearch AI

Hợp đồng dữ liệu: dữ liệu nào bot được phép đọc, thang điểm hợp lệ, và những gì **không thể biết**.
Quality gate thực thi hợp đồng này nằm ở [`utils/data_quality.py`](../utils/data_quality.py).

## 1. Nguồn và bảng

| Bảng SQLite | Nguồn | Vai trò | Bot được đọc? |
|---|---|---|---|
| `diem_chuan_verified` | `data/data_diem_chuan_verified.csv` (từ Excel điểm chuẩn 2025 qua `etl_xlsx_to_db.py` + quality gate) | Điểm chuẩn có cấu trúc | Có |
| `diem_chuan_quarantine` | Dòng bị loại bởi gate | Để rà soát thủ công | **Không** |
| `dats_master` | Đề án tuyển sinh (DATS) 2024/2025/2026 dạng văn bản | Phương thức, học phí, chỉ tiêu (văn bản tự do) | Có (qua chunk theo câu hỏi) |
| `db_metadata` | ETL | `verified_rows`, `quarantine_rows`, `verified_latest_year` | Có (hiển thị ngày dữ liệu) |

## 2. Mỗi trường một cách xét tuyển và một thang điểm

Trộn các thang với nhau làm "Top điểm cao nhất" vô nghĩa. Mỗi dòng sạch luôn có `method_group` và `score_scale`.

| `method_group` | Ý nghĩa | Thang hợp lệ | Ghi chú |
|---|---|---|---|
| `thpt` | Điểm thi tốt nghiệp THPT | 30 (tới 40 với ngành năng khiếu nhân hệ số) | Thang so sánh chéo trường được |
| `hoc_ba` | Xét học bạ | 30 (một số trường quy về 10) | Không so với `thpt` |
| `dgnl_hn` | ĐGNL ĐHQG Hà Nội | 150 | Nhiều sheet ghi nhãn này nhưng chứa điểm đã quy về 30 → gắn `SCALE_INFERRED` |
| `dgnl_hcm` | ĐGNL ĐHQG TPHCM | 1200 | Tương tự |
| `dgnl_sphn` | ĐGNL ĐH Sư phạm HN | ≈30 | Kỳ thi **khác** ĐGNL ĐHQG HN |
| `tu_duy` | Đánh giá tư duy ĐH Bách khoa HN | 100 | |
| `chung_chi` | IELTS/SAT/... | không đồng nhất (`mixed`) | Không dùng để xếp hạng |
| `ket_hop`, `thi_rieng`, `xt_thang`, `xt_som` | Phương thức riêng của trường | tuỳ trường | Không xếp hạng chéo trường |
| `khac` | Không xác định phương thức | — | **Quarantine** (`UNKNOWN_METHOD`) |

**Quy tắc bắt buộc với bot:** khi nêu điểm phải kèm phương thức và thang; chỉ xếp hạng chéo trường trong cùng `method_group` và cùng `score_scale` (mặc định `thpt`, thang 30).

## 3. Chính sách chất lượng

| Tình huống | Xử lý | Cờ / lý do |
|---|---|---|
| Điểm mất dấu thập phân (`250267`) và **chỉ có đúng một** cách chia hợp lệ | Khôi phục (`25.03`), giữ bản gốc ở `Điểm chuẩn_raw` | `RECOVERED_DECIMAL` |
| Điểm ngoài thang tự nhiên nhưng đúng dạng quen thuộc (vd. 24.5 ở sheet ĐGNL) | Gắn thang đã suy ra | `SCALE_INFERRED` |
| Số nhỏ ngoài thang (vd. 101 học bạ) | **Không đoán** → quarantine | `OUT_OF_RANGE` |
| Có nhiều cách chia hợp lệ | Quarantine | `AMBIGUOUS_DECIMAL` |
| Thiếu điểm / ≤ 0 | Quarantine | `MISSING_SCORE` |
| Không rõ phương thức (sheet `Sheet1`) | Quarantine | `UNKNOWN_METHOD` |
| Trùng khoá và **cùng điểm** | Giữ một dòng | — |
| Trùng khoá nhưng **khác điểm** | Quarantine cả hai | `CONFLICT_DUPLICATE_KEY` |
| Cùng trường nhiều cách viết | Gộp về một `school_id` (giữ phân biệt cơ sở/miền) | — |

Khoá trùng: `school_id + Mã ngành + Tên ngành + method_group + Tổ hợp môn + Ghi chú`.
Riêng `chung_chi` không xét mâu thuẫn (một ngành có nhiều ngưỡng chứng chỉ hợp lệ).

Số liệu lần chạy gần nhất nằm ở `data/quality_report.json`.

## 4. Những điều KHÔNG THỂ BIẾT (bot phải nói rõ, không được bịa)

- **Chỉ tiêu** hầu như trống trong bảng điểm chuẩn; chỉ có thể lấy từ văn bản DATS.
- **Năm có điểm chuẩn đã kiểm chứng: chỉ 2025.** Không có xu hướng nhiều năm từ bảng này.
- **Gán nhầm trường ở nguồn:** `SCHOOL_CODE_MAP` ánh xạ nhiều mã file về cùng một trường (vd. HEH/KHA/KQH → Kinh tế Quốc dân); một số file có thể chứa dữ liệu của trường khác (ví dụ nội dung giống Hải Phòng nằm trong "Mỹ thuật Việt Nam"). Cần chủ dữ liệu đối chiếu.
- **Tên mơ hồ** ("Bách khoa", "Kinh tế") không được tự đoán: bot hỏi lại.
- **DATS PDF 2024/2025:** `etl_pdf_to_db.py` giới hạn 60 000 ký tự/trường; 43/141 văn bản đang chạm trần nên có thể thiếu phần cuối. Cần chạy lại từ PDF gốc (không có trong repo) để sửa. DATS 2026 đã lưu đầy đủ.

## 5. Chủ sở hữu và quy trình

| Hạng mục | Chủ sở hữu | Khi nào |
|---|---|---|
| Rà soát `diem_chuan_quarantine` | Người phụ trách dữ liệu (cần chỉ định) | Sau mỗi lần chạy ETL |
| Cập nhật `SCHOOL_CODE_MAP` / alias | Người phụ trách dữ liệu | Khi thêm trường |
| Quality gate + test | Dev backend | Mỗi PR (`tests/test_data_quality.py`) |

Quy trình nạp dữ liệu:

```bash
python etl_xlsx_to_db.py              # Excel -> raw CSV -> quality gate -> verified / quarantine / report
python etl_2026_to_db.py              # DATS 2026 (đầy đủ, cập nhật cả master)
python scripts/migrate_csv_to_sqlite.py   # nạp SQLite + db_metadata
```
