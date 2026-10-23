import PyPDF2
import os
import sys
import numpy as np
import pandas as pd
import cv2
from PIL import Image, ImageEnhance
from llm_client import OPENROUTER_FALLBACK_MODELS, call_llm, call_llm_stream

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# === LAZY OCR READER (chỉ khởi tạo khi cần, model đã tải sẵn ở ~/.EasyOCR/model/) ===
_ocr_reader = None

def _get_ocr_reader():
    """Lazy init: tạo EasyOCR reader khi cần (models đã pre-download)."""
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        print("⏳ [Counselor] Đang khởi tạo EasyOCR reader (vi+en)...")
        _ocr_reader = easyocr.Reader(['vi', 'en'], gpu=False, verbose=False)
        print("✅ [Counselor] EasyOCR reader sẵn sàng.")
    return _ocr_reader


# ======== TIỀN XỬ LÝ ẢNH CHO OCR (OpenCV) ========
def _preprocess_image_for_ocr(img_array: np.ndarray) -> np.ndarray:
    """
    Tiền xử lý ảnh học bạ để OCR chính xác hơn:
    1. Upscale 2x nếu ảnh nhỏ
    2. Chuyển grayscale
    3. CLAHE (tăng contrast cục bộ)
    4. Denoise
    5. Sharpen
    """
    h, w = img_array.shape[:2]

    # Bước 1: Upscale nếu ảnh nhỏ (< 1500px cạnh dài)
    if max(h, w) < 1500:
        scale = 2
        img_array = cv2.resize(img_array, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
        print(f"DEBUG [Preprocess]: Upscale {w}x{h} -> {w*scale}x{h*scale}")

    # Bước 2: Chuyển grayscale
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    # Bước 3: CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Bước 4: Denoise nhẹ
    denoised = cv2.fastNlMeansDenoising(enhanced, h=10, templateWindowSize=7, searchWindowSize=21)

    # Bước 5: Sharpen
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]])
    sharpened = cv2.filter2D(denoised, -1, kernel)

    # Chuyển lại RGB cho EasyOCR
    result = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB)
    print(f"DEBUG [Preprocess]: Anh xu ly xong, {result.shape[1]}x{result.shape[0]}")
    return result


# ======== CLUSTER TEXT BLOCKS THÀNH HÀNG BẢNG ========
def _cluster_into_rows(results: list, y_tolerance: int = 15) -> list:
    """
    Nhóm các text blocks theo toạ độ Y (cùng hàng trong bảng).
    Returns: list of rows, mỗi row là list of block dicts đã sort theo X.
    """
    if not results:
        return []

    blocks = []
    for item in results:
        bbox = item[0]
        text = item[1]
        confidence = item[2]

        y_center = (bbox[0][1] + bbox[2][1]) / 2
        x_center = (bbox[0][0] + bbox[2][0]) / 2

        if text.strip() and confidence > 0.15:
            blocks.append({
                'y': y_center,
                'x': x_center,
                'text': text.strip(),
                'conf': confidence
            })

    if not blocks:
        return []

    blocks.sort(key=lambda b: b['y'])

    rows = []
    current_row = [blocks[0]]

    for block in blocks[1:]:
        if abs(block['y'] - current_row[0]['y']) <= y_tolerance:
            current_row.append(block)
        else:
            current_row.sort(key=lambda b: b['x'])
            rows.append(current_row)
            current_row = [block]

    current_row.sort(key=lambda b: b['x'])
    rows.append(current_row)

    return rows


def _format_rows_as_table(rows: list) -> str:
    """Chuyển rows thành text có cấu trúc bảng."""
    output_lines = []
    for row in rows:
        cells = [b['text'] for b in row]
        line = " | ".join(cells)
        output_lines.append(line)
    return "\n".join(output_lines)


# ======== TOOL 1: ĐỌC FILE ========
def doc_pdf(file_obj) -> str:
    """Tool 1a: Đọc văn bản từ file PDF (CV/Hồ sơ)"""
    try:
        reader = PyPDF2.PdfReader(file_obj)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    except Exception as e:
        return f"[LOI XU LY PDF]: {str(e)}"


