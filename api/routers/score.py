from fastapi import APIRouter, HTTPException
from api.schemas.score_schema import ScoreCalculationRequest, ScoreCalculationResponse
from utils.score_calculator import get_top_k_combinations, get_strength_analysis, normalize_scores

router = APIRouter()

@router.post("/calculate", response_model=ScoreCalculationResponse)
def calculate_scores(request: ScoreCalculationRequest):
    """
    Tính điểm các tổ hợp khối thi dựa trên điểm số các môn học và điểm ưu tiên.
    """
    try:
        # Chuẩn hóa tên môn học
        normalized_scores = normalize_scores(request.scores)
        
        # Tính top tổ hợp khối thi
        top_combos = get_top_k_combinations(
            scores=normalized_scores, 
            k=request.k, 
            bonus=request.bonus
        )
        
        # Phân tích điểm mạnh / yếu
        analysis = get_strength_analysis(scores=normalized_scores)
        
        return ScoreCalculationResponse(
            top_combinations=top_combos,
            analysis=analysis
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
