from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class ScoreCalculationRequest(BaseModel):
    scores: Dict[str, float] = Field(
        ...,
        description="Từ điển các môn học và điểm số",
        example={"Toán": 8.0, "Vật lý": 7.5, "Hóa học": 8.5}
    )
    bonus: float = Field(
        0.0,
        description="Điểm ưu tiên (khu vực, đối tượng)",
        example=0.5
    )
    k: int = Field(
        5,
        description="Số lượng tổ hợp muốn lấy (top K)",
        example=5
    )

class CombinationResult(BaseModel):
    code: str = Field(..., description="Mã tổ hợp (VD: A00)")
    subjects: List[str] = Field(..., description="Danh sách các môn học trong tổ hợp")
    total: float = Field(..., description="Tổng điểm tổ hợp")
    below_threshold: bool = Field(False, description="True nếu bị điểm liệt hoặc tổng điểm < 15")
    rank: int = Field(..., description="Thứ hạng của tổ hợp")

class ScoreCalculationResponse(BaseModel):
    top_combinations: List[CombinationResult] = Field(
        ...,
        description="Danh sách các tổ hợp điểm cao nhất"
    )
    analysis: Dict[str, Any] = Field(
        ...,
        description="Bản phân tích điểm mạnh yếu của thí sinh"
    )
