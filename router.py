import sys
import json
import re

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from agents.recommender import query_diem_chuan, query_diem_chuan_stream
from agents.counselor import tu_van_cv, tu_van_cv_stream
from llm_client import OPENROUTER_FALLBACK_MODELS, call_llm, call_llm_stream

# ======== UNIFIED ANALYZER: 1 LLM CALL = Routing + Entity Extraction + Query Expansion ========
ANALYZER_PROMPT = """Bạn là BỘ PHÂN TÍCH TRUNG TÂM (Analyzer) cho Hệ thống AI Tư vấn Tuyển sinh Đại học.
Nhiệm vụ: Đọc lịch sử hội thoại + câu hỏi mới, thực hiện 3 việc trong 1 lần:

1. PHÂN LOẠI (intent):
   - "RECOMMENDER": Tra cứu điểm chuẩn, tìm trường/ngành, hỏi chỉ tiêu, thông tin tuyển sinh, so sánh trường, hỏi về ngành phù hợp dựa trên điểm số.
   - "COUNSELOR": Tư vấn hướng nghiệp, đánh giá hồ sơ năng lực, phân tích CV, định hướng sở thích/tính cách.
   - "GENERAL": Mọi câu hỏi KHÔNG liên quan tới tuyển sinh đại học Việt Nam hoặc tư vấn hướng nghiệp. VD: hỏi thời tiết, lập trình, lịch sử, toán học, chào hỏi xã giao, hỏi "bạn là ai", v.v.
   LƯU Ý: Nếu câu hỏi đề cập tới trường/ngành CỤ THỂ (kể cả qua "trường này", "ngành đó") → luôn là RECOMMENDER.

2. TRÍCH XUẤT THỰC THỂ (entities — chỉ cho RECOMMENDER):
   - school: Trả về từ khóa TIẾNG VIỆT ĐÚNG NGUYÊN VĂN những gì user gõ. TUYỆT ĐỐI KHÔNG THÊM ĐỊA DANH nếu user không nói rõ.
     VD ĐÚNG: user gõ "bách khoa" → trả về "Bách khoa" (KHÔNG thêm Hà Nội).
     VD ĐÚNG: user gõ "bách khoa hà nội" → trả về "Bách khoa Hà Nội".
     VD ĐÚNG: user gõ "ngoại thương" → trả về "Ngoại thương".
     BẮT BUỘC DỊCH viết tắt tiếng Anh thành tiếng Việt: "HUST" → "Bách khoa Hà Nội", "NEU" → "Kinh tế Quốc dân", "FTU" → "Ngoại thương", "PTIT" → "Bưu chính Viễn thông", "UET" → "Công nghệ ĐHQG Hà Nội", "BKU" → "Bách khoa TPHCM".
     KHÔNG kèm "Đại học", "Học viện", "Trường". Nếu user nói "trường này/trường đó" → dùng lịch sử hội thoại xác định. Nếu không xác định → "ALL".
   - location: Vùng miền hoặc địa phương nếu user có đề cập (VD: "HN", "HCM", "ĐN", "Hà Nội", "Đà Nẵng", "TPHCM"). Nếu không đề cập → "ALL".
   - keyword: Tên ngành cụ thể (VD: "công nghệ thông tin"). Nếu user gõ mã ngành dạng số → ghi kèm sau dấu | (VD: "y khoa|7720101"). TUYỆT ĐỐI KHÔNG TỰ BỊA MÃ NGÀNH. Nếu hỏi chung "điểm các ngành" → ghi "điểm|chuẩn".
   - year: Năm cụ thể nếu user đề cập (VD: 2024). Nếu không → 0.

3. CHUẨN HOÁ CÂU HỎI (standalone_query):
   Viết lại câu hỏi thành câu độc lập, giải tham chiếu "trường này" → tên trường thật, "ngành đó" → tên ngành thật dựa trên lịch sử.

BẮT BUỘC trả về JSON duy nhất, KHÔNG giải thích:
{"intent": "RECOMMENDER|COUNSELOR|GENERAL", "school": "...", "location": "...", "keyword": "...", "year": 0, "standalone_query": "..."}"""


