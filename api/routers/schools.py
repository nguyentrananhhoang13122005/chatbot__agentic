from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from api.schemas.school_schema import MatchRequest, RecommendRequest, SchoolMatchResult, RecommendResponse, ChatRequest
from agents.match_maker import find_top_k_schools, generate_analysis_stream
from agents.recommender import query_diem_chuan, query_diem_chuan_stream
import pandas as pd
import json
import math
import logging
import os
import sqlite3
from typing import Optional
from chat_db import save_searched_university
from api.routers.auth import get_current_user_optional
from utils.guardrails import (
    GuardrailViolation,
    chat_rate_limiter,
    sanitize_history,
    validate_user_query,
)
from utils.response_stream import iter_response_chunks

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Adapter: Vietnamese DataFrame columns → frontend-expected English keys
# ---------------------------------------------------------------------------

def _normalize_school_record(raw: dict) -> dict:
    """Map Vietnamese DataFrame columns → frontend-expected English keys."""
    return {
        "school_name": raw.get("Trường"),
        "major_name": raw.get("Tên ngành"),
        "major_code": raw.get("Mã ngành"),
        "combo": raw.get("Tổ hợp khớp"),
        "score": raw.get("Điểm của bạn"),
        "score_min": raw.get("Điểm min"),
        "year_score": raw.get("Điểm chuẩn"),
        "year": raw.get("Năm"),
        "tier": raw.get("Tier"),
        "method": raw.get("Phương thức xét tuyển"),
        "delta": raw.get("Delta"),
        "is_scale_40": raw.get("Thang_40"),
        "notes": raw.get("Chú thích"),
    }


def _normalize_strength(raw: dict) -> dict:
    """Map score_calculator strength dict → frontend-expected keys."""
    strongest = raw.get("strongest")
    # strongest may be a list of [subject, score] pairs — extract names
    if isinstance(strongest, list):
        strongest = [s[0] if isinstance(s, (list, tuple)) else s for s in strongest]
    return {
        "avg_score": raw.get("avg"),
        "trend": raw.get("category"),
        "best_subjects": strongest,
        "subjects_count": raw.get("total_subjects"),
    }


def _sanitize_nan(records: list[dict]) -> list[dict]:
    """Replace NaN floats with None in a list of dicts (pandas artifact)."""
    for rec in records:
        for key, val in rec.items():
            if isinstance(val, float) and math.isnan(val):
                rec[key] = None
    return records


def _remember_school_search(user: Optional[dict], request: RecommendRequest) -> None:
    """Persist searched school history for authenticated users only."""
    if not user:
        return
    school_name = (request.pre_extracted_school or "").strip()
    if not school_name or school_name.upper() == "ALL":
        return
    try:
        save_searched_university(user["id"], school_name, query_text=request.user_query)
    except Exception:
        logger.exception("Failed to save searched university history")


@router.post("/match", response_model=SchoolMatchResult)
async def match_schools(request: MatchRequest, user: Optional[dict] = Depends(get_current_user_optional)):
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
    raw_schools = df_top.to_dict(orient="records") if not df_top.empty else []
    _sanitize_nan(raw_schools)

    # Normalize to frontend contract
    schools_list = [_normalize_school_record(s) for s in raw_schools]
    strength = _normalize_strength(match_result.get("strength", {}))

    if request.stream:
        def sse_generator():
            # Send initial data block
            init_data = {
                "type": "meta",
                "schools": schools_list,
                "top_combinations": match_result.get("top_combinations", []),
                "strength": strength,
                "warnings": match_result.get("warnings", [])
            }
            yield f"data: {json.dumps(init_data, ensure_ascii=False)}\n\n"

            # Send LLM chunks
            if not request.skip_analysis:
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
            strength=strength,
            warnings=match_result.get("warnings", []),
            analysis=analysis_text
        )

@router.post("/recommend", response_model=RecommendResponse)
async def recommend_schools(request: RecommendRequest, user: Optional[dict] = Depends(get_current_user_optional)):
    """
    Tra cứu điểm chuẩn và gợi ý trường qua Chat (Recommender Agent).
    Hỗ trợ trả về JSON hoặc SSE Stream.
    """
    _remember_school_search(user, request)

    if request.stream:
        def recommender_sse_generator():
            response_generator = query_diem_chuan_stream(
                user_query=request.user_query,
                pre_extracted_school=request.pre_extracted_school,
                pre_extracted_location=request.pre_extracted_location,
                pre_extracted_keyword=request.pre_extracted_keyword,
                pre_extracted_year=request.pre_extracted_year
            )
            for chunk in iter_response_chunks(response_generator):
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



