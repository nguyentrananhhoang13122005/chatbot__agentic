import os
import re
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

# Tải biến môi trường (override=True bắt buộc nạp key mới nhất bỏ qua cache Terminal)
load_dotenv(override=True)
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
)

# --- KHỞI TẠO DATABASE ---
# Load Data một lần duy nhất vào RAM khi ứng dụng khởi chạy (tăng tốc độ phản hồi)
csv_path = "data/data_tuyensinh_clean.csv"
verified_path = "data/data_diem_chuan_verified.csv"

try:
    if os.path.exists(csv_path):
        df_tuyensinh = pd.read_csv(csv_path, low_memory=False).fillna("")
    else:
        df_tuyensinh = None
        
    if os.path.exists(verified_path):
        df_verified = pd.read_csv(verified_path).fillna("")
    else:
        df_verified = None
except Exception as e:
    print("Lỗi load Database:", e)
    df_tuyensinh = None
    df_verified = None

# ======== HELPER: HYBRID SCHOOL MATCHER (BM25 + Fuzzy + Token Overlap) ========
import math
from difflib import SequenceMatcher
from collections import Counter

def _normalize_school_name(name: str) -> str:
    """Chuẩn hoá tên trường: bỏ số đầu, bỏ năm cuối, lowercase."""
    name = str(name).strip().lower()
    # Bỏ số thứ tự đầu dòng: "33. ĐH Bách khoa" → "đh bách khoa"
    name = re.sub(r'^\d+[\.\-\s]+', '', name)
    # Bỏ năm cuối: "ĐH ABC 2024" → "ĐH ABC"
    name = re.sub(r'\s*\d{4}\s*$', '', name)
    # Bỏ ký tự đặc biệt thừa
    name = re.sub(r'[_\-]+', ' ', name)
    # Map aliases
    name = re.sub(r'\bhn\b', 'hà nội', name)
    name = re.sub(r'\bhcm\b', 'hồ chí minh', name)
    name = re.sub(r'\btphcm\b', 'tp hồ chí minh', name)
    name = re.sub(r'\bđhqg\b', 'đại học quốc gia', name)
    
    return name.strip()

def _tokenize_vn(text: str) -> list:
    """Tách token tiếng Việt, bỏ stopwords ngắn."""
    tokens = re.split(r'[\s,\.\-/\(\)]+', text.lower())
    return [t for t in tokens if len(t) > 1]

def _bm25_score(query_tokens: list, doc_tokens: list, avg_dl: float, k1: float = 1.5, b: float = 0.75) -> float:
    """BM25 scoring thuần Python (không cần thư viện)."""
    if not doc_tokens or not query_tokens:
        return 0.0
    doc_len = len(doc_tokens)
    doc_counter = Counter(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        tf = doc_counter.get(qt, 0)
        if tf > 0:
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / max(avg_dl, 1))
            score += numerator / denominator
    return score

def _fuzzy_score(query: str, school_name: str) -> float:
    """Fuzzy matching dùng difflib (built-in Python, không cần cài gì thêm)."""
    return SequenceMatcher(None, query.lower(), school_name.lower()).ratio()

def _token_overlap_score(query_tokens: list, school_name_lower: str) -> float:
    """Token overlap score (CẢI TIẾN từ logic cũ): đếm % token query nằm trong tên trường."""
    if not query_tokens:
        return 0.0
    hits = sum(1 for kw in query_tokens if kw in school_name_lower)
    return hits / len(query_tokens)  # Chuẩn hoá về 0-1

