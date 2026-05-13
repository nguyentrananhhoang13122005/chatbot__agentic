import os
import re
import pandas as pd
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
from openai import OpenAI

# Tải biến môi trường (override=True bắt buộc nạp key mới nhất bỏ qua cache Terminal)
load_dotenv(override=True)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# --- KHỞI TẠO DATABASE ---
# Load Data một lần duy nhất vào RAM khi ứng dụng khởi chạy (tăng tốc độ phản hồi)
csv_path = "data/data_tuyensinh_clean.csv"
verified_path = "data/data_diem_chuan_verified.csv"
dats_2026_path = "data/data_tuyensinh_2026.csv"

try:
    if os.path.exists(csv_path):
        df_tuyensinh = pd.read_csv(csv_path, low_memory=False).fillna("")
    else:
        df_tuyensinh = None
        
    if os.path.exists(verified_path):
        df_verified = pd.read_csv(verified_path).fillna("")
        print(f"✅ [Recommender] Verified DB loaded: {len(df_verified)} dòng, {df_verified['Trường'].nunique()} trường")
    else:
        df_verified = None
    
    if os.path.exists(dats_2026_path):
        df_2026 = pd.read_csv(dats_2026_path).fillna("")
        print(f"✅ [Recommender] DATS 2026 loaded: {len(df_2026)} trường")
    else:
        df_2026 = None
except Exception as e:
    print("Lỗi load Database:", e)
    df_tuyensinh = None
    df_verified = None
    df_2026 = None

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

