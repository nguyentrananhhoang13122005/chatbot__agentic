import os
import re
import pandas as pd
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
from llm_client import OPENROUTER_FALLBACK_MODELS, call_llm, call_llm_stream

# --- KHỞI TẠO DATABASE ---
# Load Data một lần duy nhất vào RAM khi ứng dụng khởi chạy (tăng tốc độ phản hồi)
csv_path = "data/data_tuyensinh_clean.csv"
verified_path = "data/data_diem_chuan_verified.csv"
dats_2026_path = "data/data_tuyensinh_2026.csv"
dats_2025_path = "data/data_tuyensinh_2025_dats.csv"
dats_2024_path = "data/data_tuyensinh_2024.csv"

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

    # --- Load DATS Master ---
    master_path = "data/data_tuyensinh_master.csv"
    if os.path.exists(master_path):
        df_dats = pd.read_csv(master_path).fillna("")
        df_2026 = df_dats[df_dats['Năm'] == 2026]
        print(f"✅ [Recommender] DATS tổng hợp (Master) loaded: {len(df_dats)} bản ghi")
    else:
        df_dats = None
        df_2026 = None

except Exception as e:
    print("Lỗi load Database:", e)
    df_tuyensinh = None
    df_verified = None
    df_2026 = None
    df_dats = None

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
    # Map aliases & abbreviations
    name = re.sub(r'\bđh\b', 'đại học', name)
    name = re.sub(r'\bhv\b', 'học viện', name)
    name = re.sub(r'\bcđ\b', 'cao đẳng', name)
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

def find_matching_schools(truong_query: str, school_list: list, min_confidence: float = 0.5, strict: bool = False, location: str = "ALL") -> list:
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

    # Chuẩn hóa location để buff điểm
    loc_norm = ""
    if location != "ALL":
        loc_norm = _normalize_school_name(location)

    scored = []
    for i, school in enumerate(school_list):
        school_normalized = _normalize_school_name(school)
        doc_tokens = all_doc_tokens[i]

        s_bm25 = _bm25_score(query_tokens, doc_tokens, avg_dl)
        s_fuzzy = _fuzzy_score(query_normalized, school_normalized)
        s_token = _token_overlap_score(query_tokens, school_normalized)
        combined = (s_bm25 * 0.4) + (s_fuzzy * 0.3) + (s_token * 0.3)

        # Buff điểm nếu có location và location khớp một phần vào tên trường
        if loc_norm and loc_norm in school_normalized:
            combined += 1.0  # Buff cực mạnh để leo lên Top 1
            print(f"DEBUG [Matcher]: Buffed {school} by 1.0 due to location '{loc_norm}'")

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
def _stream_llm_response(prefix: str, messages: list, temperature: float = 0.1, max_tokens: int | None = None, suffix: str = ""):
    if prefix:
        yield prefix
    for chunk in call_llm_stream(
        messages=messages,
        model=OPENROUTER_FALLBACK_MODELS[0],
        temperature=temperature,
        max_tokens=max_tokens,
    ):
        yield chunk
    if suffix:
        yield suffix


def _build_structured_response(dataframe: pd.DataFrame, prefix: str, messages: list, temperature: float = 0.1, max_tokens: int | None = None, suffix: str = "") -> dict:
    return {
        "dataframe": dataframe.copy(),
        "prefix": prefix,
        "stream": call_llm_stream(
            messages=messages,
            model=OPENROUTER_FALLBACK_MODELS[0],
            temperature=temperature,
            max_tokens=max_tokens,
        ),
        "suffix": suffix,
    }


