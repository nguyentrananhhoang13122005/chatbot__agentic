import sys
import json
import re

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import logging

from agents.recommender import query_diem_chuan, query_diem_chuan_stream
from agents.counselor import tu_van_cv, tu_van_cv_stream
from llm_client import OPENROUTER_FALLBACK_MODELS, call_llm, call_llm_stream

logger = logging.getLogger(__name__)

# ======== HEURISTIC FALLBACK (khi Analyzer LLM lỗi) ========
_YEAR_RE = re.compile(r"\b(20[12]\d)\b")
_ABBR_RE = re.compile(r"\b(ptit|hust|neu|ftu|uet|uit|hcmut|bku|hcmus|khtn|spkt)\b", re.IGNORECASE)
_SCHOOL_RE = re.compile(
    r"(?:đại học|học viện|trường|đh)\s+([^\d,?.!]+?)(?=\s+(?:năm|ngành|khối|tổ hợp|bao nhiêu|có|là|thế nào|lấy|xét)\b|\s*[\d,?.!]|$)",
    re.IGNORECASE,
)
_COUNSELOR_HINTS = ("cv", "hồ sơ năng lực", "hướng nghiệp", "tính cách", "sở thích", "phù hợp với tôi", "phù hợp với mình")
_QUALITATIVE_HINTS = ("chất lượng", "uy tín", "cơ sở vật chất", "môi trường", "nên học", "nên chọn", "so sánh", "đánh giá")
_DATA_HINTS = ("điểm", "chỉ tiêu", "mã ngành", "tổ hợp", "khối", "phương thức", "top ", "xét tuyển", "học phí")


def _heuristic_classify(user_query: str, has_file: bool = False) -> dict:
    """Phân loại rẻ bằng quy tắc khi Analyzer LLM không dùng được. Không bịa: không chắc thì để ALL."""
    q = user_query.lower()
    year_match = _YEAR_RE.search(q)
    school = "ALL"
    abbr = _ABBR_RE.search(user_query)
    if abbr:
        school = abbr.group(1).upper()
    else:
        m = _SCHOOL_RE.search(user_query)
        if m:
            school = m.group(1).strip()

    has_data = any(k in q for k in _DATA_HINTS)
    if has_file or (any(k in q for k in _COUNSELOR_HINTS) and not has_data):
        intent = "COUNSELOR"
    elif any(k in q for k in _QUALITATIVE_HINTS) and not has_data:
        intent = "GENERAL"
    else:
        intent = "RECOMMENDER"

    return {
        "intent": intent,
        "school": school,
        "location": "ALL",
        "keyword": "ALL",
        "year": int(year_match.group(1)) if year_match else 0,
        "standalone_query": user_query,
        "status": "heuristic",
    }