def doc_image(file_obj) -> str:
    """Tool 1b: Doc van ban tu anh hoc ba — OCR 2 pass (preprocessed + raw), chon ket qua tot nhat."""
    try:
        ocr = _get_ocr_reader()
    except Exception as e:
        print(f"ERROR [Counselor OCR init]: {e}")
        return "[LOI OCR]: Khong the khoi tao EasyOCR."

    try:
        # Doc anh
        image = Image.open(file_obj)
        if image.mode in ('RGBA', 'P', 'LA'):
            image = image.convert('RGB')

        # Tang sac net bang Pillow truoc
        image = ImageEnhance.Contrast(image).enhance(1.3)
        image = ImageEnhance.Sharpness(image).enhance(1.5)

        img_array = np.array(image)
        print(f"DEBUG [OCR]: Anh goc {image.size}, mode={image.mode}")

        # === PASS 1: OCR tren anh preprocessed (OpenCV) ===
        processed = _preprocess_image_for_ocr(img_array)
        
        # Luu anh debug de kiem tra
        try:
            debug_img = Image.fromarray(processed)
            debug_img.save("debug_ocr_processed.jpg", quality=95)
            print("DEBUG [OCR]: Saved debug_ocr_processed.jpg")
        except:
            pass

        results_processed = ocr.readtext(
            processed, detail=1, paragraph=False,
            text_threshold=0.5, low_text=0.3,
            width_ths=0.7, height_ths=0.5,
        )

        # === PASS 2: OCR tren anh goc (khong preprocess) ===
        results_raw = ocr.readtext(
            img_array, detail=1, paragraph=False,
            text_threshold=0.5, low_text=0.3,
            width_ths=0.7, height_ths=0.5,
        )

        print(f"DEBUG [OCR]: Pass 1 (preprocessed): {len(results_processed)} blocks")
        print(f"DEBUG [OCR]: Pass 2 (raw):           {len(results_raw)} blocks")

        # Chon pass nao co nhieu text block hon
        if len(results_processed) >= len(results_raw):
            results = results_processed
            print("DEBUG [OCR]: --> Chon Pass 1 (preprocessed)")
        else:
            results = results_raw
            print("DEBUG [OCR]: --> Chon Pass 2 (raw)")

        if not results:
            return "[CANH BAO]: Khong trich xuat duoc van ban tu anh."

        # === DEBUG: In toan bo text blocks ===
        print(f"\nDEBUG [OCR]: === CHI TIET {len(results)} TEXT BLOCKS ===")
        for i, item in enumerate(results):
            bbox, text, conf = item[0], item[1], item[2]
            y_center = (bbox[0][1] + bbox[2][1]) / 2
            x_center = (bbox[0][0] + bbox[2][0]) / 2
            print(f"  [{i:2d}] x={x_center:6.0f} y={y_center:6.0f} conf={conf:.2f} | '{text}'")
        print("DEBUG [OCR]: === END TEXT BLOCKS ===\n")

        # === CLUSTER THANH HANG BANG ===
        rows = _cluster_into_rows(results, y_tolerance=20)

        # === FORMAT OUTPUT ===
        structured_text = _format_rows_as_table(rows)

        # Raw text lam backup
        raw_lines = [item[1].strip() for item in results if item[1].strip() and item[2] > 0.15]
        raw_text = "\n".join(raw_lines)

        output = f"""=== BANG DIEM (DA PHAN TICH CAU TRUC THEO HANG) ===
{structured_text}

=== TOAN BO VAN BAN TRICH XUAT ===
{raw_text}"""

        print(f"DEBUG [OCR]: Output {len(rows)} hang, {len(raw_lines)} dong raw, {len(output)} ky tu")
        return output

    except Exception as e:
        print(f"ERROR [Counselor OCR]: {e}")
        return f"[LOI XU LY ANH]: {str(e)}"


def doc_file(file_obj) -> str:
    """Tool 1: Doc van ban tu file (PDF hoac anh) — tu phat hien loai file."""
    if file_obj is None:
        return ""

    file_name = getattr(file_obj, 'name', '').lower()
    print(f"DEBUG [Counselor]: Dang xu ly file '{file_name}'")

    if file_name.endswith('.pdf'):
        return doc_pdf(file_obj)
    elif file_name.endswith(('.jpg', '.jpeg', '.png')):
        return doc_image(file_obj)
    else:
        return f"[LOI]: Dinh dang file '{file_name}' khong duoc ho tro."


