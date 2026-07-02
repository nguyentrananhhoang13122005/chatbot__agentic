from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from api.routers.score import router as scores_router
from api.routers.schools import router as schools_router

app = FastAPI(
    title="UniSearch AI API",
    description="Backend API cho hệ thống tư vấn tuyển sinh đại học",
    version="1.0.0"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên giới hạn origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các router
app.include_router(scores_router, prefix="/api/v1/scores", tags=["Scores"])
app.include_router(schools_router, prefix="/api/v1/schools", tags=["Schools"])

@app.get("/health")
def health_check():
    """Endpoint kiểm tra sức khỏe của API."""
    return {"status": "ok", "message": "UniSearch API is running smoothly!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)  # nosec B104
