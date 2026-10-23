from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from api.routers.score import router as score_router

app = FastAPI(
    title="UniSearch AI API",
    description="Backend API for UniSearch Admissions",
    version="1.0.0"
)

# Cấu hình CORS cho phép Frontend (ví dụ Next.js ở cổng 3000) gọi API
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(score_router, prefix="/api/v1/scores", tags=["Scores"])

@app.get("/health")
def health_check():
    """Endpoint kiểm tra sức khỏe của API."""
    return {"status": "ok", "message": "UniSearch API is running smoothly!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)  # nosec B104