# ======== UNIFIED ANALYZER: 1 LLM CALL = Routing + Entity Extraction + Query Expansion ========
ANALYZER_PROMPT = """Bạn là BỘ PHÂN TÍCH TRUNG TÂM (Analyzer) cho Hệ thống AI Tư vấn Tuyển sinh Đại học.
Nhiệm vụ: Đọc lịch sử hội thoại + câu hỏi mới, thực hiện 3 việc trong 1 lần:

1. PHÂN LOẠI (intent):
   - "RECOMMENDER": CHỈ DÙNG KHI TRA CỨU SỐ LIỆU (Tra cứu điểm chuẩn, mã ngành, danh sách các ngành đào tạo, chỉ tiêu, học phí, thông tin tuyển sinh, phương thức xét tuyển, khối thi). Mọi câu hỏi về HỌC PHÍ / CHỈ TIÊU / CÁC NGÀNH ĐÀO TẠO của một trường cụ thể đều là RECOMMENDER (số liệu phải lấy từ đề án tuyển sinh, không được trả lời từ trí nhớ).
   - "COUNSELOR": Tư vấn hướng nghiệp, đánh giá hồ sơ năng lực, phân tích CV, định hướng sở thích/tính cách.
   - "GENERAL": Mọi câu hỏi KHÁC. BAO GỒM: 
       + So sánh chất lượng, đánh giá uy tín, cơ sở vật chất, môi trường học tập giữa các trường/ngành.
       + Hỏi đáp kiến thức chung, lịch sử, toán học, chào hỏi, v.v.
   LƯU Ý TỐI QUAN TRỌNG: Mặc dù câu hỏi có nhắc đến tên trường cụ thể (VD: "so sánh ngoại thương và bách khoa", "trường kinh tế quốc dân đào tạo tốt không"), nhưng nếu tính chất câu hỏi là TƯ VẤN/ĐÁNH GIÁ CHẤT LƯỢNG (không hỏi điểm chuẩn) thì BẮT BUỘC phải phân loại là "GENERAL".

2. TRÍCH XUẤT THỰC THỂ (entities — chỉ cho RECOMMENDER):
   - school: Trả về từ khóa TIẾNG VIỆT ĐÚNG NGUYÊN VĂN những gì user gõ. TUYỆT ĐỐI KHÔNG THÊM ĐỊA DANH nếu user không nói rõ.
     VD ĐÚNG: user gõ "bách khoa" → trả về "Bách khoa" (KHÔNG thêm Hà Nội).
     VD ĐÚNG: user gõ "bách khoa hà nội" → trả về "Bách khoa Hà Nội".
     VD ĐÚNG: user gõ "ngoại thương" → trả về "Ngoại thương".
     BẮT BUỘC DỊCH viết tắt tiếng Anh thành tiếng Việt: "HUST" → "Bách khoa Hà Nội", "NEU" → "Kinh tế Quốc dân", "FTU" → "Ngoại thương", "PTIT" → "Bưu chính Viễn thông", "UET" → "Công nghệ ĐHQG Hà Nội", "BKU" → "Bách khoa TPHCM". Nếu câu hỏi có "dệt may" khi tra cứu tuyển sinh/điểm chuẩn thì school là "Dệt May" (ĐH Công nghiệp Dệt May).
     KHÔNG kèm "Đại học", "Học viện", "Trường". Nếu user nói "trường này/trường đó" → dùng lịch sử hội thoại xác định. Nếu không xác định → "ALL".
   - location: Vùng miền hoặc địa phương nếu user có đề cập (VD: "HN", "HCM", "ĐN", "Hà Nội", "Đà Nẵng", "TPHCM"). Nếu không đề cập → "ALL".
   - keyword: Tên ngành cụ thể (VD: "công nghệ thông tin"). Nếu user gõ mã ngành dạng số → ghi kèm sau dấu | (VD: "y khoa|7720101"). TUYỆT ĐỐI KHÔNG TỰ BỊA MÃ NGÀNH. Nếu hỏi chung "điểm các ngành" hoặc "các ngành" → ghi "điểm|chuẩn".
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
            
            # ======== GUARD: Override RECOMMENDER → GENERAL cho câu hỏi đánh giá/so sánh chất lượng ========
            if result["intent"] == "RECOMMENDER":
                q_lower = user_query.lower()
                # Từ khóa đánh giá chất lượng / so sánh định tính
                qualitative_keywords = [
                    'so sánh chất lượng', 'so sánh giữa', 'so sánh trường',
                    'chất lượng đào tạo', 'chất lượng giảng dạy', 'chất lượng',
                    'môi trường học', 'cơ sở vật chất', 'uy tín',
                    'trường nào tốt hơn', 'trường nào hơn', 'nên học trường nào',
                    'nên chọn trường', 'đào tạo tốt', 'đào tạo có tốt',
                    'trường nào uy tín', 'review trường', 'đánh giá trường',
                    'trường nào đáng', 'có nên học', 'có tốt không',
                    'khác nhau như thế nào', 'khác nhau thế nào', 'khác gì',
                    'hơn gì', 'thua gì', 'mạnh hơn', 'yếu hơn',
                ]
                # Từ khóa tra cứu SỐ LIỆU cụ thể (nếu có thì giữ nguyên RECOMMENDER)
                data_keywords = [
                    'điểm chuẩn', 'bao nhiêu điểm', 'điểm trúng tuyển',
                    'chỉ tiêu', 'mã ngành', 'tổ hợp', 'khối thi',
                    'học phí', 'phương thức xét tuyển',
                ]
                has_qualitative = any(kw in q_lower for kw in qualitative_keywords)
                has_data_lookup = any(kw in q_lower for kw in data_keywords)
                
                if has_qualitative and not has_data_lookup:
                    result["intent"] = "GENERAL"
                    logger.info("router guard: RECOMMENDER -> GENERAL (qualitative comparison)")

            # Guard ngược: hỏi số liệu cụ thể hoặc danh sách ngành của một trường mà bị phân GENERAL thì LLM sẽ trả lời từ trí nhớ và dễ bịa số.
            q_lower = user_query.lower()
            if result["intent"] == "GENERAL":
                hard_data_terms = (
                    'học phí', 'chỉ tiêu', 'điểm chuẩn', 'mã ngành', 'phương thức xét tuyển',
                    'tổ hợp xét tuyển', 'các ngành', 'danh sách ngành', 'những ngành', 'chương trình đào tạo'
                )
                soft_terms = ('so sánh chất lượng', 'uy tín', 'cơ sở vật chất', 'nên học', 'nên chọn', 'môi trường học')
                if any(t in q_lower for t in hard_data_terms) and not any(t in q_lower for t in soft_terms):
                    result["intent"] = "RECOMMENDER"
                    logger.info("router guard: GENERAL -> RECOMMENDER (câu hỏi số liệu / danh sách ngành cụ thể)")

            # Trợ giúp trích xuất tên trường Dệt May nếu LLM bỏ sót
            if result.get("school") in ("ALL", "", None) and "dệt may" in q_lower and ("điểm" in q_lower or "tuyển sinh" in q_lower or "chỉ tiêu" in q_lower):
                result["school"] = "Dệt May"

            logger.info(
                "router classify intent=%s school=%r location=%r keyword=%r year=%s",
                result["intent"], result["school"], result["location"], result["keyword"], result["year"],
            )
            
            return result

        except Exception as e:
            logger.warning("Router parse error: %s", e)
            error_info = {
                "message": "⚠️ Router AI trả về dữ liệu không hợp lệ. Hệ thống sẽ dùng phân loại mặc định.",
                "detail": str(e),
            }

    # Mọi model đều lỗi → phân loại heuristic (không còn mặc định mù)
    logger.warning("Router: LLM analyzer failed, using heuristic classifier")
    result = _heuristic_classify(user_query, has_file)
    result["error_message"] = error_info["message"] if error_info else "⚠️ Router AI tạm thời không khả dụng. Hệ thống sẽ dùng phân loại heuristic."
    return result


from utils.location_registry import detect_location_query, get_grounding_context_for_location

# ======== GENERAL LLM PROMPT ========
GENERAL_SYSTEM_PROMPT = """Bạn là UniSearch AI — trợ lý thông minh và chuyên gia tư vấn giáo dục đại học tại Việt Nam.
Nhiệm vụ của bạn là giải đáp các thắc mắc chung, TƯ VẤN CHẤT LƯỢNG, MÔI TRƯỜNG HỌC TẬP, CƠ SỞ VẬT CHẤT, và ĐỊNH HƯỚNG chọn trường cho học sinh.
Hãy trả lời bám sát đúng trọng tâm câu hỏi của người dùng, phân tích khách quan đa chiều (ưu điểm, nhược điểm). TUYỆT ĐỐI không trả lời lan man, không bịa đặt.