def find_best_school_match(truong_query: str, list_of_schools: list, min_confidence: float = 0.20) -> str:
    """
    Hybrid School Matcher: Kết hợp 3 thuật toán để tìm trường chính xác nhất.
    - BM25: Tìm kiếm theo tần suất từ khoá (giỏi với keyword chính xác)
    - Fuzzy: Tìm kiếm theo chuỗi tương đồng (giỏi với lỗi chính tả, viết tắt)
    - Token Overlap: Logic cũ đã chứng minh ổn định

    Returns: Tên trường match tốt nhất, hoặc None nếu không đủ confident.
    """
    if not list_of_schools or truong_query == "ALL":
        return None
    
    query_normalized = _normalize_school_name(truong_query)
    query_tokens = _tokenize_vn(query_normalized)
    
    if not query_tokens:
        return None
    
    # Tính avg document length cho BM25
    all_doc_tokens = [_tokenize_vn(_normalize_school_name(s)) for s in list_of_schools]
    avg_dl = sum(len(dt) for dt in all_doc_tokens) / max(len(all_doc_tokens), 1)
    
    scored = []
    for i, school in enumerate(list_of_schools):
        school_normalized = _normalize_school_name(school)
        doc_tokens = all_doc_tokens[i]
        
        # === 3 tín hiệu scoring ===
        s_bm25 = _bm25_score(query_tokens, doc_tokens, avg_dl)
        s_fuzzy = _fuzzy_score(query_normalized, school_normalized)
        s_token = _token_overlap_score(query_tokens, school_normalized)
        
        # === Combined Score (weighted) ===
        # BM25 giỏi exact keyword, Fuzzy giỏi partial/typo, Token giỏi substring
        combined = (s_bm25 * 0.4) + (s_fuzzy * 0.3) + (s_token * 0.3)
        
        scored.append((school, combined, s_bm25, s_fuzzy, s_token))
    
    # Sắp xếp theo điểm giảm dần
    scored.sort(key=lambda x: x[1], reverse=True)
    
    if scored and scored[0][1] >= min_confidence:
        best = scored[0]
        print(f"DEBUG [Matcher]: '{truong_query}' → '{best[0]}' (combined={best[1]:.3f}, bm25={best[2]:.3f}, fuzzy={best[3]:.3f}, token={best[4]:.3f})")
        # Log runner-up để debug nếu cần
        if len(scored) > 1 and scored[1][1] > 0:
            runner = scored[1]
            print(f"DEBUG [Matcher]: Runner-up: '{runner[0]}' (combined={runner[1]:.3f})")
        return best[0]
    
    print(f"DEBUG [Matcher]: No match for '{truong_query}' (best_score={scored[0][1]:.3f} < threshold={min_confidence})" if scored else f"DEBUG [Matcher]: Empty school list")
    return None

# ======== HELPER: SMART OCR CLEANER (Làm sạch dữ liệu OCR trước khi gửi LLM) ========
def clean_ocr_for_llm(filtered_df: pd.DataFrame) -> str:
    """
    Chiến thuật: KHÔNG cố parse bảng OCR bằng Regex.
    1. Nối mỗi dòng CSV thành text, loại bỏ rác OCR bị đảo ngược
    2. Tìm khu vực "điểm trúng tuyển" (section 11.2) — nơi chứa bảng điểm
    3. Gửi text đã sạch cho LLM đọc
    """
    if filtered_df.empty:
        return "Không tìm thấy dữ liệu."

    # Bước 1: Nối mỗi dòng thành text, bỏ tên trường (cột đầu) 
    row_texts = []
    for _, row in filtered_df.iterrows():
        vals = [str(v).strip() for v in row.values[1:] if str(v).strip()]
        if vals:
            row_texts.append(" | ".join(vals))
    
    # Bước 2: Lọc rác OCR MẠNH TAY
    clean_lines = []
    # Ký tự rác đặc trưng của OCR bị lật/đảo
    garbage_chars = set("{}[]'`~€£¥₹ÒẸỊỌỌBSLOIuenqpd")
    
    for t in row_texts:
        # Loại bỏ HIDDEN_CODE trước
        t_clean = re.sub(r'\[HIDDEN_CODE:\s*\d+\]', '', t).strip()
        if not t_clean or len(t_clean) < 5:
            continue
        
        # Đếm ký tự Việt Nam thường (chữ cái + số + dấu)
        vn_chars = sum(1 for c in t_clean if c.isalnum() or c.isspace() or c in '|./,()-:;+')
        ratio = vn_chars / max(len(t_clean), 1)
        
        # Kiểm tra xem dòng có phải OCR bị lật (chứa nhiều ký tự rác liên tiếp)
        garbage_count = sum(1 for c in t_clean if c in garbage_chars)
        garbage_ratio = garbage_count / max(len(t_clean), 1)
        
        # Giữ dòng nếu: tỉ lệ ký tự hợp lệ > 70% VÀ tỉ lệ rác < 15%
        if ratio > 0.70 and garbage_ratio < 0.15:
            clean_lines.append(t_clean)
    
    if not clean_lines:
        return "Không tìm thấy dữ liệu có ý nghĩa."
    
    # Bước 3: Tìm khu vực ĐIỂM TRÚNG TUYỂN
    # QUAN TRỌNG: Scan từ ĐẦU đến CUỐI, ưu tiên section 11.2 (chứa bảng điểm chuẩn thực)
    # Section 11.2 LUÔN nằm ở CUỐI tài liệu → lấy match CUỐI CÙNG
    score_section_start = -1
    
    for i, line in enumerate(clean_lines):
        line_lower = line.lower()
        # Pattern 1: Section "11. Thông tin tuyển sinh của 2 năm gần nhất"
        if '11.' in line and ('tuyển sinh' in line_lower or 'năm gần' in line_lower):
            score_section_start = i  # Ghi đè lên match cũ → luôn lấy match cuối
        # Pattern 2: "11.2. Điểm trúng tuyển" (chính xác nhất)
        elif '11.2' in line and 'điểm' in line_lower:
            score_section_start = max(0, i - 2)  # Lấy thêm 2 dòng header
        # Pattern 3: Dòng header bảng điểm (chứa cả 3 từ khóa)
        elif 'chỉ tiêu' in line_lower and 'nhập học' in line_lower and 'điểm' in line_lower:
            score_section_start = i  # Ghi đè
        # Pattern 4: "8.2. Điểm trúng tuyển" (một số trường dùng section 8 thay vì 11)
        elif ('8.2' in line or '3.2' in line) and 'điểm' in line_lower and 'trúng' in line_lower:
            score_section_start = max(0, i - 1)

    # Nếu tìm được section điểm, ưu tiên lấy phần đó
    if score_section_start >= 0:
        priority_lines = clean_lines[score_section_start:min(len(clean_lines), score_section_start + 150)]
        # Ghép thêm phần thông tin chung (giới hạn 15 dòng)
        general_info = clean_lines[:min(score_section_start, 15)]
        result = "=== THÔNG TIN CHUNG ===\n" + "\n".join(general_info[:15])
        result += "\n\n=== BẢNG ĐIỂM TRÚNG TUYỂN ===\n" + "\n".join(priority_lines)
    else:
        # Không tìm thấy section điểm → gửi toàn bộ dữ liệu sạch
        result = "\n".join(clean_lines[:120])
    
    return result