# ======== BƯỚC 1: PHÂN LOẠI CÂU HỎI (Classification Only) ========
def classify_query(user_query: str, has_file: bool = False, chat_history: list = None) -> dict:
    """
    Router Section 1: Phân loại câu hỏi và trích xuất thực thể.
    Chỉ trả về kết quả phân loại (dict), KHÔNG gọi Agent.
    """
    # Xây dựng context từ lịch sử hội thoại
    history_context = ""
    if chat_history:
        history_lines = []
        for msg in chat_history[-4:]:
            role = "Người dùng" if msg["role"] == "user" else "Trợ lý"
            content = msg["content"][:300] if msg["role"] == "assistant" else msg["content"]
            history_lines.append(f"{role}: {content}")
        history_context = "\n".join(history_lines)

    # ======== 1 LLM CALL DUY NHẤT ========
    user_message = f"""Lịch sử hội thoại gần nhất:
{history_context if history_context else "(Chưa có lịch sử)"}

Câu hỏi mới nhất của người dùng: "{user_query}"
Người dùng có đính kèm file CV?: {"Có file" if has_file else "Không có file"}"""

    llm_messages = [
        {"role": "system", "content": ANALYZER_PROMPT},
        {"role": "user", "content": user_message},
    ]
    
    raw_response, error_info = call_llm(
        messages=llm_messages,
        model_list=OPENROUTER_FALLBACK_MODELS,
        temperature=0.0,
        max_tokens=300,
    )

    if raw_response:
        try:
            # Parse JSON response — xử lý trường hợp LLM wrap trong markdown
            json_str = raw_response
            if "```" in json_str:
                match = re.search(r'```(?:json)?\s*(.*?)\s*```', json_str, re.DOTALL)
                if match:
                    json_str = match.group(1)
            
            analysis = json.loads(json_str)
            
            result = {
                "intent": analysis.get("intent", "RECOMMENDER").upper(),
                "school": analysis.get("school", "ALL"),
                "location": analysis.get("location", "ALL"),
                "keyword": analysis.get("keyword", "ALL"),
                "year": analysis.get("year", 0),
                "standalone_query": analysis.get("standalone_query", user_query),
                "status": "success"
            }
            
            print(f"DEBUG [Router → Classify]: intent={result['intent']}, school='{result['school']}', location='{result['location']}', keyword='{result['keyword']}', year={result['year']}")
            print(f"DEBUG [Router → Classify]: standalone_query='{result['standalone_query']}'")
            
            return result

        except Exception as e:
            print(f"⚠️ Router parse error: {e}")
            error_info = {
                "message": "⚠️ Router AI trả về dữ liệu không hợp lệ. Hệ thống sẽ dùng phân loại mặc định.",
                "detail": str(e),
            }

    # Cả 2 model đều lỗi → fallback
    print("⚠️ Router: All models failed, falling back to defaults")
    return {
        "intent": "COUNSELOR" if has_file else "RECOMMENDER",
        "school": "ALL",
        "location": "ALL",
        "keyword": "ALL",
        "year": 0,
        "standalone_query": user_query,
        "status": "fallback",
        "error_message": error_info["message"] if error_info else "⚠️ Router AI tạm thời không khả dụng. Hệ thống sẽ dùng phân loại mặc định."
    }


# ======== GENERAL LLM PROMPT ========
GENERAL_SYSTEM_PROMPT = """Bạn là UniSearch AI — trợ lý thông minh đa năng.
Bạn chuyên về tuyển sinh đại học Việt Nam, nhưng cũng có thể trả lời các câu hỏi kiến thức chung.
Hãy trả lời ngắn gọn, chính xác, thân thiện bằng tiếng Việt.
Nếu câu hỏi liên quan đến tuyển sinh, hãy nhắc người dùng rằng họ có thể hỏi trực tiếp về điểm chuẩn, ngành học, hoặc so sánh trường để được hỗ trợ chuyên sâu hơn."""


