# 🎓 UniSearch AI — Hệ thống AI Phân tích Xét điểm & Gợi ý Tuyển sinh Đại học

[![Tests](https://github.com/nguyentrananhhoang13122005/chatbot__agentic/actions/workflows/test.yml/badge.svg)](https://github.com/nguyentrananhhoang13122005/chatbot__agentic/actions/workflows/test.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)

Hệ thống AI thông minh hỗ trợ phân tích điểm thi, tính toán tổ hợp, đọc hiểu học bạ bằng OCR và tư vấn trường đại học phù hợp cho thí sinh Việt Nam. Hệ thống tập trung tối đa vào độ chính xác của dữ liệu và ứng dụng trí tuệ nhân tạo để đưa ra các gợi ý an toàn/thử thách cho học sinh.

## ✨ Tính năng chính

- **Tính toán tổ hợp & Điểm ưu tiên:** Tự động tính điểm tổ hợp mạnh nhất, bao gồm cả điểm cộng khu vực, đối tượng theo quy chế tuyển sinh mới nhất (2026) của Bộ GD&ĐT.
- **Phân tích Học bạ bằng AI (OCR):** Tải file PDF hoặc ảnh học bạ lên, AI sẽ sử dụng EasyOCR + LLM để tự động nhận diện điểm số các môn và chuyển thành bảng dữ liệu cấu trúc.
- **Hybrid Search Engine:** Kết hợp thuật toán BM25, Fuzzy Matching và Token Overlap giúp tra cứu và đối chiếu trường chính xác tuyệt đối mà không gặp tình trạng ảo giác (zero-hallucination).
- **Match Maker & Admission Evaluator:** Đánh giá độ chênh lệch giữa điểm của thí sinh và điểm chuẩn các năm trước, từ đó phân loại cơ hội trúng tuyển thành các nhóm (Safe, Target, Reach).
- **Streaming Response:** Trải nghiệm phản hồi phân tích điểm thời gian thực mượt mà với `st.write_stream()`.
- **Gold Test Suite:** Bộ kiểm thử tự động với hàng loạt test cases để đảm bảo tính chính xác của các công thức tính toán.

## 🏗️ Kiến trúc hệ thống

```
chatbot__agentic/
├── app.py                  # Giao diện chính Streamlit
├── core/
│   ├── score_calculator.py # Logic tính điểm, cộng điểm ưu tiên theo quy chế 2026
│   └── query_processor.py  # Xử lý các logic AI và truy vấn dữ liệu
├── agents/
│   ├── recommender.py      # Module tra cứu điểm chuẩn (Hybrid Matcher + SQLite)
│   ├── counselor.py        # Module OCR và Parser trích xuất điểm học bạ
│   └── match_maker.py      # Đánh giá cơ hội trúng tuyển dựa trên độ chênh lệch điểm
├── tests/
│   ├── gold_queries.py     # Bộ test cases chuẩn (Gold Test Set)
│   └── run_gold_tests.py   # Test Runner tự động
├── data/                   # ⚠️ THƯ MỤC CƠ SỞ DỮ LIỆU (Chứa SQLite và CSV)
├── etl_pipeline.py         # Pipeline trích xuất dữ liệu từ PDF Đề án tuyển sinh
├── requirements.txt        # Danh sách thư viện cần cài
├── docker-compose.yml      # Cấu hình deploy bằng Docker
├── Dockerfile              # Docker image build file được tối ưu hóa cho môi trường Production
├── .env.example            # Template cấu hình API Key
└── .gitignore              # Danh sách file bị chặn không push lên GitHub
```

---

## 🚀 Hướng dẫn Cài đặt (Dành cho Thành viên Nhóm)

### Bước 1: Clone code về máy

```bash
git clone https://github.com/nguyentrananhhoang13122005/chatbot__agentic.git
cd chatbot__agentic
```

### Bước 2: Tạo môi trường ảo (Virtual Environment)

```bash
# Tạo môi trường ảo
python -m venv .venv

# Kích hoạt môi trường ảo
# Trên Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Trên macOS/Linux:
source .venv/bin/activate
```

### Bước 3: Cài đặt thư viện

```bash
pip install -r requirements.txt
```

### Bước 4: Cấu hình API Key

```bash
# Copy file template thành file .env thật
cp .env.example .env

# Mở file .env và điền OpenRouter API Key của bạn
# (Lấy key tại: https://openrouter.ai/keys)
```

Nội dung file `.env` sau khi điền:
```
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
```

### Bước 5: Chuẩn bị Dữ liệu

> ⚠️ **QUAN TRỌNG:** Cơ sở dữ liệu tuyển sinh KHÔNG được đẩy lên GitHub do yêu cầu bảo mật và dung lượng. Bạn cần liên hệ trưởng nhóm để nhận các file DB và CSV rồi đặt vào thư mục `data/`.

### Bước 6: Chạy ứng dụng

```bash
python -m streamlit run app.py
```
Truy cập trình duyệt tại: `http://localhost:8501`

---

## 🧪 Chạy kiểm thử (Testing)

Dự án sử dụng `pytest` để đảm bảo logic tính toán điểm chuẩn, cộng điểm ưu tiên luôn đạt độ chính xác 100%.

```bash
# Unit Tests — Chạy offline (KHÔNG cần API key)
python -m pytest tests/ -v

# Unit Tests với Coverage Report
python -m pytest tests/ --cov=core --cov=utils --cov-report=term-missing -v
```

> **Lưu ý:** CI/CD (GitHub Actions) sẽ tự động chạy bộ **Unit Tests** mỗi khi có commit mới đẩy lên nhánh `main`.

---

## 📝 Quy tắc làm việc nhóm

1. **KHÔNG BAO GIỜ** commit file `.env`, file SQLite `.db` hoặc file CSV dữ liệu lên GitHub.
2. Tạo nhánh riêng (`git checkout -b ten_tinh_nang`) khi phát triển tính năng mới.
3. Chạy `pytest` sau mỗi lần thay đổi code phần tính điểm để đảm bảo không làm hỏng logic của hệ thống.
4. Ưu tiên sử dụng `sqlite3` thay vì load toàn bộ CSV vào pandas để chống sập RAM (Out of Memory) trên server.

---

## 🛠️ Tech Stack

| Thành phần | Công nghệ |
|---|---|
| AI / LLM | OpenRouter API (`qwen/qwen3-8b` + fallback models) |
| UI Framework | Streamlit |
| Cơ sở dữ liệu | SQLite (Truy vấn tốc độ cao O(log N)) |
| Data Processing | Pandas, Numpy |
| Search Engine | BM25 + Fuzzy Matching (thuần Python) |
| Phân tích Học bạ | EasyOCR + OpenCV + PyMuPDF |
| Infrastructure | Docker, Docker Compose |
| Testing | Pytest |
