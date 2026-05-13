import PyPDF2
import os
import pandas as pd
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
    """Tool 1: Đọc văn bản từ file PDF (CV/Hồ sơ)"""
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

def retrieve_main_data() -> str:
    """Tool 2: Truy xuất và lấy dữ liệu từ thư mục data chính (Tuân thủ Architecture)"""
    try:
        csv_path = "data/data_diem_chuan_verified.csv"
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            # Nhóm danh sách các trường và ngành có sẵn trong DB để Counselor đề xuất chính xác
            grouped = df.groupby('Trường')['Tên ngành'].apply(lambda x: list(set(x))).to_dict()
            
            db_info = "DỮ LIỆU NGÀNH HỌC THỰC TẾ TRONG DATABASE CHÍNH (Hãy ưu tiên đề xuất các trường/ngành này):\n"
            for school, majors in list(grouped.items())[:10]: # Lấy top 10 trường
                db_info += f"- {school}: {', '.join(majors[:8])}...\n"
            return db_info
    except Exception as e:
        return f"[LỖI DATABASE]: {str(e)}"
    return ""

# Hàm này dùng để đọc text CV và tư vấn hướng nghiệp
def tu_van_cv(cv_file, user_query: str) -> str:
    # 1. Kích hoạt Tool 1 (Xử lý PDF CV)
    if cv_file is not None:
        cv_text = doc_pdf(cv_file)
        intro_text = f"Dưới đây là thông tin CV thu thập được của học sinh (dạng Text từ PDF):\n--------------------------------------------------\n{cv_text}\n--------------------------------------------------"
    else:
        intro_text = "Học sinh không đính kèm file CV hay hồ sơ nào. Bạn hãy tư vấn hoàn toàn dựa trên dữ liệu người dùng cung cấp trong câu hỏi."
    
    # 2. Kích hoạt Tool 2 (Truy xuất dữ liệu Data chính)
    main_db_context = retrieve_main_data()
    
    # 3. Xây dựng System Prompt kết hợp dữ liệu từ cả 2 Tool
    system_prompt = f"""
Bạn là một CHUYÊN GIA HƯỚNG NGHIỆP VÀ TƯ VẤN TUYỂN SINH ĐẠI HỌC giàu kinh nghiệm.
Nhiệm vụ của bạn là nhận định và phân tích thắc mắc, sở thích, nguyện vọng (và Hồ sơ nếu có) của học sinh để đánh giá và định hướng ngành học/trường học phù hợp.

{main_db_context}

{intro_text}

TRUY VẤN TỪ HỌC SINH: 
"{user_query}"

YÊU CẦU TRẢ LỜI CỦA BẠN:
1. Chỉ tập trung trả lời đúng trọng tâm câu hỏi, TUYỆT ĐỐI không đưa ra thông tin thừa.
2. "PHÂN TÍCH VÀ ĐÁNH GIÁ" - Tóm tắt ngắn gọn các điểm sáng, sở thích, thế mạnh từ chia sẻ của học sinh. 
3. "ĐỀ XUẤT NGÀNH/TRƯỜNG" - Định hướng các ngành học liên quan nhất tới tính cách/sở thích đó, giải thích vì sao lại phù hợp? Ưu tiên sử dụng các trường/ngành có trong DATABASE CHÍNH mà tôi đã cung cấp bên trên.
4. "LỜI KHUYÊN HÀNH ĐỘNG" - Đưa ra các lời khuyên cần làm gì để chuẩn bị tốt cho ngành/sở thích đó.
5. "ĐỀ XUẤT CÂU HỎI" - Ở cuối câu trả lời, LUÔN đề xuất 2-3 câu hỏi chủ đề liên quan để học sinh có thể hỏi tiếp.
Lưu ý: Ngôn từ mang tính động viên, khách quan, xưng "Tôi - Bạn/Em" thật gần gũi. Bắt đầu câu trả lời bằng 🤖 **[Counselor Agent]**.
"""

    # --- CODE GỌI LLM qua Groq ---
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
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=1500,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ Lỗi kết nối AI: {str(e)}"
