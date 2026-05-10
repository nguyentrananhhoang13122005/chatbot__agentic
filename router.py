import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from agents.recommender import query_diem_chuan
from agents.counselor import tu_van_cv

# Tải biến môi trường
load_dotenv(override=True)
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
)

# ======== UNIFIED ANALYZER: 1 LLM CALL = Routing + Entity Extraction + Query Expansion ========
ANALYZER_PROMPT = """Bạn là BỘ PHÂN TÍCH TRUNG TÂM (Analyzer) cho Hệ thống AI Tư vấn Tuyển sinh Đại học.
Nhiệm vụ: Đọc lịch sử hội thoại + câu hỏi mới, thực hiện 3 việc trong 1 lần:

1. PHÂN LOẠI (intent):
   - "RECOMMENDER": Tra cứu điểm chuẩn, tìm trường/ngành, hỏi chỉ tiêu, thông tin tuyển sinh, so sánh trường, hỏi về ngành phù hợp dựa trên điểm số.
   - "COUNSELOR": Tư vấn hướng nghiệp, đánh giá hồ sơ năng lực, phân tích CV, định hướng sở thích/tính cách.
   LƯU Ý: Nếu câu hỏi đề cập tới trường/ngành CỤ THỂ (kể cả qua "trường này", "ngành đó") → luôn là RECOMMENDER.

2. TRÍCH XUẤT THỰC THỂ (entities — chỉ cho RECOMMENDER):
   - school: BẮT BUỘC trả về 2-4 từ khóa TIẾNG VIỆT dùng để tìm kiếm trong cơ sở dữ liệu, cách nhau bằng dấu phẩy. PHẢI DỊCH tên viết tắt tiếng Anh thành tiếng Việt (VD: user gõ "HUST" → trả về "Bách khoa, Hà Nội"; user gõ "NEU" → trả về "Kinh tế, Quốc dân"; user gõ "FTU" → trả về "Ngoại thương"; user gõ "PTIT" → trả về "Bưu chính, Viễn thông, BCVT"; user gõ "HUTECH" → trả về "Công nghệ, TPHCM"). KHÔNG kèm "Đại học", "Học viện", "Trường". Nếu user nói "trường này/trường đó" → dùng lịch sử để xác định tên trường thật. Nếu user gõ tên Việt rõ ràng (VD: "Bách khoa Hà Nội") thì giữ nguyên. Nếu không xác định được → để "ALL".
   - keyword: Tên ngành cụ thể (VD: "công nghệ thông tin"). Nếu user gõ mã ngành dạng số → ghi kèm sau dấu | (VD: "y khoa|7720101"). TUYỆT ĐỐI KHÔNG TỰ BỊA MÃ NGÀNH. Nếu hỏi chung "điểm các ngành" → ghi "điểm|chuẩn".
   - year: Năm cụ thể nếu user đề cập (VD: 2024). Nếu không → 0.

3. CHUẨN HOÁ CÂU HỎI (standalone_query):
   Viết lại câu hỏi thành câu độc lập, giải tham chiếu "trường này" → tên trường thật, "ngành đó" → tên ngành thật dựa trên lịch sử.

BẮT BUỘC trả về JSON duy nhất, KHÔNG giải thích:
{"intent": "RECOMMENDER", "school": "...", "keyword": "...", "year": 0, "standalone_query": "..."}"""


def route_query(user_query: str, has_file: bool = False, uploaded_file=None, chat_history: list = None):
    """
    Unified Analyzer: 1 LLM call thực hiện cả routing + entity extraction + query normalization.
    Giảm từ 2 API calls xuống 1, nhanh hơn ~50%.
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

    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": ANALYZER_PROMPT},
                {"role": "user", "content": user_message},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            max_tokens=300,
        )

        raw_response = completion.choices[0].message.content.strip()
        
        # Parse JSON response — xử lý trường hợp LLM wrap trong markdown
        json_str = raw_response
        if "```" in json_str:
            # Trích xuất JSON từ markdown code block
            import re
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', json_str, re.DOTALL)
            if match:
                json_str = match.group(1)
        
        analysis = json.loads(json_str)
        
        intent = analysis.get("intent", "RECOMMENDER").upper()
        school = analysis.get("school", "ALL")
        keyword = analysis.get("keyword", "ALL")
        year = analysis.get("year", 0)
        standalone_query = analysis.get("standalone_query", user_query)
        
        print(f"DEBUG [Analyzer]: intent={intent}, school='{school}', keyword='{keyword}', year={year}")
        print(f"DEBUG [Analyzer]: standalone_query='{standalone_query}'")
        
    except Exception as e:
        print(f"⚠️ Analyzer LLM error: {e}, falling back to defaults")
        # Fallback: dựa vào heuristic đơn giản
        intent = "COUNSELOR" if has_file else "RECOMMENDER"
        school = "ALL"
        keyword = "ALL"
        year = 0
        standalone_query = user_query

    # ======== ĐIỀU PHỐI ĐẾN ĐÚNG AGENT ========
    if intent == "COUNSELOR":
        return tu_van_cv(cv_file=uploaded_file, user_query=user_query)
    else:
        # Truyền entities đã trích xuất → recommender KHÔNG cần gọi LLM nữa
        return query_diem_chuan(
            user_query=standalone_query,
            pre_extracted_school=school,
            pre_extracted_keyword=keyword,
            pre_extracted_year=year,
        )
