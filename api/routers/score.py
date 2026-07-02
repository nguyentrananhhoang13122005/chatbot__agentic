from fastapi import APIRouter, HTTPException
from api.schemas.score_schema import ScoreCalculationRequest, ScoreCalculationResponse
from utils.score_calculator import get_top_k_combinations, get_strength_analysis, normalize_scores

router = APIRouter()

@router.post("/calculate", response_model=ScoreCalculationResponse)
def calculate_scores(request: ScoreCalculationRequest):
    """
    Tính điểm các tổ hợp khối thi dựa trên điểm số các môn học và điểm ưu tiên.
    """
    # Chuẩn hóa tên môn học
    normalized_scores = normalize_scores(request.scores)
    if len(normalized_scores) < 3:
        raise HTTPException(
            status_code=422,
            detail="Cần ít nhất 3 môn hợp lệ để tính tổ hợp khối thi.",
        )

    # Tính top tổ hợp khối thi
    top_combos = get_top_k_combinations(
        scores=normalized_scores,
        k=request.k,
        bonus=request.bonus,
    )
    if not top_combos:
        raise HTTPException(
            status_code=422,
            detail="Không tìm được tổ hợp khối thi phù hợp từ dữ liệu đã cung cấp.",
        )

    # Phân tích điểm mạnh / yếu
    analysis = get_strength_analysis(scores=normalized_scores)

    return ScoreCalculationResponse(
        top_combinations=top_combos,
        analysis=analysis,
    )
