# 🎓 UniSearch AI — Hệ thống AI Phân tích Xét điểm & Gợi ý Tuyển sinh Đại học

[![Tests](https://github.com/nguyentrananhhoang13122005/chatbot__agentic/actions/workflows/test.yml/badge.svg)](https://github.com/nguyentrananhhoang13122005/chatbot__agentic/actions/workflows/test.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)

Hệ thống AI thông minh hỗ trợ phân tích điểm thi, tính toán tổ hợp, và tư vấn trường đại học phù hợp cho thí sinh Việt Nam. Hệ thống tập trung tối đa vào độ chính xác của dữ liệu (zero-hallucination) bằng cách tách biệt tầng tính toán và tầng AI.

## ✨ Tính năng chính

- **Tính toán tổ hợp & Điểm ưu tiên:** Tự động tính điểm tổ hợp mạnh nhất, bao gồm cả điểm cộng khu vực, đối tượng theo quy chế tuyển sinh mới nhất (2026) của Bộ GD&ĐT.
- **Match Maker & Admission Evaluator:** Đánh giá độ chênh lệch (Delta) giữa điểm của thí sinh và điểm chuẩn các năm trước, phân loại cơ hội trúng tuyển: **An toàn**, **Vừa sức**, hoặc **Thử thách**.
- **Hybrid Search Engine:** Kết hợp thuật toán BM25, Fuzzy Matching và Token Overlap giúp tra cứu trường chính xác tuyệt đối mà không gặp tình trạng ảo giác.
- **Recommender Agent:** Tra cứu thông tin đề án tuyển sinh (DATS), điểm chuẩn, phương thức xét tuyển, học phí... qua giao diện chat tự nhiên.
- **Streaming Response:** Trải nghiệm phản hồi phân tích điểm thời gian thực mượt mà với SSE (Server-Sent Events).
- **Gold Test Suite:** Bộ kiểm thử tự động với hàng loạt test cases để đảm bảo tính chính xác của các công thức tính toán.

> **Lưu ý:** OCR (EasyOCR + PyMuPDF) chỉ được dùng ở các **pipeline ETL offline** (`etl_pdf_to_db.py`) để trích xuất dữ liệu từ PDF Đề án tuyển sinh. Tính năng này không chạy trên production server.

## 🏗️ Kiến trúc hệ thống

```
chatbot__agentic/
├── main.py                 # Entry point FastAPI backend
├── api/
│   ├── routers/            # API endpoints (scores, schools)
│   └── schemas/            # Pydantic request/response models
├── frontend/               # Next.js frontend (React + Tailwind + shadcn/ui)
│   ├── app/                # App Router pages (score, chat)
│   ├── components/         # Reusable UI components
│   ├── hooks/              # React hooks (useScoreForm)
│   ├── lib/                # Utilities (SSE client, validators, API client)
│   └── types/              # TypeScript type definitions
├── agents/
│   ├── recommender.py      # Tra cứu điểm chuẩn (Hybrid Matcher + SQLite)
│   ├── counselor.py        # Phân tích thế mạnh dựa trên học bạ
│   └── match_maker.py      # Đánh giá cơ hội trúng tuyển (Delta scoring)
├── utils/
│   ├── score_calculator.py # Logic tính điểm, cộng điểm ưu tiên theo quy chế 2026
│   ├── admission_matcher.py # SQLite exam-only matching pipeline
│   └── ...                 # Validators, normalizers, models
├── core/
│   └── query_processor.py  # Xử lý logic AI và routing truy vấn
├── data/                   # ⚠️ CSDL (SQLite + CSV, không push lên Git)
├── tests/                  # Pytest test suite
├── etl_*.py                # Offline ETL pipelines (PDF/XLSX → DB)
├── requirements.txt        # Python dependencies
├── Dockerfile              # Production image (FastAPI only, no OCR)
└── docker-compose.yml      # Docker deployment config
```

---

## 🚀 Hướng dẫn Cài đặt

### Bước 1: Clone code về máy

```bash
git clone https://github.com/nguyentrananhhoang13122005/chatbot__agentic.git
cd chatbot__agentic
```

### Bước 2: Backend — Python setup

```bash
# Tạo và kích hoạt môi trường ảo
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt
```

### Bước 3: Frontend — Node.js setup

```bash
cd frontend
npm install
cd ..
```

### Bước 4: Cấu hình API Key

```bash
# Copy file template thành file .env thật
cp .env.example .env
```

Mở file `.env` và điền OpenRouter API Key:
```
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
```

### Bước 5: Chuẩn bị Dữ liệu

> ⚠️ **QUAN TRỌNG:** Cơ sở dữ liệu tuyển sinh KHÔNG được đẩy lên GitHub do yêu cầu bảo mật và dung lượng. Liên hệ trưởng nhóm để nhận các file DB và CSV rồi đặt vào thư mục `data/`.

### Bước 6: Chạy ứng dụng

```bash
# Terminal 1 — Backend (FastAPI)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend (Next.js)
cd frontend
npm run dev
```

- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`

---

## 🧪 Chạy kiểm thử (Testing)

```bash
# Unit Tests — Chạy offline (KHÔNG cần API key)
python -m pytest tests/ -v

# Unit Tests với Coverage Report
python -m pytest tests/ --cov=utils --cov-report=term-missing -v

# Frontend build check
cd frontend && npm run build
```

> **Lưu ý:** CI/CD (GitHub Actions) tự động chạy bộ **Unit Tests** mỗi khi có commit mới đẩy lên nhánh `main`.

---

## 📝 Quy tắc làm việc nhóm

1. **KHÔNG BAO GIỜ** commit file `.env`, file SQLite `.db` hoặc file CSV dữ liệu lên GitHub.
2. Tạo nhánh riêng (`git checkout -b ten_tinh_nang`) khi phát triển tính năng mới.
3. Chạy `pytest` sau mỗi lần thay đổi code phần tính điểm để đảm bảo không làm hỏng logic.
4. Ưu tiên sử dụng `sqlite3` thay vì load toàn bộ CSV vào pandas để chống sập RAM.

---

## 🛠️ Tech Stack

| Thành phần           | Công nghệ                                          |
| -------------------- | ---------------------------------------------------- |
| AI / LLM             | OpenRouter API (`qwen/qwen3-8b` + fallback models) |
| Backend              | FastAPI + Uvicorn                                    |
| Frontend             | Next.js 15 + React + Tailwind CSS + shadcn/ui        |
| Cơ sở dữ liệu       | SQLite (truy vấn tốc độ cao O(log N))               |
| Data Processing      | Pandas, NumPy                                        |
| Search Engine        | BM25 + Fuzzy Matching (thuần Python)                |
| Offline ETL          | PyMuPDF + EasyOCR (chỉ chạy trên máy dev)           |
| Infrastructure       | Docker, Docker Compose                               |
| Testing              | Pytest                                               |