def find_matching_schools(truong_query: str, school_list: list, min_confidence: float = 0.5, strict: bool = False) -> list:
    """
    Hybrid School Matcher (Multi-Result): Trả về DANH SÁCH tất cả trường khớp.
    Khi người dùng hỏi 'Bách Khoa' → trả về cả Hà Nội, Đà Nẵng, TPHCM.
    
    Returns: List[str] — danh sách tên trường khớp (có thể rỗng).
    """
    if not school_list or truong_query == "ALL":
        return []
    
    query_normalized = _normalize_school_name(truong_query)
    query_tokens = _tokenize_vn(query_normalized)
    
    if not query_tokens:
        return []
    
    # Tính avg document length cho BM25
    all_doc_tokens = [_tokenize_vn(_normalize_school_name(s)) for s in school_list]
    avg_dl = sum(len(dt) for dt in all_doc_tokens) / max(len(all_doc_tokens), 1)
    
    scored = []
    for i, school in enumerate(school_list):
        school_normalized = _normalize_school_name(school)
        doc_tokens = all_doc_tokens[i]
        
        s_bm25 = _bm25_score(query_tokens, doc_tokens, avg_dl)
        s_fuzzy = _fuzzy_score(query_normalized, school_normalized)
        s_token = _token_overlap_score(query_tokens, school_normalized)
        combined = (s_bm25 * 0.4) + (s_fuzzy * 0.3) + (s_token * 0.3)
        
        scored.append((school, combined, s_bm25, s_fuzzy, s_token))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    
    if not scored or scored[0][1] < min_confidence:
        print(f"DEBUG [Matcher]: No match for '{truong_query}'")
        return []
    
    best_score = scored[0][1]
    
    # Ưu tiên lấy các trường có token_overlap = 1.0 (TẤT CẢ từ khóa đều xuất hiện)
    # Ví dụ: "bách khoa" → cả "bách" và "khoa" đều phải có trong tên trường
    full_matches = [(s, c, t) for s, c, _, _, t in scored if t >= 1.0 and c >= min_confidence]
    
    if full_matches:
        matches = [s for s, _, _ in full_matches]
        for s, c, t in full_matches:
            print(f"DEBUG [Matcher]: '{truong_query}' → '{s}' (combined={c:.3f}, token={t:.3f})")
        return matches
    
    # Nếu strict=True → chỉ trả về full match, không fallback
    if strict:
        return []
    
    # Nếu không có full match, lấy top-1 (trường điểm cao nhất)
    if scored[0][1] >= min_confidence:
        print(f"DEBUG [Matcher]: Fallback top-1: '{scored[0][0]}' (combined={scored[0][1]:.3f})")
        return [scored[0][0]]
    
    return []

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

    # ======== GUARD 0: KIỂM TRA ĐA TRƯỜNG — PHẢI TRƯỚC MỌI LOOKUP ========
    # Dùng verified DB (290 trường) để phát hiện ambiguity
    if df_verified is not None and not df_verified.empty and truong != "ALL":
        all_schools = df_verified['Trường'].dropna().unique().tolist()
        all_matches = find_matching_schools(truong, all_schools)
        
        # Nếu nhiều trường khớp → HỎI LẠI, không đoán mò
        if len(all_matches) > 1:
            school_list_str = "\n".join([f"  {i+1}. **{s}**" for i, s in enumerate(all_matches)])
            return (
                f"🤖 **[Recommender Agent]**\n\n"
                f"Tôi tìm thấy **{len(all_matches)} trường** khớp với từ khóa **\"{truong}\"**:\n\n"
                f"{school_list_str}\n\n"
                f"👉 Bạn muốn xem thông tin trường nào? Hãy gõ tên cụ thể hơn nhé! "
                f"(VD: *\"{all_matches[0]}\"* hoặc *\"{all_matches[-1]}\"*)"
            )
    
    # ======== QUYẾT ĐỊNH DỮ LIỆU: 2026 DATS hay 2025 ĐIỂM CHUẨN? ========
    # Câu hỏi về "điểm chuẩn" → ưu tiên 2025 verified (có số liệu thực)
    # Câu hỏi về "tuyển sinh/phương thức/chỉ tiêu/ngành" → ưu tiên 2026 DATS
    query_lower = user_query.lower()
    is_score_query = any(kw in query_lower for kw in ['điểm chuẩn', 'điểm', 'bao nhiêu điểm', 'điểm trúng tuyển'])
    is_admission_query = any(kw in query_lower for kw in ['tuyển sinh', 'phương thức', 'chỉ tiêu', 'xét tuyển', 'điều kiện', 'hồ sơ', 'đăng ký'])
    
    # ======== BƯỚC 1: TRA CỨU DATS 2026 (cho câu hỏi tuyển sinh) ========
    # Chỉ dùng 2026 khi: (1) KHÔNG hỏi điểm chuẩn, hoặc (2) hỏi tuyển sinh/phương thức
    if df_2026 is not None and not df_2026.empty and truong != "ALL" and (is_admission_query or not is_score_query):
        list_2026 = df_2026['Trường'].dropna().unique().tolist()
        matched_2026 = find_matching_schools(truong, list_2026, strict=True)
        
        if len(matched_2026) == 1:
            school_2026 = matched_2026[0]
            row_2026 = df_2026[df_2026['Trường'] == school_2026].iloc[0]
            content_2026 = row_2026.get('Nội dung', '')
            
            if content_2026:
                print(f"DEBUG [Recommender]: Found 2026 DATS for '{school_2026}' ({len(content_2026)} chars)")
                
                llm_prompt_2026 = f"""Bạn là trợ lý tuyển sinh AI chuyên nghiệp cho Việt Nam.

CÂU HỎI CỦA NGƯỜI DÙNG: "{user_query}"

THÔNG TIN TUYỂN SINH NĂM 2026 CỦA TRƯỜNG {school_2026}:
{content_2026}

QUY TẮC TRẢ LỜI:
1. Trả lời CHÍNH XÁC câu hỏi dựa HOÀN TOÀN trên thông tin tuyển sinh năm 2026 ở trên. TUYỆT ĐỐI KHÔNG bịa thông tin. Chỉ tập trung trả lời đúng trọng tâm câu hỏi, TUYỆT ĐỐI không đưa ra thông tin thừa.
2. BẮT BUỘC ghi rõ đây là thông tin tuyển sinh **năm 2026** trong tiêu đề hoặc mở đầu.
3. Nếu hỏi về phương thức → liệt kê chi tiết các phương thức, điều kiện, chỉ tiêu.
4. Nếu hỏi về ngành → liệt kê danh sách ngành, mã ngành, tổ hợp môn xét tuyển.
5. Nếu hỏi chung → tóm tắt ngắn gọn.
6. Nếu người dùng hỏi về ĐIỂM CHUẨN nhưng dữ liệu 2026 chưa có → nói rõ: "Điểm chuẩn năm 2026 chưa được công bố. Dữ liệu hiện có là đề án tuyển sinh 2026."
7. Sử dụng Markdown (bảng, in đậm, danh sách). Trả lời tiếng Việt, chuyên nghiệp.
8. Ở cuối câu trả lời, LUÔN đề xuất 2-3 câu hỏi chủ đề liên quan để người dùng có thể hỏi tiếp."""

                for model_2026 in ["qwen/qwen3-8b", "llama-3.1-8b-instant"]:
                    try:
                        completion = client.chat.completions.create(
                            messages=[{"role": "user", "content": llm_prompt_2026}],
                            model=model_2026,
                            temperature=0.1,
                            max_tokens=3000,
                        )
                        llm_answer = completion.choices[0].message.content.strip()
                        return f"🤖 **[Recommender Agent]** — Trường: **{school_2026}** · Năm: **2026**\n\n{llm_answer}\n\n---\n*Nguồn: Đề án tuyển sinh chính thức năm 2026.*"
                    except Exception as e:
                        print(f"DEBUG [2026 LLM {model_2026}]: {e}")
                        continue

    # ======== BƯỚC 2: TRA CỨU DỮ LIỆU ĐIỂM CHUẨN 2025 (VERIFIED DATABASE) ========
    if df_verified is not None and not df_verified.empty and truong != "ALL":
        list_of_verified_schools = df_verified['Trường'].dropna().unique().tolist()
        matched_schools = find_matching_schools(truong, list_of_verified_schools)
        
        print(f"DEBUG [Recommender]: Matched {len(matched_schools)} schools: {matched_schools}")
        
        # (GUARD đa trường đã xử lý ở GUARD 0 phía trên)
        
        # ===== GUARD 2: Không tìm thấy trường nào =====
        if not matched_schools:
            vf_school = pd.DataFrame()
        else:
            vf_school = df_verified[df_verified['Trường'].isin(matched_schools)].copy()
        
        if not vf_school.empty:
            # --- Lọc theo ngành nếu user chỉ định ---
            vf_match = pd.DataFrame()
            has_specific_major = tu_khoa != "ALL" and not ('điểm' in tu_khoa.lower() or 'chuẩn' in tu_khoa.lower())
            
            if has_specific_major:
                major_keywords = [kw.strip() for kw in tu_khoa.split('|') if kw.strip()]
                code_keywords = [kw for kw in major_keywords if kw.isdigit()]
                text_keywords = [kw for kw in major_keywords if not kw.isdigit()]
                
                if code_keywords:
                    major_pattern = '|'.join(code_keywords)
                    vf_match = vf_school[vf_school['Mã ngành'].astype(str).str.contains(major_pattern, case=False, na=False)]
                
                if vf_match.empty and text_keywords:
                    major_pattern = '|'.join(text_keywords)
                    vf_match = vf_school[vf_school['Tên ngành'].astype(str).str.contains(major_pattern, case=False, na=False)]
            
            # ===== BƯỚC CUỐI: Dùng LLM để trả lời dựa trên dữ liệu =====
            # Thay vì dump bảng, AI đọc dữ liệu và trả lời đúng câu hỏi
            if vf_match.empty:
                vf_match = vf_school
            
            # --- Lọc theo năm ---
            if nam > 0 and 'Năm' in vf_match.columns:
                vf_match.loc[:, 'Năm_Num'] = pd.to_numeric(vf_match['Năm'], errors='coerce').fillna(0)
                vf_match_year = vf_match[vf_match['Năm_Num'] == nam]
                if not vf_match_year.empty:
                    vf_match = vf_match_year
                else:
                    latest_year = vf_match['Năm_Num'].max()
                    if latest_year > 0:
                        vf_match = vf_match[vf_match['Năm_Num'] == latest_year]
                vf_match = vf_match.drop(columns=['Năm_Num'], errors='ignore')
            
            if not vf_match.empty:
                school_name = matched_schools[0]
                
                # Bỏ các cột trống hoàn toàn (toàn NaN hoặc rỗng) để LLM và Fallback dễ xử lý
                vf_match = vf_match.replace('', pd.NA).dropna(axis=1, how='all')
                
                # Gửi TẤT CẢ dữ liệu cho LLM (tối đa 120 dòng — đủ cho hầu hết trường)
                data_sample = vf_match.head(120)
                export_cols = [c for c in ['Mã ngành','Tên ngành','Năm','Phương thức xét tuyển','Điểm chuẩn','Chỉ tiêu','Tổ hợp môn'] if c in data_sample.columns]
                data_context = data_sample[export_cols].to_csv(index=False, encoding='utf-8')
                
                # Tóm tắt thống kê
                stats = (
                    f"Tổng số ngành: {vf_match['Tên ngành'].nunique() if 'Tên ngành' in vf_match.columns else 0}. "
                    f"Phương thức: {', '.join(vf_match['Phương thức xét tuyển'].dropna().unique().tolist()) if 'Phương thức xét tuyển' in vf_match.columns else ''}. "
                )
                if 'Điểm chuẩn' in vf_match.columns:
                    stats += f"Điểm chuẩn: {vf_match['Điểm chuẩn'].min()} - {vf_match['Điểm chuẩn'].max()}."
                
                llm_prompt = f"""Bạn là trợ lý tuyển sinh AI chuyên nghiệp cho Việt Nam.

CÂU HỎI CỦA NGƯỜI DÙNG: "{user_query}"

DỮ LIỆU CHÍNH THỨC CỦA TRƯỜNG {school_name} (dạng CSV):
{data_context}

THỐNG KÊ: {stats}

QUY TẮC TRẢ LỜI:
1. Trả lời CHÍNH XÁC câu hỏi dựa HOÀN TOÀN trên dữ liệu trên. TUYỆT ĐỐI KHÔNG bịa thông tin. Chỉ tập trung trả lời đúng trọng tâm câu hỏi, TUYỆT ĐỐI không đưa ra thông tin thừa.
2. Dữ liệu trên là DỮ LIỆU CHÍNH THỨC từ trường — mọi phương thức xét tuyển đều do trường công bố.
   Lưu ý: Nhiều trường ở các tỉnh/thành khác (VD: Đà Nẵng, Huế) vẫn CHẤP NHẬN kết quả ĐGNL ĐHQG TPHCM hoặc ĐHQG Hà Nội. Đây là bình thường, KHÔNG phải lỗi dữ liệu.
3. Nếu hỏi về phương thức → liệt kê CÁC PHƯƠNG THỨC trong dữ liệu và số ngành áp dụng.
4. Nếu hỏi về điểm chuẩn ngành cụ thể → cho điểm chính xác theo từng phương thức.
5. Nếu hỏi chung chung → tóm tắt ngắn gọn.
6. Sử dụng Markdown (bảng, in đậm, danh sách). Trả lời tiếng Việt, chuyên nghiệp, thân thiện.
7. BẮT BUỘC ghi rõ NĂM CỤ THỂ của dữ liệu trong câu trả lời (VD: "Điểm chuẩn **năm 2025**"). Luôn nhấn mạnh năm ở tiêu đề hoặc đoạn mở đầu.
8. ĐẶC BIỆT LƯU Ý: Nếu người dùng hỏi thông tin KHÔNG CÓ trong bảng dữ liệu (ví dụ: người dùng hỏi "chỉ tiêu" nhưng dữ liệu chỉ có "điểm chuẩn"), BẮT BUỘC phải trả lời rõ: "Rất tiếc, dữ liệu hiện tại của trường này chưa có thông tin đó." TUYỆT ĐỐI KHÔNG tự ý liệt kê toàn bộ điểm chuẩn thay thế khi người dùng không hỏi.
9. Ở cuối câu trả lời, LUÔN đề xuất 2-3 câu hỏi chủ đề liên quan để người dùng có thể hỏi tiếp."""

                # === Gọi LLM: thử model chính → model dự phòng → smart fallback ===
                llm_messages = [{"role": "user", "content": llm_prompt}]
                llm_answer = None
                
                for model_name in ["qwen/qwen3-8b", "llama-3.1-8b-instant"]:
                    try:
                        completion = client.chat.completions.create(
                            messages=llm_messages,
                            model=model_name,
                            temperature=0.1,
                            max_tokens=3000,
                        )
                        llm_answer = completion.choices[0].message.content.strip()
                        print(f"DEBUG [Recommender]: LLM OK with {model_name}")
                        break
                    except Exception as e:
                        print(f"DEBUG [Recommender LLM {model_name}]: {e}")
                        continue
                
                data_year = int(data_sample['Năm'].mode().iloc[0]) if 'Năm' in data_sample.columns else ""
                
                if llm_answer:
                    return f"🤖 **[Recommender Agent]** — Trường: **{school_name}** · Năm: **{data_year}**\n\n{llm_answer}\n\n---\n*Dữ liệu chính thức năm {data_year}, đã kiểm chứng chính xác.*"
                
                # === SMART FALLBACK: Không dùng LLM, phân tích bằng Pandas ===
                print("DEBUG [Recommender]: All LLM models failed, using smart fallback")
                query_lower = user_query.lower()
                
                # Nếu người dùng hỏi "chỉ tiêu" nhưng dữ liệu chỉ có "điểm chuẩn"
                if 'chỉ tiêu' in query_lower and 'Chỉ tiêu' not in vf_match.columns:
                    return (
                        f"🤖 **[Recommender Agent]** — Trường: **{school_name}** · Năm: **{data_year}**\n\n"
                        f"Rất tiếc, dữ liệu hiện tại của trường này chỉ lưu trữ thông tin về **điểm chuẩn** và **phương thức xét tuyển**, chưa có thông tin về **chỉ tiêu**.\n\n"
                        f"👉 Bạn có thể hỏi tôi về điểm chuẩn của các ngành thay thế nhé!"
                    )
                
                # Phương thức tuyển sinh
                if any(kw in query_lower for kw in ['phương thức', 'xét tuyển', 'cách tuyển', 'hình thức']):
                    methods = vf_match.groupby('Phương thức xét tuyển').agg(
                        Số_ngành=('Tên ngành', 'nunique'),
                        Điểm_thấp=('Điểm chuẩn', 'min'),
                        Điểm_cao=('Điểm chuẩn', 'max')
                    ).reset_index()
                    table = "| Phương thức | Số ngành | Điểm thấp nhất | Điểm cao nhất |\n|---|---|---|---|\n"
                    for _, r in methods.iterrows():
                        table += f"| **{r['Phương thức xét tuyển']}** | {r['Số_ngành']} | {r['Điểm_thấp']} | {r['Điểm_cao']} |\n"
                    return f"🤖 **[Recommender Agent]** — Trường: **{school_name}** · Năm: **{data_year}**\n\n### Các phương thức xét tuyển\n\n{table}"
                
                # Ngành nào điểm cao/thấp nhất
                if any(kw in query_lower for kw in ['cao nhất', 'thấp nhất', 'top']):
                    sorted_df = vf_match.sort_values('Điểm chuẩn', ascending='thấp' in query_lower).head(10)
                    table = "| Tên ngành | Phương thức | Điểm chuẩn |\n|---|---|---|\n"
                    for _, r in sorted_df.iterrows():
                        table += f"| {r['Tên ngành']} | {r['Phương thức xét tuyển']} | **{r['Điểm chuẩn']}** |\n"
                    label = "thấp nhất" if 'thấp' in query_lower else "cao nhất"
                    return f"🤖 **[Recommender Agent]** — Trường: **{school_name}** · Năm: **{data_year}**\n\n### Top 10 ngành điểm {label}\n\n{table}"
                
                # Fallback cuối: tóm tắt thống kê
                total = vf_match['Tên ngành'].nunique()
                methods_list = ", ".join(vf_match['Phương thức xét tuyển'].unique().tolist())
                return (
                    f"🤖 **[Recommender Agent]** — Trường: **{school_name}** · Năm: **{data_year}**\n\n"
                    f"Trường có **{total} ngành** tuyển sinh theo phương thức: {methods_list}.\n\n"
                    f"👉 Hãy hỏi cụ thể hơn để tôi cung cấp thông tin chính xác!\n"
                    f"VD: *\"điểm chuẩn ngành CNTT {school_name}\"* hoặc *\"phương thức tuyển sinh {school_name}\"*"
                )

    # ======== BƯỚC 2: PANDAS DATA ENGINE TÌM KIẾM (LỚP 2 - FALLBACK OCR) ======== 
    filtered_df = df_tuyensinh.copy()
    
    # Lọc theo trường bằng Token Scoring
    if truong != "ALL":
        list_of_all_schools = filtered_df['Tên Trường'].dropna().unique().tolist()
        matched_ocr = find_matching_schools(truong, list_of_all_schools)
        
        if matched_ocr:
            filtered_df = filtered_df[filtered_df['Tên Trường'].isin(matched_ocr)]
            print(f"DEBUG: Matched OCR schools = {matched_ocr} ({len(filtered_df)} rows)")
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
1. Trả lời CHÍNH XÁC trọng tâm câu hỏi. TUYỆT ĐỐI không đưa thông tin thừa. Nếu người dùng hỏi một ngành cụ thể, CHỈ trả lời về ngành đó, không liệt kê tất cả các ngành. Nếu người dùng hỏi chung chung về điểm chuẩn, thì mới liệt kê dưới dạng BẢNG MARKDOWN.
2. KHÔNG viết bài luận, KHÔNG quảng cáo trường, KHÔNG bịa thông tin.
3. Cấu trúc bảng (nếu cần dùng bảng): | Mã ngành | Tên ngành | Phương thức | Điểm chuẩn | Chỉ tiêu |
4. Nếu dữ liệu có nhiều năm (2023, 2024), ghi rõ năm nào. {f'ĐẶC BIỆT LƯU Ý: Người dùng đang muốn tìm năm {nam}. Hãy ưu tiên báo cáo số liệu của năm {nam}. Nếu không có năm {nam}, hãy CẢNH BÁO rõ là không có và báo cáo năm gần nhất.' if nam > 0 else ''}
5. Nếu KHÔNG tìm thấy dữ liệu điểm: Trả lời "Không tìm thấy dữ liệu điểm trúng tuyển."
6. Câu hỏi về thông tin chung (vị trí, học phí): Được dùng kiến thức chung, trả lời ngắn gọn.
7. Ở cuối câu trả lời, LUÔN đề xuất 2-3 câu hỏi chủ đề liên quan để người dùng có thể hỏi tiếp.


DỮ LIỆU:
{context_data}"""
    
    try:
        answer_res = client.chat.completions.create(
            messages=[{"role": "user", "content": answer_prompt}],
            model="qwen/qwen3-8b",
            temperature=0.1,  # Giảm temperature để LLM bám sát dữ liệu
        ).choices[0].message.content
        return f"🤖 **[Recommender Agent]**\n\n{answer_res}"
    except Exception as e:
        return f"⚠️ Lỗi suy luận AI: {e}"