def _data_as_of() -> str:
    """Nhãn ngày dữ liệu hiển thị cho người dùng (lấy từ db_metadata, không hard-code)."""
    db_path = os.getenv("DB_PATH", "data/admissions.db")
    try:
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute("SELECT value FROM db_metadata WHERE key='verified_latest_year'").fetchone()
        finally:
            conn.close()
        if row and row[0]:
            return f"Điểm chuẩn đã kiểm chứng đến năm {row[0]}"
    except Exception:
        logger.debug("Không đọc được db_metadata", exc_info=True)
    return ""


def _sse(payload) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat")
def chat(request: ChatRequest, http_request: Request, user: Optional[dict] = Depends(get_current_user_optional)):
    """
    Chat hợp nhất: guardrail → router (phân loại + trích thực thể + giải tham chiếu) → agent phù hợp.
    SSE: {"type":"meta",...} → {"type":"chunk","content":...}* → [DONE]
    """
    # Import trễ để tránh vòng phụ thuộc và giữ thời gian khởi động API.
    from router import classify_query, dispatch_to_agent_stream

    client_key = f"user:{user['id']}" if user else f"ip:{http_request.client.host if http_request.client else 'unknown'}"
    try:
        chat_rate_limiter.check(client_key)
        query = validate_user_query(request.user_query)
    except GuardrailViolation as violation:
        logger.info("guardrail blocked code=%s key=%s", violation.code, client_key)
        if violation.status_code == 429:
            raise HTTPException(status_code=429, detail=violation.message)
        v_code = violation.code
        v_msg = violation.message
        if request.stream:
            def blocked_stream():
                yield _sse({"type": "meta", "intent": "BLOCKED", "guardrail": v_code})
                yield _sse({"type": "chunk", "content": v_msg})
                yield "data: [DONE]\n\n"
            return StreamingResponse(blocked_stream(), media_type="text/event-stream")
        return {"answer": v_msg, "intent": "BLOCKED"}

    history = sanitize_history([m.model_dump() for m in request.history])

    def run_pipeline():
        classification = classify_query(query, has_file=request.has_file, chat_history=history)
        response = dispatch_to_agent_stream(classification, query, history)
        return classification, iter_response_chunks(response)

    if request.stream:
        def chat_sse():
            try:
                classification, chunks = run_pipeline()
                if user and classification.get("intent") == "RECOMMENDER":
                    school = (classification.get("school") or "").strip()
                    if school and school.upper() != "ALL":
                        try:
                            save_searched_university(user["id"], school, query_text=query)
                        except Exception:
                            logger.exception("Failed to save searched university history")
                yield _sse({
                    "type": "meta",
                    "intent": classification.get("intent"),
                    "school": classification.get("school"),
                    "router_status": classification.get("status"),
                    "data_as_of": _data_as_of() if classification.get("intent") == "RECOMMENDER" else "",
                })
                full_answer = []
                for chunk in chunks:
                    full_answer.append(chunk)
                    yield _sse({"type": "chunk", "content": chunk})

                # Tự động lưu phiên chat vào CSDL nếu người dùng đã đăng nhập và có session_id
                full_text = "".join(full_answer)
                if user and request.session_id and full_text.strip():
                    try:
                        from chat_db import save_session
                        history_msgs = [m.model_dump() for m in request.history]
                        history_msgs.append({"role": "user", "content": query})
                        history_msgs.append({"role": "assistant", "content": full_text})
                        save_session(
                            session_id=request.session_id,
                            messages=history_msgs,
                            user_id=user["id"]
                        )
                    except Exception:
                        logger.exception("Failed to auto-save chat session in SSE")
            except Exception:
                logger.exception("chat pipeline failed")
                yield _sse({"type": "chunk", "content": "⚠️ Hệ thống đang gặp sự cố khi xử lý câu hỏi. Bạn vui lòng thử lại sau ít phút."})
            yield "data: [DONE]\n\n"

        return StreamingResponse(chat_sse(), media_type="text/event-stream")

    try:
        classification, chunks = run_pipeline()
        answer = "".join(chunks)
        if user and request.session_id and answer.strip():
            try:
                from chat_db import save_session
                history_msgs = [m.model_dump() for m in request.history]
                history_msgs.append({"role": "user", "content": query})
                history_msgs.append({"role": "assistant", "content": answer})
                save_session(
                    session_id=request.session_id,
                    messages=history_msgs,
                    user_id=user["id"]
                )
            except Exception:
                logger.exception("Failed to auto-save chat session")
        return {
            "answer": answer,
            "intent": classification.get("intent"),
            "data_as_of": _data_as_of() if classification.get("intent") == "RECOMMENDER" else "",
        }
    except Exception:
        logger.exception("chat pipeline failed")
        raise HTTPException(status_code=500, detail="Hệ thống đang gặp sự cố, vui lòng thử lại.")