QUY TẮC BẮT BUỘC VỀ THÔNG TIN TRƯỜNG HỌC & CHỐNG ẢO GIÁC:
1. TUYỆT ĐỐI KHÔNG TỰ BỊA TÊN VIẾT TẮT TIẾNG ANH (Acronym). Nếu không biết chính xác 100% tên viết tắt chuẩn tại Việt Nam, CHỈ DÙNG TÊN TIẾNG VIỆT ĐẦY ĐỦ CỦA TRƯỜNG.
   - Ví dụ đúng: Trường Đại học Công nghệ Thông tin và Truyền thông - Đại học Thái Nguyên có viết tắt chính thức là **ICTU** (TUYỆT ĐỐI KHÔNG BỊA "TUIT").
   - Lưu ý về mã trường: Mỗi trường đại học tại Việt Nam có mã tuyển sinh riêng biệt (DTS, DTK, DTN, DTC, HUST, NEU...). TUYỆT ĐỐI KHÔNG dùng mã của trường này gán cho trường khác.
   - ĐH Bách khoa Hà Nội: HUST; ĐH Kinh tế Quốc dân: NEU; ĐH Ngoại thương: FTU; ĐH Công nghệ ĐHQGHN: UET; ĐH CNTT ĐHQG-HCM: UIT; Học viện BCVT: PTIT.