# ======== TOOL 1c: LLM PARSER — DỌN OCR THÀNH BẢNG ĐIỂM SẠCH ========
def _llm_parse_scores(raw_ocr_text: str) -> str:
    """
    Dùng LLM để "dọn" output OCR thô:
    - Nhận diện tên môn học thật (dù bị OCR đọc sai ký tự)
    - Lọc chỉ lấy điểm hợp lệ (thang 0–10, 1 chữ số thập phân)
    - Bỏ qua số trang, mã số, ngày tháng, số không phải điểm
    - Trả về bảng Markdown sạch: Môn học | Điểm
    """
    PARSE_PROMPT = """Bạn là công cụ xử lý dữ liệu OCR học bạ Việt Nam.
Nhiệm vụ: Từ văn bản OCR thô bên dưới, hãy trích xuất ĐÚNG các cặp (Môn học, Điểm).

QUY TẮC BẮT BUỘC:
1. Điểm hợp lệ là số từ 0 đến 10 (ví dụ: 6.5, 8.0, 9, 10, 7.5). LOẠI BỎ các số khác (mã học sinh, ngày tháng, số trang...).
2. Tên môn học phổ biến ở Việt Nam: Toán, Ngữ văn (Văn), Tiếng Anh (Anh), Vật lý (Lý), Hóa học (Hóa), Sinh học (Sinh), Lịch sử (Sử), Địa lý (Địa), GDCD, Tin học.
3. Các môn Ngoại ngữ 2: Tiếng Nhật, Tiếng Trung, Tiếng Pháp, Tiếng Đức, Tiếng Nga.
4. Các môn Năng khiếu: Vẽ, Năng khiếu Mầm non, Năng khiếu Âm nhạc (hoặc Hát), Năng khiếu TDTT (hoặc Thể dục), Năng khiếu SKĐA, Năng khiếu Báo chí.
5. Nếu OCR đọc sai ký tự (ví dụ: "Toin" → "Toán", "Vit Iy" → "Vật lý", "TIEN ANH" → "Tiếng Anh"), hãy sửa lại đúng.
6. Bỏ qua các hàng không phải môn học + điểm (họ tên, trường, lớp, ghi chú...).

Chỉ trả về bảng Markdown theo định dạng này, KHÔNG giải thích gì thêm:
| Môn học | Điểm |
|---------|------|
| Toán | 8.5 |
..."""

    parsed, error_info = call_llm(
        messages=[
            {"role": "system", "content": PARSE_PROMPT},
            {"role": "user",   "content": f"VĂN BẢN OCR THÔ:\n{raw_ocr_text}"}
        ],
        model_list=OPENROUTER_FALLBACK_MODELS,
        temperature=0.0,
        max_tokens=800,
    )
    if parsed:
        print(f"DEBUG [LLM Parser]: Parsed {len(parsed)} chars")
        return parsed
    if error_info:
        print(f"ERROR [LLM Parser]: {error_info['message']} {error_info.get('detail', '')}")
    return raw_ocr_text  # fallback: dùng raw text nếu parser lỗi


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


# ======== HAM CHINH: TU VAN HUONG NGHIEP ========
def process_cv_ocr(cv_file) -> tuple[str, str]:
    """Phase A: OCR file → (raw_ocr, score_table). Tách riêng để app.py wrap st.status."""
    if cv_file is None:
        return "", ""
    raw_ocr = doc_file(cv_file)
    print(f"DEBUG [process_cv_ocr]: Raw OCR {len(raw_ocr)} chars")
    
    score_table = parse_cv_scores(raw_ocr)
    print(f"DEBUG [process_cv_ocr]: Cleaned score table:\n{score_table}")
    
    return raw_ocr, score_table


def parse_cv_scores(raw_ocr_text: str) -> str:
    return _llm_parse_scores(raw_ocr_text)