# ======== HÀM CHÍNH ========
def query_diem_chuan(user_query: str, pre_extracted_school: str = "ALL", pre_extracted_keyword: str = "ALL", pre_extracted_year: int = 0) -> str:
    if df_tuyensinh is None or df_tuyensinh.empty:
        return "⚠️ Dữ liệu tuyển sinh chưa sẵn sàng. Hãy đảm bảo file tiến trình ETL đã cào dữ liệu thành công."

    # ======== BƯỚC 1: NHẬN THỰC THỂ TỪ ROUTER (Bỏ qua LLM extraction) ======== 
    truong = pre_extracted_school
    tu_khoa = pre_extracted_keyword
    nam = pre_extracted_year
    
    print(f"DEBUG [Recommender]: truong='{truong}', tu_khoa='{tu_khoa}', nam='{nam}'")

    # ======== BƯỚC 1.5: TRA CỨU LỚP 1 (DỮ LIỆU SẠCH - VERIFIED DATABASE) ========
    if df_verified is not None and not df_verified.empty and truong != "ALL":
        list_of_verified_schools = df_verified['Trường'].dropna().unique().tolist()
        best_school_vf = find_best_school_match(truong, list_of_verified_schools)
        
        vf_school = pd.DataFrame()
        if best_school_vf:
            vf_school = df_verified[df_verified['Trường'] == best_school_vf]
        
        if not vf_school.empty:
            vf_match = pd.DataFrame()
            if tu_khoa != "ALL" and not ('điểm' in tu_khoa.lower() or 'chuẩn' in tu_khoa.lower()):
                major_keywords = [kw.strip() for kw in tu_khoa.split('|') if kw.strip()]
                code_keywords = [kw for kw in major_keywords if kw.isdigit()]
                text_keywords = [kw for kw in major_keywords if not kw.isdigit()]
                
                if code_keywords:
                    major_pattern = '|'.join(code_keywords)
                    vf_match = vf_school[vf_school['Mã ngành'].astype(str).str.contains(major_pattern, case=False, na=False)]
                
                if vf_match.empty and text_keywords:
                    major_pattern = '|'.join(text_keywords)
                    vf_match = vf_school[vf_school['Tên ngành'].astype(str).str.contains(major_pattern, case=False, na=False)]
            
            # SCHOOL-LEVEL OVERRIDE
            if vf_match.empty:
                vf_match = vf_school
                
            year_warning = ""
            if nam > 0 and 'Năm' in vf_match.columns:
                # Ép kiểu an toàn để so sánh
                vf_match['Năm_Num'] = pd.to_numeric(vf_match['Năm'], errors='coerce').fillna(0)
                vf_match_year = vf_match[vf_match['Năm_Num'] == nam]
                
                if not vf_match_year.empty:
                    vf_match = vf_match_year
                else:
                    try:
                        latest_year = vf_match['Năm_Num'].max()
                        if latest_year > 0:
                            vf_match = vf_match[vf_match['Năm_Num'] == latest_year]
                            year_warning = f"⚠️ *Lưu ý: Không tìm thấy dữ liệu điểm chuẩn năm {nam}, hệ thống tự động hiển thị dữ liệu năm gần nhất ({int(latest_year)}).* \n\n"
                    except Exception as e:
                        print("DEBUG [Year Filter Fallback Error]:", e)
                        
                vf_match = vf_match.drop(columns=['Năm_Num'], errors='ignore')
            
            if not vf_match.empty:
                vf_match = vf_match.head(30)
                markdown_table = "| Trường | Mã ngành | Tên ngành | Năm | Phương thức xét tuyển | Điểm chuẩn | Chỉ tiêu |\n"
                markdown_table += "|---|---|---|---|---|---|---|\n"
                for _, row in vf_match.iterrows():
                    markdown_table += f"| {row['Trường']} | {row['Mã ngành']} | {row['Tên ngành']} | {row['Năm']} | {row['Phương thức xét tuyển']} | **{row['Điểm chuẩn']}** | {row['Chỉ tiêu']} |\n"
                
                return f"🤖 **[Recommender Agent] (Dữ liệu Đã Kiểm Chứng Chính Xác 100%)**\n\nChào bạn! Dưới đây là thông tin tuyển sinh chính xác cho trường/ngành bạn đang quan tâm:\n\n{year_warning}{markdown_table}\n\n*Đây là dữ liệu đã được hệ thống xác thực trực tiếp. Bỏ qua phân tích OCR để đảm bảo không sai lệch.*"

    # ======== BƯỚC 2: PANDAS DATA ENGINE TÌM KIẾM (LỚP 2 - FALLBACK OCR) ======== 
    filtered_df = df_tuyensinh.copy()
    
    # Lọc theo trường bằng Token Scoring
    if truong != "ALL":
        list_of_all_schools = filtered_df['Tên Trường'].dropna().unique().tolist()
        best_school_ocr = find_best_school_match(truong, list_of_all_schools)
        
        if best_school_ocr:
            filtered_df = filtered_df[filtered_df['Tên Trường'] == best_school_ocr]
            print(f"DEBUG: Matched school = '{best_school_ocr}' ({len(filtered_df)} rows)")
        else:
            filtered_df = pd.DataFrame()
        
    # Lọc theo Từ khóa ngành — CHỈ lọc khi người dùng hỏi về 1 NGÀNH CỤ THỂ
    # Nếu tu_khoa chứa 'điểm', 'chuẩn', 'các ngành', 'tất cả' → KHÔNG lọc, lấy toàn bộ dữ liệu trường
    skip_keyword_filter = False
    if tu_khoa == "ALL":
        skip_keyword_filter = True
    else:
        generic_markers = ['điểm', 'chuẩn', 'các ngành', 'tất cả', 'toàn bộ', 'danh sách']
        if any(m in tu_khoa.lower() for m in generic_markers):
            skip_keyword_filter = True
    
    if not skip_keyword_filter and not filtered_df.empty:
        row_strings = filtered_df.astype(str).apply(lambda row: ' | '.join(row.values), axis=1)
        
        processed_keywords = []
        for kw in tu_khoa.split('|'):
            kw = kw.strip()
            if kw.isdigit():
                processed_keywords = [kw]
                break
            elif kw:
                processed_keywords.append(kw.replace(' ', '.*'))
        regex_pattern = '|'.join(processed_keywords)
        
        match_indices = filtered_df.index[row_strings.str.contains(regex_pattern, case=False, na=False, regex=True)]
        
        if len(match_indices) > 0:
            context_indices = []
            for idx in match_indices:
                loc = filtered_df.index.get_loc(idx)
                
                # DYNAMIC HEADER RECOVERY
                for j in range(loc - 1, max(-1, loc - 30), -1):
                    row_val = row_strings.iloc[j].lower()
                    if 'chỉ tiêu' in row_val or 'điểm' in row_val or 'ngành' in row_val or 'stt' in row_val:
                        context_indices.append(j)
                        break
                
                start = max(0, loc - 4)
                end = min(len(filtered_df), loc + 5)
                context_indices.extend(range(start, end))
            
            context_indices = sorted(list(set(context_indices)))
            filtered_df = filtered_df.iloc[context_indices]
            
    # ======== BƯỚC 2.5: SMART OCR CLEANER (LÀM SẠCH, KHÔNG PARSE) ========
    context_data = clean_ocr_for_llm(filtered_df)
    
    # Giới hạn token
    if len(context_data) > 10000:
        context_data = context_data[:5000] + "\n...[Dữ liệu bị lược bỏ do giới hạn Token]...\n" + context_data[-5000:]
        
    # ======== BƯỚC 3: LLM SYNTHESIS (PROMPT CỨNG - ĐA DẠNG FORMAT) ========
    answer_prompt = f"""Bạn là CHUYÊN GIA TƯ VẤN TUYỂN SINH. Trả lời câu hỏi dựa HOÀN TOÀN trên DỮ LIỆU bên dưới.

CÂU HỎI: "{user_query}"

QUAN TRỌNG — DỮ LIỆU BÊN DƯỚI ĐƯỢC TRÍCH TỪ PDF QUA OCR, MỖI TRƯỜNG CÓ FORMAT BẢNG KHÁC NHAU:
- Có trường dùng: Chỉ tiêu | Số nhập học | Điểm trúng tuyển
- Có trường dùng: Phương thức | Chỉ tiêu | Số nhập học | Điểm X/30
- Có trường dùng: Tổ hợp | Điểm trúng tuyển | Số trúng tuyển
- Có trường dùng điểm dạng thập phân (23.5, 22.75), có trường dùng X/30 (19/30, 15/30), có trường dùng X,00 (18,00)

CÁCH ĐỌC ĐÚNG:
1. ĐỌC DÒNG HEADER TRƯỚC — dòng chứa "Chỉ tiêu", "Số nhập học", "Điểm trúng tuyển" cho bạn biết thứ tự cột.
2. SAU ĐÓ đọc các dòng dữ liệu theo thứ tự cột đó.
3. ĐIỂM TRÚNG TUYỂN thường là cột CUỐI CÙNG trong mỗi nhóm (Năm 2024, Năm 2023).

QUY TẮC OUTPUT BẮT BUỘC:
1. BẮT BUỘC liệt kê TẤT CẢ ngành có trong dữ liệu dưới dạng BẢNG MARKDOWN.
2. KHÔNG viết bài luận, KHÔNG quảng cáo trường, KHÔNG bịa thông tin.
3. Cấu trúc bảng: | Mã ngành | Tên ngành | Phương thức | Điểm chuẩn | Chỉ tiêu |
4. Nếu dữ liệu có nhiều năm (2023, 2024), ghi rõ năm nào. {f'ĐẶC BIỆT LƯU Ý: Người dùng đang muốn tìm năm {nam}. Hãy ưu tiên báo cáo số liệu của năm {nam}. Nếu không có năm {nam}, hãy CẢNH BÁO rõ là không có và báo cáo năm gần nhất.' if nam > 0 else ''}
5. Nếu KHÔNG tìm thấy dữ liệu điểm: Trả lời "Không tìm thấy dữ liệu điểm trúng tuyển."
6. Câu hỏi về thông tin chung (vị trí, học phí): Được dùng kiến thức chung, trả lời ngắn gọn.

DỮ LIỆU:
{context_data}"""
    
    try:
        answer_res = client.chat.completions.create(
            messages=[{"role": "user", "content": answer_prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,  # Giảm temperature để LLM bám sát dữ liệu
        ).choices[0].message.content
        return f"🤖 **[Recommender Agent]**\n\n{answer_res}"
    except Exception as e:
        return f"⚠️ Lỗi suy luận AI: {e}"
