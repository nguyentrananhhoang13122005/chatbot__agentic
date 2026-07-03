from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class MatchRequest(BaseModel):
    scores: Dict[str, float] = Field(..., description="Điểm các môn (VD: {'Toán': 8.5, 'Vật lý': 9.0})")
    bonus: float = Field(0.0, description="Điểm ưu tiên")
    methods: Optional[List[str]] = Field(
        default=["Xét điểm thi THPT"], 
        description="Phương thức xét tuyển"
    )
    k: int = Field(5, description="Số lượng trường/ngành gợi ý")
    year_priority: Optional[List[int]] = Field(default=[2025, 2024], description="Thứ tự ưu tiên năm")
    top_n_combos: int = Field(5, description="Số lượng tổ hợp tối đa để xem xét")
    province: Optional[str] = Field(None, description="Lọc theo Tỉnh/Thành phố")
    major: Optional[str] = Field(None, description="Lọc theo Ngành học")
    stream: bool = Field(False, description="Trả về StreamingResponse (true) hay JSON tĩnh (false)")
    # Extra fields — forwarded for future pipeline use
    ielts: Optional[float] = Field(None, description="Điểm IELTS")
    toefl: Optional[int] = Field(None, description="Điểm TOEFL iBT")
    toeic: Optional[int] = Field(None, description="Điểm TOEIC")
    gpa12: Optional[float] = Field(None, description="ĐTB lớp 12")
    rank12: Optional[str] = Field(None, description="Học lực lớp 12")
    not_taken_subjects: Optional[List[str]] = Field(default=[], description="Các môn không thi")

class SchoolMatchResult(BaseModel):
    schools: List[Dict[str, Any]] = Field(..., description="Danh sách các trường phù hợp")
    top_combinations: List[Dict[str, Any]] = Field(..., description="Các tổ hợp điểm cao nhất")
    strength: Dict[str, Any] = Field(..., description="Điểm mạnh/yếu")
    warnings: List[str] = Field(default=[], description="Cảnh báo quy chế")
    analysis: str = Field(..., description="Bản phân tích từ AI")

class RecommendRequest(BaseModel):
    user_query: str = Field(..., description="Câu hỏi tự nhiên của người dùng")
    stream: bool = Field(False, description="Trả về StreamingResponse (true) hay JSON tĩnh (false)")
    pre_extracted_school: str = Field("ALL", description="Mã/Tên trường trích xuất trước")
    pre_extracted_location: str = Field("ALL", description="Địa điểm trích xuất trước")
    pre_extracted_keyword: str = Field("ALL", description="Từ khóa trích xuất trước")
    pre_extracted_year: int = Field(0, description="Năm trích xuất trước")

class RecommendResponse(BaseModel):
    answer: str = Field(..., description="Câu trả lời từ AI")
