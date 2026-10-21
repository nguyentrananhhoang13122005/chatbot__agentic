import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from api.routers.score import router as scores_router
from api.routers.schools import router as schools_router
from api.routers.auth import router as auth_router
from api.routers.chat import router as chat_router

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Origin mặc định + origin bổ sung qua env (phân tách bằng dấu phẩy), vd. CORS_EXTRA_ORIGINS=http://127.0.0.1:3000
_CORS_ORIGINS = ["http://localhost:3000"] + [
    o.strip() for o in os.getenv("CORS_EXTRA_ORIGINS", "").split(",") if o.strip()
]

app = FastAPI(
    title="UniSearch AI API",
    description="Backend API cho hệ thống tư vấn tuyển sinh đại học",
    version="1.0.0"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,  # Bắt buộc khai báo origin cụ thể khi dùng credentials=True
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các router
app.include_router(scores_router, prefix="/api/v1/scores", tags=["Scores"])
app.include_router(schools_router, prefix="/api/v1/schools", tags=["Schools"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])

@app.get("/health")
def health_check():
    """Endpoint kiểm tra sức khỏe của API."""
    return {"status": "ok", "message": "UniSearch API is running smoothly!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)  # nosec B104