def _general_llm_answer(user_query: str, chat_history: list = None) -> str:
    """Gọi LLM trực tiếp để trả lời câu hỏi chung không liên quan đến data tuyển sinh."""
    messages = [{"role": "system", "content": GENERAL_SYSTEM_PROMPT}]
    if chat_history:
        for msg in chat_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"][:500]})
    messages.append({"role": "user", "content": user_query})

    content, error_info = call_llm(
        messages=messages,
        model_list=OPENROUTER_FALLBACK_MODELS,
        temperature=0.5,
        max_tokens=1024,
    )
    if content:
        return content
    return error_info["message"] if error_info else "⚠️ Không thể xử lý câu hỏi lúc này."


def _general_llm_stream(user_query: str, chat_history: list = None):
    """Gọi LLM stream trực tiếp để trả lời câu hỏi chung."""
    messages = [{"role": "system", "content": GENERAL_SYSTEM_PROMPT}]
    if chat_history:
        for msg in chat_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"][:500]})
    messages.append({"role": "user", "content": user_query})

    return call_llm_stream(
        messages=messages,
        model=OPENROUTER_FALLBACK_MODELS[0],
        temperature=0.5,
        max_tokens=1024,
    )


# ======== BƯỚC 2: GIAO VIỆC CHO ĐÚNG AGENT (Dispatch Only) ========
def dispatch_to_agent(classification: dict, user_query: str, uploaded_file=None, chat_history: list = None) -> str:
    """
    Router Section 2: Dựa trên kết quả phân loại, giao việc cho đúng Agent.
    - RECOMMENDER → agents/recommender.py (Tra cứu điểm chuẩn)
    - COUNSELOR  → agents/counselor.py (Tư vấn hướng nghiệp)
    - GENERAL    → LLM trực tiếp (câu hỏi chung)
    """
    intent = classification.get("intent", "RECOMMENDER")
    standalone_query = classification.get("standalone_query", user_query)

    if intent == "GENERAL":
        return _general_llm_answer(user_query, chat_history)
    elif intent == "COUNSELOR":
        return tu_van_cv(cv_file=uploaded_file, user_query=user_query)
    if intent == "RECOMMENDER":
        return query_diem_chuan(
            user_query=standalone_query,
            pre_extracted_school=classification.get("school", "ALL"),
            pre_extracted_location=classification.get("location", "ALL"),
            pre_extracted_keyword=classification.get("keyword", "ALL"),
            pre_extracted_year=classification.get("year", 0),
        )


def dispatch_to_agent_stream(classification: dict, user_query: str, uploaded_file=None, chat_history: list = None):
    """
    Router Section 2 Streaming: Dựa trên kết quả phân loại, giao việc cho đúng Agent và trả về kết quả stream/structured response.
    """
    intent = classification.get("intent", "RECOMMENDER")

    if intent == "GENERAL":
        return _general_llm_stream(user_query, chat_history)
    elif intent == "COUNSELOR":
        return tu_van_cv_stream(cv_file=uploaded_file, user_query=user_query)
    else:
        recommender_response = query_diem_chuan_stream(
            user_query=classification.get("standalone_query", user_query),
            pre_extracted_school=classification.get("school", "ALL"),
            pre_extracted_location=classification.get("location", "ALL"),
            pre_extracted_keyword=classification.get("keyword", "ALL"),
            pre_extracted_year=classification.get("year", 0),
        )
        return recommender_response


# ======== WRAPPER (Backward compatibility) ========
def route_query(user_query: str, has_file: bool = False, uploaded_file=None, chat_history: list = None) -> str:
    """Wrapper gọi classify → dispatch tuần tự."""
    classification = classify_query(user_query, has_file, chat_history)
    return dispatch_to_agent(classification, user_query, uploaded_file, chat_history)