def parse_scores_to_json(raw_ocr_text: str) -> dict:
    """
    Trích xuất điểm từ OCR text thành JSON tĩnh để score_calculator tính toán.
    Khác với parse_cv_scores() trả Markdown, hàm này trả dict.

    Output: {"Toán": 8.5, "Ngữ văn": 7.0, "Tiếng Anh": 9.0, ...}
    Fallback: {} nếu parse lỗi
    """
    import json as _json

    JSON_PARSE_PROMPT = """Bạn là công cụ trích xuất điểm số từ văn bản OCR học bạ Việt Nam.

NHIỆM VỤ: Từ văn bản OCR bên dưới, trích xuất các cặp (Môn học, Điểm) và trả về JSON.

QUY TẮC BẮT BUỘC:
1. Điểm hợp lệ: số từ 0 đến 10 (ví dụ: 6.5, 8.0, 9, 10). LOẠI BỎ các số khác.
2. Tên môn chuẩn hóa: Toán, Ngữ văn, Tiếng Anh, Vật lý, Hóa học, Sinh học, Lịch sử, Địa lý, GDCD, Tin học.
3. Sửa lỗi OCR: "Toin" → "Toán", "Vit Iy" → "Vật lý", "TIEN ANH" → "Tiếng Anh".
4. Nếu có nhiều cột điểm (Học kỳ 1, HK2, Cả năm), ưu tiên lấy điểm CẢ NĂM.
5. Nếu có nhiều năm học (Lớp 10, 11, 12), ưu tiên lấy LỚP 12.

CHỈ trả về JSON duy nhất, KHÔNG giải thích:
{"Toán": 8.5, "Ngữ văn": 7.0, "Tiếng Anh": 9.0}"""

    parsed, error_info = call_llm(
        messages=[
            {"role": "system", "content": JSON_PARSE_PROMPT},
            {"role": "user",   "content": f"VĂN BẢN OCR THÔ:\n{raw_ocr_text}"}
        ],
        model_list=OPENROUTER_FALLBACK_MODELS,
        temperature=0.0,
        max_tokens=500,
    )

    if parsed:
        # Cố gắng parse JSON từ response
        text = parsed.strip()
        # Loại bỏ markdown code block nếu có
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            result = _json.loads(text)
            if isinstance(result, dict):
                # Validate: chỉ giữ các giá trị số 0-10
                cleaned = {}
                for k, v in result.items():
                    try:
                        score = float(v)
                        if 0 <= score <= 10:
                            cleaned[k] = round(score, 1)
                    except (ValueError, TypeError):
                        continue
                print(f"DEBUG [parse_scores_to_json]: Extracted {len(cleaned)} subjects: {cleaned}")
                return cleaned
        except _json.JSONDecodeError:
            print(f"WARNING [parse_scores_to_json]: Failed to parse JSON from LLM response")

    if error_info:
        print(f"ERROR [parse_scores_to_json]: {error_info['message']}")
    return {}


def _build_system_prompt(score_table: str, user_query: str, main_db_context: str) -> str:
    """Helper xây dựng system prompt chung cho các mode."""
    if score_table:
        data_section = f"""BẢNG ĐIỂM HỌC BẠ (đã được làm sạch từ OCR):
{score_table}

Dựa vào bảng điểm trên, hãy xác định:
- Môn nào điểm CAO (>= 8.0) → đây là thế mạnh
- Môn nào điểm THẤP (< 6.5) → cần cải thiện
Rồi đề xuất ngành phù hợp với thế mạnh đó."""
    else:
        data_section = "Học sinh không đính kèm học bạ. Tư vấn dựa hoàn toàn trên nội dung câu hỏi."

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


def counselor_respond_stream(score_table: str, user_query: str):
    """Phase B: Từ score_table đã xử lý → stream LLM response."""
    main_db_context = retrieve_main_data()
    system_prompt = _build_system_prompt(score_table, user_query, main_db_context)

    return counselor_respond_stream_from_prompt(system_prompt, user_query)


def tu_van_cv(cv_file, user_query: str, stream_output: bool = False) -> str:
    # 1. Phase A: OCR
    _, score_table = process_cv_ocr(cv_file)

    # 2. Truy xuất dữ liệu & Build Prompt
    main_db_context = retrieve_main_data()
    system_prompt = build_counselor_system_prompt(score_table, user_query, main_db_context)

    # 3. Gọi LLM phân tích và tư vấn
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


def tu_van_cv_stream(cv_file, user_query: str):
    response = tu_van_cv(cv_file=cv_file, user_query=user_query, stream_output=True)
    if isinstance(response, str):
        yield response
        return
    yield from response
