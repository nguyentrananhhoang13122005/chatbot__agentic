# 🎓 UniSearch AI — Chatbot Tư Vấn Tuyển Sinh Đại Học

[![Tests](https://github.com/nguyentrananhhoang13122005/chatbot__agentic/actions/workflows/test.yml/badge.svg)](https://github.com/nguyentrananhhoang13122005/chatbot__agentic/actions/workflows/test.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)

Hệ thống AI Chatbot thông minh hỗ trợ tra cứu điểm chuẩn, thông tin tuyển sinh và tư vấn hướng nghiệp cho sinh viên Việt Nam.

## ✨ Tính năng chính

- **Tra cứu điểm chuẩn:** Hỏi bằng ngôn ngữ tự nhiên, hỗ trợ viết tắt (HUST, PTIT, NEU...).
- **Hybrid Search Engine:** Kết hợp BM25 + Fuzzy Matching + Token Overlap để tìm trường chính xác tuyệt đối.
- **Unified Analyzer:** Gộp phân loại ý định + trích xuất thực thể + chuẩn hóa query vào 1 lần gọi AI duy nhất.
- **Tư vấn hướng nghiệp:** Upload CV để nhận đánh giá và gợi ý ngành học phù hợp.
- **Gold Test Suite:** Bộ kiểm thử tự động 18 test cases để đảm bảo chất lượng.

## 🏗️ Kiến trúc hệ thống

```
chatbot__agentic/
├── app.py                  # Giao diện Streamlit (UI chính)
├── router.py               # Unified Analyzer (Routing + Entity Extraction)
├── agents/
│   ├── recommender.py      # Agent tra cứu điểm chuẩn (Hybrid Matcher + Pandas Engine)
│   └── counselor.py        # Agent tư vấn hướng nghiệp (CV Analysis)
├── tests/
│   ├── gold_queries.py     # Bộ test cases chuẩn (Gold Test Set)
│   └── run_gold_tests.py   # Test Runner tự động
├── data/                   # ⚠️ THƯ MỤC NÀY KHÔNG ĐƯỢC PUSH LÊN GITHUB (xem bên dưới)
├── clean_data.py           # Script làm sạch dữ liệu OCR
├── etl_pipeline.py         # Pipeline trích xuất dữ liệu từ PDF
├── ocr_extractor.py        # OCR Engine (EasyOCR + PyMuPDF)
├── requirements.txt        # Danh sách thư viện cần cài
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

# Trên Windows (CMD):
.venv\Scripts\activate.bat

# Trên macOS/Linux:
source .venv/bin/activate
```

> **Lưu ý:** Sau khi kích hoạt thành công, bạn sẽ thấy `(.venv)` xuất hiện ở đầu dòng lệnh.

### Bước 3: Cài đặt thư viện

```bash
pip install -r requirements.txt
```

### Bước 4: Cấu hình API Key

```bash
# Copy file template thành file .env thật
cp .env.example .env

# Mở file .env và điền API Key Groq của bạn vào
# (Lấy key miễn phí tại: https://console.groq.com/keys)
```

Nội dung file `.env` sau khi điền:
```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

### Bước 5: Chuẩn bị Dữ liệu

> ⚠️ **QUAN TRỌNG:** Dữ liệu tuyển sinh KHÔNG được đẩy lên GitHub do yêu cầu bảo mật. Bạn cần liên hệ trưởng nhóm để nhận các file sau và đặt vào thư mục `data/`:

```
data/
├── data_tuyensinh_clean.csv        # Database tuyển sinh chính (đã làm sạch)
├── data_diem_chuan_verified.csv    # Database điểm chuẩn đã xác thực
├── DATS_2024/                      # Thư mục PDF gốc năm 2024
└── DATS_2025/                      # Thư mục PDF gốc năm 2025
```

### Bước 6: Chạy ứng dụng

```bash
python -m streamlit run app.py
```

Truy cập trình duyệt tại: `http://localhost:8501`

---

## 🧪 Chạy kiểm thử (Testing)

```bash
# Unit Tests — Chạy offline, KHÔNG cần API key (45 test cases)
python -m pytest tests/test_matcher.py -v

# Unit Tests với Coverage Report
python -m pytest tests/test_matcher.py --cov=agents --cov-report=term-missing -v

# Gold Tests — CẦN API key + data CSV (18 test cases)
python tests/run_gold_tests.py

# Chạy 1 Gold test case cụ thể
python tests/run_gold_tests.py --id S08
```

> **Lưu ý:** CI/CD (GitHub Actions) chỉ chạy **Unit Tests** tự động. Gold Tests cần chạy thủ công vì yêu cầu API key và dữ liệu.

---

## 📝 Quy tắc làm việc nhóm

1. **KHÔNG BAO GIỜ** commit file `.env` hoặc file CSV/PDF dữ liệu lên GitHub.
2. Tạo nhánh riêng (`git checkout -b ten_tinh_nang`) khi phát triển tính năng mới.
3. Tạo Pull Request để review code trước khi merge vào `main`.
4. Chạy `python tests/run_gold_tests.py` sau mỗi lần thay đổi code để đảm bảo không gây lỗi.

---

## 🛠️ Tech Stack

| Thành phần | Công nghệ |
|---|---|
| LLM | Groq API (Llama 3.3 70B) |
| UI | Streamlit |
| Data Engine | Pandas |
| Search | BM25 + Fuzzy Matching (thuần Python) |
| OCR | EasyOCR + PyMuPDF |
| Testing | Gold Test Set (Custom) |