2. KHI NGƯỜI DÙNG HỎI "BẠN BIẾT TRƯỜNG [X] KHÔNG?":
   - Trả lời đúng trọng tâm về trường đó (Tên đầy đủ, cơ quan chủ quản/trực thuộc, viết tắt chính thức, mã trường, địa điểm, các ngành thế mạnh).
   - KHÔNG tự động vẽ bảng so sánh lan man dìm hàng trường với các trường khác nếu người dùng không yêu cầu so sánh.
   - Gợi mở thân thiện để hỗ trợ tra cứu: *"Bạn có muốn mình tra cứu điểm chuẩn năm 2025, phương thức xét tuyển hay học phí các ngành của trường không? Hãy nói cho mình biết ngành bạn quan tâm nhé!"*
3. ĐỊNH DẠNG BẢNG MARKDOWN:
   - Nếu trả lời có bảng biểu, BẮT BUỘC mỗi hàng phải nằm trên một dòng riêng biệt có ký tự xuống dòng (`\\n`). TUYỆT ĐỐI KHÔNG viết gộp nhiều hàng trên một dòng.
4. PHẠM VI & SỐ LIỆU:
   - CHỈ trả lời giáo dục, tuyển sinh, hướng nghiệp. Từ chối yêu cầu ngoài phạm vi.
   - KHÔNG bịa điểm chuẩn hay chỉ tiêu cụ thể. Nhắc người dùng yêu cầu tra cứu để hệ thống đọc từ cơ sở dữ liệu tuyển sinh."""

GROUNDED_LOCATION_SYSTEM_PROMPT = """Bạn là UniSearch AI — trợ lý thông minh và chuyên gia tư vấn tuyển sinh đại học tại Việt Nam.
Nhiệm vụ của bạn là giải đáp câu hỏi của học sinh về danh sách các trường đại học tại địa phương/khu vực.

