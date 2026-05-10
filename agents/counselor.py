import PyPDF2
import os
from dotenv import load_dotenv
from openai import OpenAI

# Tải file .env từ môi trường (override=True bắt buộc nạp key mới)
load_dotenv(override=True)

# Khởi tạo client Groq (thay thế Cerebras — model 70B mạnh gấp 9 lần)
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
)

def doc_pdf(file_obj) -> str:
    """Hàm phụ trợ để đọc văn bản từ file PDF"""
    try:
        reader = PyPDF2.PdfReader(file_obj)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    except Exception as e:
        return f"[LỖI XỬ LÝ PDF]: {str(e)}"

# Hàm này dùng để đọc text CV và tư vấn hướng nghiệp
def tu_van_cv(cv_file, user_query: str) -> str:
    # 1. Đọc text từ file PDF truyền vào (Nếu học sinh có Upload)
    if cv_file is not None:
        cv_text = doc_pdf(cv_file)
        intro_text = f"Dưới đây là thông tin CV thu thập được của học sinh (dạng Text từ PDF):\n--------------------------------------------------\n{cv_text}\n--------------------------------------------------"
    else:
        intro_text = "Học sinh không đính kèm file CV hay hồ sơ nào. Bạn hãy tư vấn hoàn toàn dựa trên dữ liệu người dùng cung cấp trong câu hỏi."
    
    # 2. Xây dựng System Prompt tuyệt đỉnh để nhập vai chuyên gia
    system_prompt = f"""
Bạn là một CHUYÊN GIA HƯỚNG NGHIỆP VÀ TƯ VẤN TUYỂN SINH ĐẠI HỌC giàu kinh nghiệm.
Nhiệm vụ của bạn là nhận định và phân tích thắc mắc, sở thích, nguyện vọng (và Hồ sơ nếu có) của học sinh để đánh giá và định hướng ngành học/trường học phù hợp.

{intro_text}

TRUY VẤN TỪ HỌC SINH: 
"{user_query}"

YÊU CẦU TRẢ LỜI CỦA BẠN:
1. "PHÂN TÍCH VÀ ĐÁNH GIÁ" - Tóm tắt ngắn gọn các điểm sáng, sở thích, thế mạnh từ chia sẻ của học sinh. 
2. "ĐỀ XUẤT NGÀNH/TRƯỜNG" - Định hướng các ngành học liên quan nhất tới tính cách/sở thích đó, giải thích vì sao lại phù hợp? Mức độ rủi ro/khó khăn?
3. "LỜI KHUYÊN HÀNH ĐỘNG" - Đưa ra các lời khuyên cần làm gì để chuẩn bị tốt cho ngành nghệ thuật/sở thích đó.
Lưu ý: Ngôn từ mang tính động viên, khách quan, xưng "Tôi - Bạn/Em" thật gần gũi.
"""

    # --- CODE GỌI LLM qua OpenRouter ---
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_query
                }
            ],
            model="llama-3.3-70b-versatile", # Model Llama 3.3 70B qua Groq
            temperature=0.7,
            max_tokens=1500,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ Lỗi kết nối Cerebras API: {str(e)}"
