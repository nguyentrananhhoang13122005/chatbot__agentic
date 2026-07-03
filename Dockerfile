# Sử dụng Python 3.11 slim - tối ưu cho môi trường deploy
FROM python:3.11-slim

# Ngăn Python tạo file .pyc và bật log unbuffered
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết (đặc biệt cho OpenCV và thư viện C)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt công cụ cập nhật pip
RUN pip install --no-cache-dir --upgrade pip

# ==============================================================================
# HACK TỐI ƯU CHO AI:
# Cài đặt Torch bản CPU trước. Mặc định pip sẽ tải bản có CUDA > 2.5GB.
# Máy chủ không GPU không cần CUDA. Dòng này giúp tiết kiệm 2GB dung lượng!
# ==============================================================================
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Cài đặt các thư viện Python từ requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào Container
COPY . .

# Expose cổng của FastAPI
EXPOSE 8000

# Chạy ứng dụng FastAPI bằng Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
