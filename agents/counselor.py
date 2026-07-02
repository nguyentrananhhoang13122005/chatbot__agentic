import os
import sys
import pandas as pd
from llm_client import OPENROUTER_FALLBACK_MODELS, call_llm, call_llm_stream

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ======== TOOL 2: TRUY XUAT DATABASE ========
def retrieve_main_data() -> str:
    """Tool 2: Truy xuat va lay du lieu tu thu muc data chinh"""
    try:
        csv_path = "data/data_diem_chuan_verified.csv"
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            grouped = df.groupby('Trường')['Tên ngành'].apply(lambda x: list(set(x))).to_dict()

            db_info = "DỮ LIỆU NGÀNH HỌC THỰC TẾ TRONG DATABASE CHÍNH (Hãy ưu tiên đề xuất các trường/ngành này):\n"
            for school, majors in list(grouped.items())[:10]:
                db_info += f"- {school}: {', '.join(majors[:8])}...\n"
            return db_info
    except Exception as e:
        return f"[LOI DATABASE]: {str(e)}"
    return ""


def _build_system_prompt(score_table: str, user_query: str, main_db_context: str) -> str:
    """Helper xây dựng system prompt chung cho các mode."""
    if score_table:
        data_section = f"""BẢNG ĐIỂM HỌC BẠ:
{score_table}

Dựa vào bảng điểm trên, hãy xác định:
- Môn nào điểm CAO (>= 8.0) → đây là thế mạnh
- Môn nào điểm THẤP (< 6.5) → cần cải thiện
Rồi đề xuất ngành phù hợp với thế mạnh đó."""
    else:
        data_section = "Học sinh không cung cấp bảng điểm học bạ. Tư vấn dựa hoàn toàn trên nội dung câu hỏi."

    system_prompt = f"""Bạn là CHUYÊN GIA TƯ VẤN TUYỂN SINH ĐẠI HỌC Việt Nam.

{main_db_context}

{data_section}

CÂU HỎI CỦA HỌC SINH: "{user_query}"

YÊU CẦU TRẢ LỜI:
1. **PHÂN TÍCH ĐIỂM MẠNH & HỌC BẠ** (nếu có bảng điểm):
   - Hiển thị bảng Môn học | Điểm đầy đủ
   - Xác định rõ MÔN HỌC THẾ MẠNH NHẤT (>= 8.0) và MÔN YẾU (< 6.5). Phân tích chi tiết năng lực dựa trên tổ hợp các môn mạnh.
2. **ĐỀ XUẤT TRƯỜNG/NGÀNH TỐI ƯU**:
   - Dựa vào Môn Thế Mạnh Nhất, tư vấn cụ thể tại sao ngành/trường đó lại phù hợp.
   - Toán/Lý/Hóa/Tin mạnh → CNTT, Kỹ thuật, Khoa học tự nhiên
   - Văn/Sử/Địa mạnh → Luật, Báo chí, Xã hội học, Ngôn ngữ
   - Sinh/Hóa mạnh → Y dược, Công nghệ sinh học, Nông lâm
   - Anh/Ngoại ngữ khác mạnh → Ngôn ngữ học, Quan hệ quốc tế, Du lịch
   - Năng khiếu mạnh (Vẽ/Hát/Thể thao) → Kiến trúc, Nghệ thuật, Báo chí, Thể dục thể thao
   - Đặc biệt, giải thích lý do trường gợi ý phù hợp dựa trên điểm chuẩn và phổ điểm của thí sinh.
   Ưu tiên trường/ngành có trong DATABASE CHÍNH.
3. **LỜI KHUYÊN & CHIẾN LƯỢC** - 2-3 bước chuẩn bị hồ sơ hoặc chọn nguyện vọng (An toàn, Thử thách).
4. **GỢI Ý CÂU HỎI** - 2-3 câu hỏi liên quan để hỏi tiếp.

Tuyệt đối KHÔNG đưa thông tin thừa. Xưng "Tôi - Bạn/Em". Bắt đầu bằng**[Counselor Agent]**.
"""
    return system_prompt


def build_counselor_system_prompt(score_table: str, user_query: str, main_db_context: str) -> str:
    return _build_system_prompt(score_table, user_query, main_db_context)


def counselor_respond_stream_from_prompt(system_prompt: str, user_query: str):
    return call_llm_stream(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_query}
        ],
        model=OPENROUTER_FALLBACK_MODELS[0],
        temperature=0.3,
        max_tokens=2000,
    )


def tu_van_cv(score_table: str, user_query: str, stream_output: bool = False) -> str:
    # 1. Truy xuất dữ liệu & Build Prompt
    main_db_context = retrieve_main_data()
    system_prompt = build_counselor_system_prompt(score_table, user_query, main_db_context)

    # 2. Gọi LLM phân tích và tư vấn
    if stream_output:
        return counselor_respond_stream_from_prompt(system_prompt, user_query)

    answer, error_info = call_llm(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_query}
        ],
        model_list=OPENROUTER_FALLBACK_MODELS,
        temperature=0.3,
        max_tokens=2000,
    )
    if answer:
        return answer
    return f"**[Counselor Agent]**\n\n{error_info['message'] if error_info else '⚠️ Hệ thống AI tạm thời không khả dụng. Vui lòng thử lại sau.'}"


def tu_van_cv_stream(score_table: str, user_query: str):
    response = tu_van_cv(score_table=score_table, user_query=user_query, stream_output=True)
    if isinstance(response, str):
        yield response
        return
    yield from response
