from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from api.schemas.school_schema import MatchRequest, RecommendRequest, SchoolMatchResult, RecommendResponse
from agents.match_maker import find_top_k_schools, build_analysis_prompt, generate_analysis_stream
from agents.recommender import query_diem_chuan, query_diem_chuan_stream
import pandas as pd
import json

router = APIRouter()

@router.post("/match", response_model=SchoolMatchResult)
async def match_schools(request: MatchRequest):
    """
    Tìm kiếm và gợi ý trường/ngành dựa trên điểm số người dùng.
    Hỗ trợ trả về JSON hoặc SSE Stream.
    """
    match_result = find_top_k_schools(
        student_scores=request.scores,
        methods=request.methods,
        k=request.k,
        bonus=request.bonus,
        year_priority=request.year_priority,
        top_n_combos=request.top_n_combos,
        province=request.province,
        major=request.major
    )
    
    if "error" in match_result:
        raise HTTPException(status_code=400, detail=match_result["error"])

    df_top = match_result.get("matched_schools", pd.DataFrame())
    schools_list = df_top.to_dict(orient="records") if not df_top.empty else []
    
    # Xử lý NaN trong pandas dict
    import math
    for s in schools_list:
        for k, v in s.items():
            if isinstance(v, float) and math.isnan(v):
                s[k] = None
    


    if request.stream:
        def sse_generator():
            # Send initial data block
            init_data = {
                "type": "meta",
                "schools": schools_list,
                "top_combinations": match_result.get("top_combinations", []),
                "strength": match_result.get("strength", {}),
                "warnings": match_result.get("warnings", [])
            }
            yield f"data: {json.dumps(init_data, ensure_ascii=False)}\n\n"
            
            # Send LLM chunks
            for chunk in generate_analysis_stream(match_result):
                if chunk:
                    chunk_data = {"type": "chunk", "content": chunk}
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
            
            yield "data: [DONE]\n\n"
            
        return StreamingResponse(sse_generator(), media_type="text/event-stream")

    else:
        # Chạy đồng bộ gom chunk
        analysis_text = ""
        for chunk in generate_analysis_stream(match_result):
            if chunk:
                analysis_text += chunk
                
        return SchoolMatchResult(
            schools=schools_list,
            top_combinations=match_result.get("top_combinations", []),
            strength=match_result.get("strength", {}),
            warnings=match_result.get("warnings", []),
            analysis=analysis_text
        )

@router.post("/recommend", response_model=RecommendResponse)
async def recommend_schools(request: RecommendRequest):
    """
    Tra cứu điểm chuẩn và gợi ý trường qua Chat (Recommender Agent).
    Hỗ trợ trả về JSON hoặc SSE Stream.
    """
    if request.stream:
        def recommender_sse_generator():
            response_generator = query_diem_chuan_stream(
                user_query=request.user_query,
                pre_extracted_school=request.pre_extracted_school,
                pre_extracted_location=request.pre_extracted_location,
                pre_extracted_keyword=request.pre_extracted_keyword,
                pre_extracted_year=request.pre_extracted_year
            )
            for chunk in response_generator:
                if chunk:
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            
        return StreamingResponse(recommender_sse_generator(), media_type="text/event-stream")
    else:
        answer = query_diem_chuan(
            user_query=request.user_query,
            pre_extracted_school=request.pre_extracted_school,
            pre_extracted_location=request.pre_extracted_location,
            pre_extracted_keyword=request.pre_extracted_keyword,
            pre_extracted_year=request.pre_extracted_year
        )
        return RecommendResponse(answer=answer)