QUY TẮC BẮT BUỘC VỀ CHỐNG ẢO GIÁC (ZERO-HALLUCINATION RULES):
1. BẠN CHỈ ĐƯỢC PHÉP TRẢ LỜI CÁC TRƯỜNG CÓ TÊN TRONG PHẦN "DỮ LIỆU ĐÃ XÁC THỰC" ĐƯỢC CUNG CẤP DƯỚI ĐÂY.
2. TUYỆT ĐỐI KHÔNG TỰ BỊA THÊM BẤT KỲ TRƯỜNG NÀO (Ví dụ: KHÔNG được đưa ĐH Mỏ - Địa chất hay ĐH Thủy Lợi vào Thái Nguyên).
3. ĐỐI VỚI MÃ TRƯỜNG (School Code): BẮT BUỘC DÙNG ĐÚNG MÃ ĐƯỢC LIỆT KÊ TRONG DỮ LIỆU (VD: Sư phạm là DTS, Kỹ thuật Công nghiệp là DTK, Nông Lâm là DTN, Y Dược là DTY, Kinh tế là DTE, Khoa học là DTZ, CNTT&TT là DTC, Ngoại ngữ là DTF). TUYỆT ĐỐI KHÔNG GÁN MÃ DTC CHO CÁC TRƯỜNG KHÁC.
4. NÊU RÕ BẢN CHẤT HỆ THỐNG: Nếu là Đại học Vùng (như Đại học Thái Nguyên, Đại học Đà Nẵng, Đại học Huế) thì phải gọi đúng là "Đại học Vùng trực thuộc Bộ GD&ĐT", TUYỆT ĐỐI KHÔNG gọi là "Đại học Quốc gia".
5. ĐỊNH DẠNG TRÌNH BÀY: Rõ ràng, mạch lạc theo từng nhóm trường. Nêu rõ Tên trường, Mã tuyển sinh chính thức, và các ngành thế mạnh.
6. Cuối câu trả lời, hãy gợi ý thân thiện: Người dùng muốn tra cứu điểm chuẩn hoặc học phí ngành nào của trường nào thì hỏi tiếp nhé!
"""


def _general_llm_answer(user_query: str, chat_history: list = None, grounding_data: str = None) -> str:
    """Gọi LLM trực tiếp để trả lời câu hỏi chung (có thể kèm grounding context nếu hỏi địa phương)."""
    if grounding_data:
        system_content = GROUNDED_LOCATION_SYSTEM_PROMPT + "\n\n" + grounding_data
        temp = 0.2
    else:
        system_content = GENERAL_SYSTEM_PROMPT
        temp = 0.5

    messages = [{"role": "system", "content": system_content}]
    if chat_history:
        for msg in chat_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"][:500]})
    messages.append({"role": "user", "content": user_query})

    content, error_info = call_llm(
        messages=messages,
        model_list=OPENROUTER_FALLBACK_MODELS,
        temperature=temp,
        max_tokens=1500,
    )
    if content:
        return content
    return error_info["message"] if error_info else "⚠️ Không thể xử lý câu hỏi lúc này."


def _general_llm_stream(user_query: str, chat_history: list = None, grounding_data: str = None):
    """Gọi LLM stream trực tiếp để trả lời câu hỏi chung (có grounding context nếu hỏi địa phương)."""
    if grounding_data:
        system_content = GROUNDED_LOCATION_SYSTEM_PROMPT + "\n\n" + grounding_data
        temp = 0.2
    else:
        system_content = GENERAL_SYSTEM_PROMPT
        temp = 0.5

    messages = [{"role": "system", "content": system_content}]
    if chat_history:
        for msg in chat_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"][:500]})
    messages.append({"role": "user", "content": user_query})

    return call_llm_stream(
        messages=messages,
        model=OPENROUTER_FALLBACK_MODELS[0],
        temperature=temp,
        max_tokens=1500,
    )


# ======== BƯỚC 2: GIAO VIỆC CHO ĐÚNG AGENT (Dispatch Only) ========
def dispatch_to_agent(classification: dict, user_query: str, chat_history: list = None) -> str:
    """
    Router Section 2: Dựa trên kết quả phân loại, giao việc cho đúng Agent.
    - RECOMMENDER → agents/recommender.py (Tra cứu điểm chuẩn)
    - COUNSELOR  → agents/counselor.py (Tư vấn hướng nghiệp)
    - GENERAL    → LLM trực tiếp (câu hỏi chung)
    """
    intent = classification.get("intent", "RECOMMENDER")
    standalone_query = classification.get("standalone_query", user_query)

    if intent == "GENERAL":
        loc_key = detect_location_query(user_query, classification.get("location"))
        grounding_data = get_grounding_context_for_location(loc_key) if loc_key else None
        return _general_llm_answer(user_query, chat_history, grounding_data=grounding_data)
    elif intent == "COUNSELOR":
        return tu_van_cv(score_table="", user_query=user_query)
    if intent == "RECOMMENDER":
        return query_diem_chuan(
            user_query=standalone_query,
            pre_extracted_school=classification.get("school", "ALL"),
            pre_extracted_location=classification.get("location", "ALL"),
            pre_extracted_keyword=classification.get("keyword", "ALL"),
            pre_extracted_year=classification.get("year", 0),
        )


def dispatch_to_agent_stream(classification: dict, user_query: str, chat_history: list = None):
    """
    Router Section 2 Streaming: Dựa trên kết quả phân loại, giao việc cho đúng Agent và trả về kết quả stream/structured response.
    """
    intent = classification.get("intent", "RECOMMENDER")

    if intent == "GENERAL":
        loc_key = detect_location_query(user_query, classification.get("location"))
        grounding_data = get_grounding_context_for_location(loc_key) if loc_key else None
        return _general_llm_stream(user_query, chat_history, grounding_data=grounding_data)
    elif intent == "COUNSELOR":
        return tu_van_cv_stream(score_table="", user_query=user_query)
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
def route_query(user_query: str, has_file: bool = False, chat_history: list = None) -> str:
    """Wrapper gọi classify → dispatch tuần tự."""
    classification = classify_query(user_query, has_file, chat_history)
    return dispatch_to_agent(classification, user_query, chat_history)