def query_diem_chuan(user_query: str, pre_extracted_school: str = "ALL", pre_extracted_location: str = "ALL", pre_extracted_keyword: str = "ALL", pre_extracted_year: int = 0, stream_output: bool = False):
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
        all_matches = find_matching_schools(truong, all_schools, location=pre_extracted_location)

        # Nếu nhiều trường khớp → HỎI LẠI, không đoán mò
        if len(all_matches) > 1:
            school_list_str = "\n".join([f"  {i+1}. **{s}**" for i, s in enumerate(all_matches)])
            return (
                f"**[Recommender Agent]**\n\n"
                f"Tôi tìm thấy **{len(all_matches)} trường** khớp với từ khóa **\"{truong}\"**:\n\n"
                f"{school_list_str}\n\n"
                f"👉 Bạn muốn xem thông tin trường nào? Hãy gõ tên cụ thể hơn nhé! "
                f"(VD: *\"{all_matches[0]}\"* hoặc *\"{all_matches[-1]}\"*)"
            )

    # ======== BƯỚC 1B: TRA CỨU CHÉO (CROSS-SCHOOL) — Khi truong=ALL + có keyword ========
    # Xử lý câu hỏi dạng "Top 5 trường CNTT", "ngành Y điểm cao nhất", "so sánh ngành kinh tế"
    has_specific_keyword = tu_khoa != "ALL" and not any(m in tu_khoa.lower() for m in ['điểm', 'chuẩn'])
    if truong == "ALL" and has_specific_keyword and df_verified is not None and not df_verified.empty:
        major_keywords = [kw.strip() for kw in tu_khoa.split('|') if kw.strip()]
        code_keywords = [kw for kw in major_keywords if kw.isdigit()]
        text_keywords = [kw for kw in major_keywords if not kw.isdigit()]

        vf_cross = pd.DataFrame()
        if code_keywords:
            pattern = '|'.join(code_keywords)
            vf_cross = df_verified[df_verified['Mã ngành'].astype(str).str.contains(pattern, case=False, na=False)]
        if vf_cross.empty and text_keywords:
            pattern = '|'.join(text_keywords)
            vf_cross = df_verified[df_verified['Tên ngành'].astype(str).str.contains(pattern, case=False, na=False)]

        if not vf_cross.empty:
            # Lọc theo năm: VÒNG LẶP 2026 → 2025 → 2024
            if 'Năm' in vf_cross.columns:
                vf_cross_nums = pd.to_numeric(vf_cross['Năm'], errors='coerce').fillna(0)
                if nam > 0:
                    cross_year_priority = [nam] + [y for y in [2026, 2025, 2024] if y != nam]
                else:
                    cross_year_priority = [2026, 2025, 2024]
                
                for try_year in cross_year_priority:
                    vf_cross_year = vf_cross[vf_cross_nums == try_year]
                    if not vf_cross_year.empty:
                        vf_cross = vf_cross_year
                        print(f"DEBUG [Recommender Cross]: Found data for year {try_year}")
                        break

            # Bỏ cột trống
            vf_cross = vf_cross.replace('', pd.NA).dropna(axis=1, how='all')

            # SẮP XẾP theo Điểm chuẩn GIẢM DẦN + ĐA DẠNG HOÁ trường
            if 'Điểm chuẩn' in vf_cross.columns:
                vf_cross['_score'] = pd.to_numeric(vf_cross['Điểm chuẩn'], errors='coerce').fillna(0)
                vf_cross = vf_cross.sort_values('_score', ascending=False)

                # Lấy dòng điểm cao nhất của MỖI trường (đa dạng kết quả)
                vf_cross_top = vf_cross.drop_duplicates(subset=['Trường'], keep='first')
                # Lấy thêm dòng phụ (nhiều ngành) cho top trường
                top_schools = vf_cross_top.head(30)['Trường'].tolist()
                vf_cross_detail = vf_cross[vf_cross['Trường'].isin(top_schools)]
                vf_cross = vf_cross_detail
                vf_cross = vf_cross.drop(columns=['_score'], errors='ignore')

            # Giới hạn 150 dòng cho LLM
            data_sample = vf_cross.head(150)
            export_cols = [c for c in ['Trường','Mã ngành','Tên ngành','Năm','Phương thức xét tuyển','Điểm chuẩn','Chỉ tiêu','Tổ hợp môn'] if c in data_sample.columns]
            data_context = data_sample[export_cols].to_csv(index=False, encoding='utf-8')

            data_year_val = ""
            if 'Năm' in data_sample.columns:
                year_mode = data_sample['Năm'].mode()
                data_year_val = int(year_mode.iloc[0]) if not year_mode.empty else ""

            table_rule_cross = (
                "4. KHÔNG tạo bảng Markdown. Bảng dữ liệu đã được hiển thị phía trên bằng giao diện bảng. Chỉ nhận xét và phân tích ngắn gọn."
                if stream_output
                else "4. Tạo BẢNG MARKDOWN rõ ràng."
            )

            llm_prompt_cross = f"""Bạn là trợ lý tuyển sinh AI chuyên nghiệp cho Việt Nam.

CÂU HỎI CỦA NGƯỜI DÙNG: "{user_query}"

DỮ LIỆU CHÍNH THỨC — TẤT CẢ TRƯỜNG CÓ NGÀNH LIÊN QUAN (dạng CSV):
{data_context}

TỔNG SỐ DÒNG DỮ LIỆU: {len(vf_cross)} ({vf_cross['Trường'].nunique()} trường)

QUY TẮC TRẢ LỜI (TUÂN THỦ TUYỆT ĐỐI):
1. Trả lời ĐÚNG TRỌNG TÂM câu hỏi. TUYỆT ĐỐI KHÔNG lan man, KHÔNG đưa thông tin thừa.
2. Dựa HOÀN TOÀN trên dữ liệu trên. TUYỆT ĐỐI KHÔNG bịa thông tin.
3. Nếu hỏi "top" hoặc "xếp hạng" → SẮP XẾP theo điểm chuẩn GIẢM DẦN.
{table_rule_cross}
5. BẮT BUỘC ghi rõ NĂM dữ liệu.
6. Sử dụng Markdown cho phần nhận xét, trả lời tiếng Việt chuyên nghiệp.
7. Ở cuối, đề xuất 2-3 câu hỏi liên quan MÀ HỆ THỐNG CÓ DỮ LIỆU để trả lời."""

            llm_messages_cross = [{"role": "user", "content": llm_prompt_cross}]
            prefix_cross = f"**[Recommender Agent]** — Tìm kiếm chéo: **{tu_khoa}** · {vf_cross['Trường'].nunique()} trường\n\n"
            suffix_cross = f"\n\n---\n*Dữ liệu chính thức{f' năm {data_year_val}' if data_year_val else ''}, đã kiểm chứng chính xác.*"

            print(f"DEBUG [Recommender]: Cross-school search for '{tu_khoa}' → {len(vf_cross)} rows, {vf_cross['Trường'].nunique()} schools")

            if stream_output:
                return _build_structured_response(
                    dataframe=data_sample[export_cols],
                    prefix=prefix_cross,
                    messages=llm_messages_cross,
                    temperature=0.1,
                    max_tokens=3000,
                    suffix=suffix_cross,
                )

            llm_answer, llm_error_info = call_llm(
                messages=llm_messages_cross,
                model_list=OPENROUTER_FALLBACK_MODELS,
                temperature=0.1,
                max_tokens=3000,
            )
            if llm_answer:
                return f"{prefix_cross}{llm_answer}{suffix_cross}"
            if llm_error_info:
                return f"{prefix_cross}{llm_error_info['message']}"

    # ======== QUYẾT ĐỊNH DỮ LIỆU: TÌM KIẾM TOÀN BỘ 3 NĂM ========
    # Luồng: DATS (2026→2025→2024) → Verified DB → OCR
    # CHỈ trả lời "không có dữ liệu" khi ĐÃ TÌM HẾT TẤT CẢ data sources
    query_lower = user_query.lower()
    is_score_query = any(kw in query_lower for kw in ['điểm chuẩn', 'điểm', 'bao nhiêu điểm', 'điểm trúng tuyển'])
    is_admission_query = any(kw in query_lower for kw in ['tuyển sinh', 'phương thức', 'chỉ tiêu', 'xét tuyển', 'điều kiện', 'hồ sơ', 'đăng ký', 'học phí', 'ngành', 'học bổng', 'ký túc'])

    # Flag theo dõi: đã tìm thấy và trả lời từ nguồn nào chưa?
    dats_answered = False

    # ======== BƯỚC 1: TRA CỨU DATS — TỰ ĐỘNG TÌM NĂM CÓ DỮ LIỆU PHÙ HỢP ========
    # Luôn thử DATS trước cho MỌI loại câu hỏi (admission + score)
    if df_dats is not None and not df_dats.empty and truong != "ALL":

        # Xác định năm tìm kiếm
        if nam > 0:
            target_year = nam
        else:
            target_year = 2026

        # Tìm trường trong DATS Master
        list_check = df_dats['Trường'].dropna().unique().tolist()
        exact_dats = [s for s in list_check if s == truong]
        if exact_dats:
            matched_check = exact_dats
        else:
            matched_check = find_matching_schools(truong, list_check, strict=True, location=pre_extracted_location)
            
        available_years = []
        best_match = None
        if len(matched_check) == 1:
            s = matched_check[0]
            school_rows = df_dats[df_dats['Trường'] == s]
            
            for _, r in school_rows.iterrows():
                available_years.append((r['Năm'], s))
            
            # === VÒNG LẶP TÌM NĂM: target → 2026 → 2025 → 2024 ===
            # Xây dựng danh sách năm ưu tiên: bắt đầu từ năm user yêu cầu (hoặc 2026), giảm dần
            if nam > 0:
                year_priority = [nam] + [y for y in [2026, 2025, 2024] if y != nam]
            else:
                year_priority = [2026, 2025, 2024]
            
            for try_year in year_priority:
                target_row = school_rows[school_rows['Năm'] == try_year]
                if not target_row.empty and len(str(target_row.iloc[0].get('Nội dung', ''))) >= 50:
                    best_match = (try_year, s, target_row.iloc[0].get('Nội dung', ''))
                    print(f"DEBUG [Recommender]: Found '{s}' in DATS Master (year {try_year})")
                    break
            
            if not best_match:
                print(f"DEBUG [Recommender]: No valid DATS content for '{s}' in years {year_priority}")

        # --- Helper: Smart content extraction ---
        def _extract_content_for_llm(content: str, query_lc: str) -> str:
            """Trích xuất phần nội dung liên quan từ DATS content dài."""
            if len(content) <= 8000:
                return content
            search_keywords = []
            kw_extract_map = {
                'vị trí': ['địa chỉ', 'cơ sở', 'khu', 'trụ sở', 'vị trí', 'phân hiệu'],
                'học phí': ['học phí', 'mức phí', 'chi phí đào tạo', 'tín chỉ'],
                'chỉ tiêu': ['chỉ tiêu', 'tổng chỉ tiêu'],
                'phương thức': ['phương thức', 'xét tuyển'],
                'ngành': ['danh sách ngành', 'ngành đào tạo', 'chương trình đào tạo'],
                'điều kiện': ['điều kiện', 'yêu cầu'],
                'học bổng': ['học bổng', 'miễn giảm'],
                'tổ hợp': ['tổ hợp', 'tổ hợp môn'],
            }
            for kw, patterns in kw_extract_map.items():
                if kw in query_lc:
                    search_keywords.extend(patterns)
            if search_keywords:
                content_lower = content.lower()
                best_pos = -1
                for sk in search_keywords:
                    pos = content_lower.find(sk)
                    if pos >= 0 and (best_pos < 0 or pos < best_pos):
                        best_pos = pos
                if best_pos >= 0:
                    intro = content[:1500]
                    # Bỏ qua các match ở phần Mục lục (thường nằm ở < 5000 ký tự đầu)
                    # Nếu best_pos ở quá sớm, mở rộng window
                    start = max(0, best_pos - 500)
                    end = min(len(content), best_pos + 15000)
                    relevant_section = content[start:end]
                    print(f"DEBUG [Recommender]: Extracted relevant section around '{search_keywords[0]}' (pos={best_pos})")
                    return intro + "\n\n[...]\n\n" + relevant_section
            return content[:8000]

        if best_match:
            search_year, school_found, content_found = best_match
            fell_back = (search_year != target_year)

            # === SMART SOURCE ROUTING: Ưu tiên Verified DB cho câu hỏi cần dữ liệu có cấu trúc ===
            # DATS = PDF đề án tuyển sinh (free-text) → tốt cho: phương thức, học phí, chỉ tiêu, điều kiện
            # Verified DB = bảng CSV có cấu trúc → tốt cho: danh sách ngành, điểm chuẩn, mã ngành, tổ hợp
            structured_query_keywords = [
                'ngành nào', 'những ngành', 'danh sách ngành', 'các ngành', 'có ngành',
                'điểm chuẩn', 'bao nhiêu điểm', 'điểm trúng tuyển',
                'mã ngành', 'tổ hợp', 'khối thi', 'xét tuyển ngành',
            ]
            is_structured_query = any(kw in query_lower for kw in structured_query_keywords)
            
            prefer_verified = False
            if is_structured_query and df_verified is not None and not df_verified.empty:
                verified_schools_list = df_verified['Trường'].dropna().unique().tolist()
                exact_vf = [s for s in verified_schools_list if s == school_found]
                if not exact_vf:
                    exact_vf = find_matching_schools(school_found, verified_schools_list, strict=True, location=pre_extracted_location)
                if exact_vf:
                    prefer_verified = True
                    print(f"DEBUG [Recommender]: Structured query detected → skipping DATS, preferring Verified DB for '{school_found}'")
            
            if prefer_verified:
                # Không return ở đây → để code chạy xuống Bước 2 (Verified DB) bên dưới
                pass
            else:
                print(f"DEBUG [Recommender]: Using DATS {search_year} for '{school_found}' ({len(content_found)} chars), fallback={fell_back}")

                content_for_llm = _extract_content_for_llm(content_found, query_lower)

                # Thông báo các năm khác có dữ liệu
                other_years_note = ""
                if fell_back:
                    other_years_note = f"\n💡 *Trường này hiện không có dữ liệu cho năm {target_year}, hệ thống đang dùng dữ liệu mới nhất (năm {search_year}).*"

                # Ghi chú fallback nếu đã chuyển năm
                fallback_note = ""
                if fell_back:
                    fallback_note = f"\n⚠️ Dữ liệu năm {target_year} không có thông tin về chủ đề này. Hệ thống đã tự động tìm và sử dụng dữ liệu **năm {search_year}**."

                llm_prompt_dats = f"""Bạn là trợ lý tuyển sinh AI chuyên nghiệp cho Việt Nam.

CÂU HỎI CỦA NGƯỜI DÙNG: "{user_query}"

THÔNG TIN TUYỂN SINH NĂM {search_year} CỦA TRƯỜNG {school_found}:
{content_for_llm}

QUY TẮC TRẢ LỜI (TUÂN THỦ TUYỆT ĐỐI):
1. CHỈ trả lời DỰA TRÊN DỮ LIỆU ở trên. TUYỆT ĐỐI KHÔNG dùng kiến thức riêng, KHÔNG suy luận, KHÔNG bịa số liệu.
2. Trả lời ĐÚNG TRỌNG TÂM câu hỏi. KHÔNG lan man, KHÔNG liệt kê thông tin thừa.
3. Khi trích dẫn SỐ LIỆU (học phí, chỉ tiêu, mã ngành, điểm), phải GHI ĐÚNG CON SỐ từ dữ liệu gốc. Nếu dữ liệu ghi "28,700,000 VNĐ" thì phải ghi đúng "28,700,000 VNĐ".
4. BẮT BUỘC ghi rõ năm **{search_year}** trong tiêu đề.
5. Nếu dữ liệu KHÔNG CHỨA thông tin user hỏi → nói rõ: "Dữ liệu năm {search_year} của trường này không có thông tin về [chủ đề]."
6. Nếu hỏi về học phí → tạo BẢNG MARKDOWN ĐẦY ĐỦ, GHI RÕ mức phí đúng nguyên văn từ dữ liệu.
7. Nếu hỏi về phương thức → liệt kê chi tiết. Nếu hỏi về ngành → liệt kê đầy đủ ngành, mã ngành.
8. Sử dụng Markdown (bảng, in đậm). Trả lời tiếng Việt, chuyên nghiệp.
9. KHÔNG hiển thị cột trống.
10. Ở cuối, đề xuất 2-3 câu hỏi gợi ý CỤ THỂ liên quan đến trường {school_found} mà hệ thống có dữ liệu. Gợi ý phải PHÙ HỢP với nhu cầu ban đầu của người dùng."""
                dats_prefix = f"**[Recommender Agent]** — Trường: **{school_found}** · Năm: **{search_year}**\n\n"
                if fell_back:
                    dats_prefix += f"{fallback_note}\n\n"
                dats_messages = [{"role": "user", "content": llm_prompt_dats}]
                dats_suffix = f"{other_years_note}\n\n---\n*Nguồn: Đề án tuyển sinh chính thức năm {search_year}.*"

                if stream_output:
                    return _stream_llm_response(
                        prefix=dats_prefix,
                        messages=dats_messages,
                        temperature=0.0,
                        max_tokens=4096,
                        suffix=dats_suffix,
                    )

                llm_answer, llm_error_info = call_llm(
                    messages=dats_messages,
                    model_list=OPENROUTER_FALLBACK_MODELS,
                    temperature=0.0,
                    max_tokens=4096,
                )
                if llm_answer:
                    dats_answered = True
                    return f"{dats_prefix}{llm_answer}{dats_suffix}"
                if llm_error_info:
                    dats_answered = True
                    return (
                        f"{dats_prefix}"
                        f"{llm_error_info['message']}\n\n"
                        f"Tôi đã tìm thấy dữ liệu tuyển sinh năm {search_year} của trường này, nhưng hiện chưa thể tổng hợp bằng AI. "
                        f"Vui lòng thử lại sau vài phút."
                    )

        elif available_years:
            # Không có dữ liệu nào đủ dài → NÓI RÕ + gợi ý năm khác
            other_info = "\n".join([f"  - **Năm {y}**: {s}" for y, s in available_years])
            first_year, first_school = available_years[0]
            return (
                f"**[Recommender Agent]**\n\n"
                f"⚠️ **Trường \"{truong}\" chưa có dữ liệu tuyển sinh năm {target_year}** trong hệ thống.\n\n"
                f"Tuy nhiên, tôi tìm thấy dữ liệu của trường này ở các năm khác:\n\n"
                f"{other_info}\n\n"
                f"👉 Hãy hỏi lại kèm năm cụ thể, VD: *\"{user_query} năm {first_year}\"*"
            )

    # ======== BƯỚC 2: TRA CỨU DỮ LIỆU ĐIỂM CHUẨN 2025 (VERIFIED DATABASE) ========
    if df_verified is not None and not df_verified.empty and truong != "ALL":
        list_of_verified_schools = df_verified['Trường'].dropna().unique().tolist()
        # Exact match priority: nếu truong đã được resolve bởi Guard 0 → match chính xác
        exact_verified = [s for s in list_of_verified_schools if s == truong]
        if exact_verified:
            matched_schools = exact_verified
        else:
            matched_schools = find_matching_schools(truong, list_of_verified_schools, location=pre_extracted_location)

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

            # --- Lọc theo năm: VÒNG LẶP 2026 → 2025 → 2024 ---
            year_fallback_note = ""
            if 'Năm' in vf_match.columns:
                vf_match.loc[:, 'Năm_Num'] = pd.to_numeric(vf_match['Năm'], errors='coerce').fillna(0)
                
                # Xây dựng danh sách năm ưu tiên (giống logic DATS)
                if nam > 0:
                    vf_year_priority = [nam] + [y for y in [2026, 2025, 2024] if y != nam]
                else:
                    vf_year_priority = [2026, 2025, 2024]
                
                found_year = None
                for try_year in vf_year_priority:
                    vf_match_year = vf_match[vf_match['Năm_Num'] == try_year]
                    if not vf_match_year.empty:
                        found_year = try_year
                        vf_match = vf_match_year
                        print(f"DEBUG [Recommender Verified]: Found data for year {try_year}")
                        break
                
                if found_year is None:
                    # Không có năm nào trong [2026,2025,2024] → lấy max
                    latest_year = vf_match['Năm_Num'].max()
                    if latest_year > 0:
                        found_year = int(latest_year)
                        vf_match = vf_match[vf_match['Năm_Num'] == latest_year]
                
                # Ghi chú fallback nếu năm tìm được khác năm user yêu cầu
                requested = nam if nam > 0 else 2026
                if found_year and found_year != requested:
                    year_fallback_note = f"\n\n⚠️ *Dữ liệu năm {requested} chưa có. Hệ thống tự động sử dụng dữ liệu năm {int(found_year)} (năm gần nhất có sẵn).*"
                
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

                table_rule = (
                    "7. KHÔNG tạo bảng Markdown. Bảng dữ liệu đã được hiển thị phía trên bằng giao diện bảng. Chỉ dùng Markdown cho phần nhận xét, bullet và nhấn mạnh."
                    if stream_output
                    else "7. Sử dụng Markdown (bảng, in đậm). Trả lời tiếng Việt, chuyên nghiệp."
                )

                llm_prompt = f"""Bạn là trợ lý tuyển sinh AI chuyên nghiệp cho Việt Nam.

CÂU HỎI CỦA NGƯỜI DÙNG: "{user_query}"

DỮ LIỆU CHÍNH THỨC CỦA TRƯỜNG {school_name} (dạng CSV):
{data_context}

THỐNG KÊ: {stats}

QUY TẮC TRẢ LỜI (TUÂN THỦ TUYỆT ĐỐI):
1. CHỈ trả lời DỰA TRÊN DỮ LIỆU CSV ở trên. TUYỆT ĐỐI KHÔNG dùng kiến thức riêng, KHÔNG suy luận thêm, KHÔNG bịa thông tin.
2. Trả lời ĐÚNG TRỌNG TÂM câu hỏi. KHÔNG lan man, KHÔNG đưa thông tin thừa không liên quan đến câu hỏi.
3. Khi trích dẫn ĐIỂM CHUẨN, phải GHI ĐÚNG CON SỐ từ cột "Điểm chuẩn" trong CSV. VD: nếu CSV ghi 25.5 thì trả lời 25.5, KHÔNG làm tròn. Dữ liệu trên là DỮ LIỆU CHÍNH THỨC từ trường.
4. Nếu hỏi về điểm chuẩn ngành cụ thể → cho điểm CHÍNH XÁC theo từng phương thức. KHÔNG liệt kê tất cả ngành khác.
5. Nếu hỏi về phương thức → liệt kê CÁC PHƯƠNG THỨC và số ngành áp dụng.
6. Nếu hỏi chung chung → tóm tắt ngắn gọn dựa trên thống kê.
{table_rule}
8. BẮT BUỘC ghi rõ NĂM CỤ THỂ của dữ liệu (VD: "Điểm chuẩn **năm 2025**").
9. Nếu dữ liệu CSV KHÔNG CÓ thông tin user hỏi → nói rõ "Dữ liệu hiện tại chưa có thông tin về [chủ đề]." TUYỆT ĐỐI KHÔNG tự ý liệt kê thông tin thay thế khi người dùng không hỏi.
10. Ở cuối, đề xuất 2-3 câu hỏi gợi ý CỤ THỂ cho trường {school_name} mà hệ thống có dữ liệu. Gợi ý phải PHÙ HỢP với nhu cầu ban đầu của người dùng."""

                # === Gọi LLM: thử model chính → model dự phòng → smart fallback ===
                llm_messages = [{"role": "user", "content": llm_prompt}]
                data_year = int(data_sample['Năm'].mode().iloc[0]) if 'Năm' in data_sample.columns else ""

                if stream_output:
                    return _build_structured_response(
                        dataframe=data_sample[export_cols],
                        prefix=f"**[Recommender Agent]** — Trường: **{school_name}** · Năm: **{data_year}**\n\n",
                        messages=llm_messages,
                        temperature=0.1,
                        max_tokens=3000,
                        suffix=f"\n\n---\n*Dữ liệu chính thức năm {data_year}, đã kiểm chứng chính xác.*",
                    )

                llm_answer, llm_error_info = call_llm(
                    messages=llm_messages,
                    model_list=OPENROUTER_FALLBACK_MODELS,
                    temperature=0.1,
                    max_tokens=3000,
                )
                if llm_answer:
                    print("DEBUG [Recommender]: LLM OK")

                if llm_answer:
                    return f"**[Recommender Agent]** — Trường: **{school_name}** · Năm: **{data_year}**\n\n{year_fallback_note}{llm_answer}\n\n---\n*Dữ liệu chính thức năm {data_year}, đã kiểm chứng chính xác.*"

                # === SMART FALLBACK: Không dùng LLM, phân tích bằng Pandas ===
                print("DEBUG [Recommender]: All LLM models failed, using smart fallback")
                ai_warning = f"{llm_error_info['message']}\n\nTôi sẽ trả lời bằng dữ liệu có sẵn.\n\n" if llm_error_info else ""
                query_lower = user_query.lower()

                # Nếu người dùng hỏi "chỉ tiêu" nhưng dữ liệu chỉ có "điểm chuẩn"
                if 'chỉ tiêu' in query_lower and 'Chỉ tiêu' not in vf_match.columns:
                    return (
                        f"**[Recommender Agent]** — Trường: **{school_name}** · Năm: **{data_year}**\n\n"
                        f"{ai_warning}"
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
                    return f"**[Recommender Agent]** — Trường: **{school_name}** · Năm: **{data_year}**\n\n{ai_warning}### Các phương thức xét tuyển\n\n{table}"

                # Ngành nào điểm cao/thấp nhất
                if any(kw in query_lower for kw in ['cao nhất', 'thấp nhất', 'top']):
                    sorted_df = vf_match.sort_values('Điểm chuẩn', ascending='thấp' in query_lower).head(10)
                    table = "| Tên ngành | Phương thức | Điểm chuẩn |\n|---|---|---|\n"
                    for _, r in sorted_df.iterrows():
                        table += f"| {r['Tên ngành']} | {r['Phương thức xét tuyển']} | **{r['Điểm chuẩn']}** |\n"
                    label = "thấp nhất" if 'thấp' in query_lower else "cao nhất"
                    return f"**[Recommender Agent]** — Trường: **{school_name}** · Năm: **{data_year}**\n\n{ai_warning}### Top 10 ngành điểm {label}\n\n{table}"

                # Fallback cuối: tóm tắt thống kê
                total = vf_match['Tên ngành'].nunique()
                methods_list = ", ".join(vf_match['Phương thức xét tuyển'].unique().tolist())
                return (
                    f"**[Recommender Agent]** — Trường: **{school_name}** · Năm: **{data_year}**\n\n"
                    f"{ai_warning}"
                    f"Trường có **{total} ngành** tuyển sinh theo phương thức: {methods_list}.\n\n"
                    f"👉 Hãy hỏi cụ thể hơn để tôi cung cấp thông tin chính xác!\n"
                    f"VD: *\"điểm chuẩn ngành CNTT {school_name}\"* hoặc *\"phương thức tuyển sinh {school_name}\"*"
                )

    # ======== GENERAL INFO FALLBACK — Vị trí, địa chỉ, thông tin chung ========
    # Khi trường đã được xác định nhưng KHÔNG CÓ trong DATS/Verified → dùng LLM kiến thức chung
    # CHỈ áp dụng cho câu hỏi KHÔNG cần dữ liệu chính xác (vị trí, lịch sử, cơ sở vật chất...)
    general_info_keywords = ['vị trí', 'ở đâu', 'địa chỉ', 'cơ sở', 'campus', 'trụ sở',
                             'thành lập', 'lịch sử', 'giới thiệu', 'tổng quan']
    is_general_info_query = truong != "ALL" and any(kw in query_lower for kw in general_info_keywords)

    if is_general_info_query:
        general_prompt = f"""Bạn là trợ lý tuyển sinh AI chuyên nghiệp cho Việt Nam.

CÂU HỎI CỦA NGƯỜI DÙNG: "{user_query}"
TRƯỜNG ĐƯỢC HỎI: "{truong}"

QUY TẮC TRẢ LỜI:
1. Trả lời NGẮN GỌN, ĐÚNG TRỌNG TÂM câu hỏi dựa trên kiến thức chung.
2. Nếu hỏi về vị trí/địa chỉ → cung cấp địa chỉ chính xác nhất có thể.
3. Nếu hỏi về giới thiệu → tóm tắt ngắn gọn (3-5 câu).
4. Sử dụng Markdown, tiếng Việt chuyên nghiệp.
5. Ở cuối, đề xuất 2-3 câu hỏi về điểm chuẩn, ngành học MÀ HỆ THỐNG CÓ DỮ LIỆU."""

        general_prefix = (
            f"**[Recommender Agent]** — Trường: **{truong}**\n\n"
        )
        general_suffix = (
            f"\n\n---\n"
            f"*⚠️ Thông tin trên được lấy từ kiến thức chung của AI, không phải từ database chính thức. "
            f"Vui lòng xác minh tại website chính thức của trường.*"
        )

        print(f"DEBUG [Recommender]: General info fallback for '{truong}' — query about general info")

        if stream_output:
            return _stream_llm_response(
                prefix=general_prefix,
                messages=[{"role": "user", "content": general_prompt}],
                temperature=0.3,
                max_tokens=1500,
                suffix=general_suffix,
            )

        general_answer, general_error = call_llm(
            messages=[{"role": "user", "content": general_prompt}],
            model_list=OPENROUTER_FALLBACK_MODELS,
            temperature=0.3,
            max_tokens=1500,
        )
        if general_answer:
            return f"{general_prefix}{general_answer}{general_suffix}"

    # ======== BƯỚC 2: PANDAS DATA ENGINE TÌM KIẾM (LỚP 2 - FALLBACK OCR) ========
    filtered_df = df_tuyensinh.copy()

    # Lọc theo trường bằng Token Scoring
    if truong != "ALL":
        list_of_all_schools = filtered_df['Tên Trường'].dropna().unique().tolist()
        matched_ocr = find_matching_schools(truong, list_of_all_schools, location=pre_extracted_location)

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
    if filtered_df.empty:
        print(f"DEBUG [Recommender]: filtered_df is empty, returning early to prevent LLM hallucination.")
        if truong != "ALL":
            msg = f"Xin lỗi, hiện tại hệ thống chưa có dữ liệu của trường **{truong}**."
        else:
            msg = f"Xin lỗi, không tìm thấy dữ liệu nào phù hợp với yêu cầu của bạn."
        return f"**[Recommender Agent]**\n\n{msg}\n\n👉 Vui lòng kiểm tra lại từ khóa hoặc thử một câu hỏi khác nhé!"

    context_data = clean_ocr_for_llm(filtered_df)

    # Giới hạn token
    if len(context_data) > 10000:
        context_data = context_data[:5000] + "\n...[Dữ liệu bị lược bỏ do giới hạn Token]...\n" + context_data[-5000:]

    # ======== BƯỚC 3: LLM SYNTHESIS (PROMPT CỨNG - ĐA DẠNG FORMAT) ========
    answer_prompt = f"""Bạn là CHUYÊN GIA TƯ VẤN TUYỂN SINH. CHỈ trả lời câu hỏi dựa HOÀN TOÀN trên DỮ LIỆU bên dưới. TUYỆT ĐỐI KHÔNG dùng kiến thức riêng.

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
1. CHỈ trả lời DỰA TRÊN DỮ LIỆU bên dưới. TUYỆT ĐỐI KHÔNG suy luận, KHÔNG dùng kiến thức riêng, KHÔNG bịa số liệu.
2. Trả lời CHÍNH XÁC trọng tâm câu hỏi. Nếu hỏi một ngành → CHỈ trả lời về ngành đó. Nếu hỏi chung → BẢNG MARKDOWN.
3. Khi trích dẫn số liệu (điểm, chỉ tiêu), GHI ĐÚNG con số từ dữ liệu gốc.
4. KHÔNG viết bài luận, KHÔNG quảng cáo trường.
5. Nếu dữ liệu có nhiều năm (2023, 2024), ghi rõ năm nào. {f'ĐẶC BIỆT LƯU Ý: Người dùng đang muốn tìm năm {nam}. Ưu tiên số liệu năm {nam}. Nếu không có năm {nam}, CẢNH BÁO rõ và báo cáo năm gần nhất.' if nam > 0 else ''}
6. Nếu dữ liệu KHÔNG CHỨA thông tin user hỏi → nói rõ: "Dữ liệu hiện tại không có thông tin về [chủ đề]."
7. Ở cuối, đề xuất 2-3 câu hỏi gợi ý CỤ THỂ mà hệ thống có dữ liệu, PHÙ HỢP với nhu cầu ban đầu.

DỮ LIỆU:
{context_data}"""

    if stream_output:
        return _stream_llm_response(
            prefix="**[Recommender Agent]**\n\n",
            messages=[{"role": "user", "content": answer_prompt}],
            temperature=0.1,
        )

    answer_res, error_info = call_llm(
        messages=[{"role": "user", "content": answer_prompt}],
        model_list=OPENROUTER_FALLBACK_MODELS,
        temperature=0.1,
    )
    if answer_res:
        return f"**[Recommender Agent]**\n\n{answer_res}"
    return f"**[Recommender Agent]**\n\n{error_info['message'] if error_info else '⚠️ Hệ thống AI tạm thời không khả dụng. Vui lòng thử lại sau.'}"


def query_diem_chuan_stream(user_query: str, pre_extracted_school: str = "ALL", pre_extracted_location: str = "ALL", pre_extracted_keyword: str = "ALL", pre_extracted_year: int = 0):
    return query_diem_chuan(
        user_query=user_query,
        pre_extracted_school=pre_extracted_school,
        pre_extracted_location=pre_extracted_location,
        pre_extracted_keyword=pre_extracted_keyword,
        pre_extracted_year=pre_extracted_year,
        stream_output=True,
    )
