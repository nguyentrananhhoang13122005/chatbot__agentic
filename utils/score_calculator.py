# -*- coding: utf-8 -*-
"""
score_calculator.py — Module tính toán tổ hợp khối thi & phân tích điểm mạnh/yếu.
Chạy offline, không gọi API. Dữ liệu tĩnh.
"""

# ======================================================================
# BẢNG MAPPING TỔ HỢP KHỐI THI PHỔ BIẾN (20+ khối)
# Nguồn: Bộ GD&ĐT, Hocmai.vn, Tuyensinh247.com
# ======================================================================
COMBINATIONS: dict[str, list[str]] = {
    # ==================================================================
    # Khối A — Tự nhiên (A00–A18)
    # Nguồn: Bộ GD&ĐT, hocmai.vn, tuyensinh247.com
    # ==================================================================
    "A00": ["Toán", "Vật lý", "Hóa học"],
    "A01": ["Toán", "Vật lý", "Tiếng Anh"],
    "A02": ["Toán", "Vật lý", "Sinh học"],
    "A03": ["Toán", "Vật lý", "Lịch sử"],
    "A04": ["Toán", "Vật lý", "Địa lý"],
    "A05": ["Toán", "Hóa học", "Lịch sử"],
    "A06": ["Toán", "Hóa học", "Địa lý"],
    "A07": ["Toán", "Lịch sử", "Địa lý"],
    "A08": ["Toán", "Lịch sử", "GDCD"],
    "A09": ["Toán", "Địa lý", "GDCD"],
    "A10": ["Toán", "Vật lý", "GDCD"],
    "A11": ["Toán", "Hóa học", "GDCD"],

    # ==================================================================
    # Khối B — Y sinh (B00–B08)
    # ==================================================================
    "B00": ["Toán", "Hóa học", "Sinh học"],
    "B01": ["Toán", "Sinh học", "Lịch sử"],
    "B02": ["Toán", "Sinh học", "Địa lý"],
    "B03": ["Toán", "Sinh học", "Ngữ văn"],
    "B04": ["Toán", "Sinh học", "GDCD"],
    "B08": ["Toán", "Sinh học", "Tiếng Anh"],

    # ==================================================================
    # Khối C — Xã hội / Nhân văn (C00–C20)
    # ==================================================================
    "C00": ["Ngữ văn", "Lịch sử", "Địa lý"],
    "C01": ["Ngữ văn", "Toán", "Vật lý"],
    "C02": ["Ngữ văn", "Toán", "Hóa học"],
    "C03": ["Ngữ văn", "Toán", "Lịch sử"],
    "C04": ["Ngữ văn", "Toán", "Địa lý"],
    "C05": ["Ngữ văn", "Vật lý", "Hóa học"],
    "C06": ["Ngữ văn", "Vật lý", "Sinh học"],
    "C07": ["Ngữ văn", "Hóa học", "Sinh học"],
    "C08": ["Ngữ văn", "Hóa học", "Lịch sử"],
    "C09": ["Ngữ văn", "Vật lý", "Lịch sử"],
    "C10": ["Ngữ văn", "Vật lý", "Tiếng Anh"],
    "C11": ["Ngữ văn", "Hóa học", "Địa lý"],
    "C12": ["Ngữ văn", "Sinh học", "Lịch sử"],
    "C13": ["Ngữ văn", "Sinh học", "Lịch sử"],
    "C14": ["Ngữ văn", "Toán", "GDCD"],
    "C16": ["Ngữ văn", "Vật lý", "GDCD"],
    "C17": ["Ngữ văn", "Hóa học", "GDCD"],
    "C19": ["Ngữ văn", "Lịch sử", "GDCD"],
    "C20": ["Ngữ văn", "Địa lý", "GDCD"],

    # ==================================================================
    # Khối D — Ngoại ngữ + Tổng hợp (D01–D40)
    # Nguồn: bvu.edu.vn, hocmai.vn, topcv.vn, fptshop.com.vn
    # ==================================================================
    # D01-D06: Toán + Ngữ văn + Ngoại ngữ
    "D01": ["Toán", "Ngữ văn", "Tiếng Anh"],
    "D02": ["Toán", "Ngữ văn", "Tiếng Nga"],
    "D03": ["Toán", "Ngữ văn", "Tiếng Pháp"],
    "D04": ["Toán", "Ngữ văn", "Tiếng Trung"],
    "D05": ["Toán", "Ngữ văn", "Tiếng Đức"],       # MỚI
    "D06": ["Toán", "Ngữ văn", "Tiếng Nhật"],

    # D07-D10: Toán + KHTN/KHXH + Tiếng Anh
    "D07": ["Toán", "Hóa học", "Tiếng Anh"],
    "D08": ["Toán", "Sinh học", "Tiếng Anh"],
    "D09": ["Toán", "Lịch sử", "Tiếng Anh"],
    "D10": ["Toán", "Địa lý", "Tiếng Anh"],

    # D11-D15: Ngữ văn + KHTN/KHXH + Tiếng Anh
    "D11": ["Ngữ văn", "Vật lý", "Tiếng Anh"],
    "D12": ["Ngữ văn", "Hóa học", "Tiếng Anh"],    # MỚI
    "D13": ["Ngữ văn", "Sinh học", "Tiếng Anh"],    # MỚI
    "D14": ["Ngữ văn", "Lịch sử", "Tiếng Anh"],
    "D15": ["Ngữ văn", "Địa lý", "Tiếng Anh"],

    # D16-D20: Toán + Địa lý + Ngoại ngữ hiếm
    "D16": ["Toán", "Địa lý", "Tiếng Đức"],        # MỚI
    "D17": ["Toán", "Địa lý", "Tiếng Nga"],         # MỚI
    "D18": ["Toán", "Địa lý", "Tiếng Nhật"],        # MỚI
    "D19": ["Toán", "Địa lý", "Tiếng Pháp"],        # MỚI
    "D20": ["Toán", "Địa lý", "Tiếng Trung"],       # MỚI

    # D21-D25: Toán + Hóa học + Ngoại ngữ hiếm
    "D21": ["Toán", "Hóa học", "Tiếng Đức"],        # MỚI
    "D22": ["Toán", "Hóa học", "Tiếng Nga"],        # MỚI
    "D23": ["Toán", "Hóa học", "Tiếng Nhật"],       # MỚI
    "D24": ["Toán", "Hóa học", "Tiếng Pháp"],       # MỚI
    "D25": ["Toán", "Hóa học", "Tiếng Trung"],      # MỚI

    # D26-D30: Toán + Vật lý + Ngoại ngữ hiếm
    "D26": ["Toán", "Vật lý", "Tiếng Đức"],         # MỚI
    "D27": ["Toán", "Vật lý", "Tiếng Nga"],         # MỚI
    "D28": ["Toán", "Vật lý", "Tiếng Nhật"],        # MỚI
    "D29": ["Toán", "Vật lý", "Tiếng Pháp"],        # MỚI
    "D30": ["Toán", "Vật lý", "Tiếng Trung"],       # MỚI

    # D31-D35: Toán + Sinh học + Ngoại ngữ hiếm
    "D31": ["Toán", "Sinh học", "Tiếng Đức"],       # MỚI
    "D32": ["Toán", "Sinh học", "Tiếng Nga"],       # MỚI
    "D33": ["Toán", "Sinh học", "Tiếng Nhật"],      # MỚI
    "D34": ["Toán", "Sinh học", "Tiếng Pháp"],      # MỚI
    "D35": ["Toán", "Sinh học", "Tiếng Trung"],     # MỚI

    # D36-D40: Toán + Lịch sử + Ngoại ngữ hiếm
    "D36": ["Toán", "Lịch sử", "Tiếng Đức"],       # MỚI
    "D37": ["Toán", "Lịch sử", "Tiếng Nga"],       # MỚI
    "D38": ["Toán", "Lịch sử", "Tiếng Nhật"],      # MỚI
    "D39": ["Toán", "Lịch sử", "Tiếng Pháp"],      # MỚI
    "D40": ["Toán", "Lịch sử", "Tiếng Trung"],     # MỚI
    
    # D66-D70: Ngữ văn + GDCD + Ngoại ngữ
    "D66": ["Ngữ văn", "GDCD", "Tiếng Anh"],       # TRẢ LẠI TÊN ĐÚNG (trước đây bị nhầm thành H06)
    "D67": ["Ngữ văn", "GDCD", "Tiếng Nga"],
    "D68": ["Ngữ văn", "GDCD", "Tiếng Pháp"],
    "D69": ["Ngữ văn", "GDCD", "Tiếng Nhật"],
    "D70": ["Ngữ văn", "GDCD", "Tiếng Trung"],

    # ==================================================================
    # Khối H — Nghệ Thuật / Năng khiếu Mỹ thuật (H00–H08)
    # Cập nhật chuẩn Bộ GD&ĐT: Bắt buộc phải có môn Năng khiếu (Vẽ)
    # ==================================================================
    "H00": ["Ngữ văn", "Vẽ", "Vẽ"],
    "H01": ["Toán", "Ngữ văn", "Vẽ"],
    "H02": ["Toán", "Vẽ", "Vẽ"],
    "H03": ["Toán", "Vật lý", "Vẽ"],    # KHTN thu gọn thành Vật lý
    "H04": ["Toán", "Tiếng Anh", "Vẽ"],
    "H05": ["Ngữ văn", "Lịch sử", "Vẽ"],# KHXH thu gọn thành Lịch sử
    "H06": ["Ngữ văn", "Tiếng Anh", "Vẽ"],
    "H07": ["Toán", "Vẽ", "Vẽ"],
    "H08": ["Ngữ văn", "Lịch sử", "Vẽ"],

    # ==================================================================
    # Khối Năng khiếu (V, M, N, T, S, R)
    # ==================================================================
    # Khối V (Kiến trúc, Mỹ thuật)
    "V00": ["Toán", "Vật lý", "Vẽ"],
    "V01": ["Toán", "Ngữ văn", "Vẽ"],
    "V02": ["Toán", "Tiếng Anh", "Vẽ"],
    
    # Khối M (Mầm non)
    "M00": ["Ngữ văn", "Toán", "Năng khiếu Mầm non"],
    "M01": ["Ngữ văn", "Lịch sử", "Năng khiếu Mầm non"],
    "M02": ["Toán", "Năng khiếu Mầm non", "Năng khiếu Mầm non"],

    # Khối N (Âm nhạc)
    "N00": ["Ngữ văn", "Năng khiếu Âm nhạc", "Năng khiếu Âm nhạc"],
    "N01": ["Ngữ văn", "Năng khiếu Âm nhạc", "Năng khiếu Âm nhạc"],

    # Khối T (TDTT)
    "T00": ["Toán", "Sinh học", "Năng khiếu TDTT"],
    "T01": ["Toán", "Ngữ văn", "Năng khiếu TDTT"],
    "T02": ["Ngữ văn", "Sinh học", "Năng khiếu TDTT"],

    # Khối S (Sân khấu điện ảnh)
    "S00": ["Ngữ văn", "Năng khiếu SKĐA", "Năng khiếu SKĐA"],
    "S01": ["Toán", "Năng khiếu SKĐA", "Năng khiếu SKĐA"],

    # Khối R (Báo chí, nghệ thuật)
    "R00": ["Ngữ văn", "Lịch sử", "Năng khiếu Báo chí"],
    "R01": ["Ngữ văn", "Địa lý", "Năng khiếu Báo chí"],
}

# Tên viết tắt → Tên chuẩn (dùng để normalize input)
SUBJECT_ALIASES: dict[str, str] = {
    "toán": "Toán",
    "toan": "Toán",
    "văn": "Ngữ văn",
    "van": "Ngữ văn",
    "ngữ văn": "Ngữ văn",
    "ngu van": "Ngữ văn",
    "anh": "Tiếng Anh",
    "tiếng anh": "Tiếng Anh",
    "tieng anh": "Tiếng Anh",
    "lý": "Vật lý",
    "ly": "Vật lý",
    "vật lý": "Vật lý",
    "vat ly": "Vật lý",
    "hóa": "Hóa học",
    "hoa": "Hóa học",
    "hóa học": "Hóa học",
    "hoa hoc": "Hóa học",
    "sinh": "Sinh học",
    "sinh học": "Sinh học",
    "sinh hoc": "Sinh học",
    "sử": "Lịch sử",
    "su": "Lịch sử",
    "lịch sử": "Lịch sử",
    "lich su": "Lịch sử",
    "địa": "Địa lý",
    "dia": "Địa lý",
    "địa lý": "Địa lý",
    "dia ly": "Địa lý",
    "gdcd": "GDCD",
    "giáo dục công dân": "GDCD",
    "giao duc cong dan": "GDCD",
    "tin": "Tin học",
    "tin học": "Tin học",
    "tin hoc": "Tin học",
    # Ngoại ngữ phụ
    "nhật": "Tiếng Nhật",
    "tiếng nhật": "Tiếng Nhật",
    "tieng nhat": "Tiếng Nhật",
    "trung": "Tiếng Trung",
    "tiếng trung": "Tiếng Trung",
    "tieng trung": "Tiếng Trung",
    "pháp": "Tiếng Pháp",
    "tiếng pháp": "Tiếng Pháp",
    "tieng phap": "Tiếng Pháp",
    "đức": "Tiếng Đức",
    "tiếng đức": "Tiếng Đức",
    "tieng duc": "Tiếng Đức",
    "nga": "Tiếng Nga",
    "tiếng nga": "Tiếng Nga",
    "tieng nga": "Tiếng Nga",
    # Năng khiếu
    "vẽ": "Vẽ",
    "ve": "Vẽ",
    "vẽ hình họa": "Vẽ",
    "vẽ mỹ thuật": "Vẽ",
    "năng khiếu mầm non": "Năng khiếu Mầm non",
    "nk mầm non": "Năng khiếu Mầm non",
    "năng khiếu âm nhạc": "Năng khiếu Âm nhạc",
    "âm nhạc": "Năng khiếu Âm nhạc",
    "hát": "Năng khiếu Âm nhạc",
    "năng khiếu tdtt": "Năng khiếu TDTT",
    "thể dục": "Năng khiếu TDTT",
    "tdtt": "Năng khiếu TDTT",
    "năng khiếu skđa": "Năng khiếu SKĐA",
    "sân khấu": "Năng khiếu SKĐA",
    "điện ảnh": "Năng khiếu SKĐA",
    "năng khiếu báo chí": "Năng khiếu Báo chí",
    "báo chí": "Năng khiếu Báo chí",
}

# 9 môn chính dùng trong Form nhập điểm
MAIN_SUBJECTS = [
    "Toán", "Ngữ văn", "Tiếng Anh",
    "Vật lý", "Hóa học", "Sinh học",
    "Lịch sử", "Địa lý", "GDCD",
]

# Ngoại ngữ phụ (tùy chọn) — cần cho combo D02-D06, D16-D40
EXTRA_LANGUAGES = [
    "Tiếng Nhật", "Tiếng Trung", "Tiếng Pháp",
    "Tiếng Đức", "Tiếng Nga",
]

# Năng khiếu (tùy chọn) — cần cho combo V, H, M, N, T, S, R
EXTRA_APTITUDE = [
    "Vẽ", 
    "Năng khiếu Mầm non", 
    "Năng khiếu Âm nhạc", 
    "Năng khiếu TDTT", 
    "Năng khiếu SKĐA", 
    "Năng khiếu Báo chí"
]

# Ngưỡng đầu vào tối thiểu theo quy chế 2026
MIN_THRESHOLD = 15.0

# ======================================================================
# ĐIỂM ƯU TIÊN THEO QUY CHẾ 2026 (Bộ GD&ĐT)
# Nguồn: baochinhphu.vn, hocmai.vn, luatminhkhue.vn
# ======================================================================

# Điểm ưu tiên KHU VỰC (xác định theo trường THPT đã học)
PRIORITY_KV: dict[str, float] = {
    "KV1": 0.75,        # Khu vực 1: miền núi, vùng cao, hải đảo
    "KV2-NT": 0.50,     # Khu vực 2 nông thôn
    "KV2": 0.25,        # Khu vực 2: thị xã, thành phố thuộc tỉnh
    "KV3": 0.0,         # Khu vực 3: thành phố trực thuộc TW
}

# Điểm ưu tiên ĐỐI TƯỢNG
PRIORITY_UT: dict[str, float] = {
    "Không": 0.0,       # Không thuộc diện ưu tiên
    "UT2": 1.0,         # Nhóm ưu tiên 2: con thương binh, con liệt sĩ...
    "UT1": 2.0,         # Nhóm ưu tiên 1: dân tộc thiểu số vùng KT-XH khó khăn
}

# Ngưỡng bắt đầu giảm ưu tiên
PRIORITY_REDUCTION_THRESHOLD = 22.5


def calculate_adjusted_bonus(total_3_subjects: float, raw_bonus: float) -> float:
    """
    Tính điểm ưu tiên thực tế theo quy chế 2026 của Bộ GD&ĐT.

    Công thức (nguồn: baochinhphu.vn, hocmai.vn):
        - Nếu tổng điểm 3 môn < 22.5: giữ nguyên raw_bonus
        - Nếu tổng điểm 3 môn >= 22.5:
            Điểm ưu tiên = [(30 - tổng điểm) / 7.5] × raw_bonus

    Ví dụ: Tổng = 25, KV1 (0.75) + UT2 (1.0) = raw 1.75
        → Thực tế = [(30-25)/7.5] × 1.75 = 0.667 × 1.75 = 1.17

    Args:
        total_3_subjects: Tổng điểm 3 môn (chưa cộng ưu tiên)
        raw_bonus: Tổng điểm ưu tiên gốc (KV + ĐT)

    Returns:
        Điểm ưu tiên thực tế (đã giảm nếu cần), làm tròn 2 chữ số
    """
    if raw_bonus <= 0:
        return 0.0
    if total_3_subjects < PRIORITY_REDUCTION_THRESHOLD:
        return round(raw_bonus, 2)
    # Công thức giảm dần: [(30 - tổng) / 7.5] × bonus gốc
    factor = max(0.0, (30.0 - total_3_subjects) / 7.5)
    adjusted = factor * raw_bonus
    return round(adjusted, 2)


def calculate_total_raw_bonus(kv: str = "KV3", ut: str = "Không") -> float:
    """
    Tính tổng điểm ưu tiên GỐC (chưa giảm) từ Khu vực + Đối tượng.
    Thí sinh thuộc nhiều diện chỉ được hưởng mức cao nhất mỗi loại.
    """
    kv_bonus = PRIORITY_KV.get(kv, 0.0)
    ut_bonus = PRIORITY_UT.get(ut, 0.0)
    return round(kv_bonus + ut_bonus, 2)


def normalize_subject_name(name: str) -> str:
    """Chuẩn hóa tên môn học từ nhiều kiểu viết khác nhau."""
    key = name.strip().lower()
    return SUBJECT_ALIASES.get(key, name.strip())


def normalize_scores(raw_scores: dict) -> dict[str, float]:
    """
    Chuẩn hóa tên môn và giá trị điểm.
    Input:  {"toan": 9, "van": "7.5", "anh": 8.25}
    Output: {"Toán": 9.0, "Ngữ văn": 7.5, "Tiếng Anh": 8.25}
    """
    result = {}
    for subject, score in raw_scores.items():
        normalized_name = normalize_subject_name(subject)
        try:
            score_val = float(score)
            score_val = max(0.0, min(10.0, score_val))  # Clamp 0-10
            result[normalized_name] = round(score_val, 2)
        except (ValueError, TypeError):
            continue
    return result


def calculate_all_combinations(scores: dict, bonus: float = 0.0) -> list[dict]:
    """
    Tính điểm cho TẤT CẢ tổ hợp khối thi dựa trên điểm thành phần.

    Args:
        scores: {"Toán": 9.0, "Ngữ văn": 7.0, ...} (đã normalize)
        bonus:  Điểm ưu tiên/cộng thêm (mặc định 0)

    Returns:
        List[dict] sorted descending by total:
        [
            {"code": "D01", "subjects": ["Toán", "Ngữ văn", "Tiếng Anh"],
             "subject_scores": [9.0, 7.0, 9.0], "total": 25.0, "rank": 1},
            ...
        ]
    """
    results = []
    for code, subjects in COMBINATIONS.items():
        # Kiểm tra xem có đủ điểm cho tổ hợp này không
        subject_scores = []
        has_all = True
        for subj in subjects:
            if subj in scores:
                subject_scores.append(scores[subj])
            else:
                has_all = False
                break

        if not has_all:
            continue

        raw_total = round(sum(subject_scores), 2)
        # Tìm môn điểm thấp nhất và cao nhất trong tổ hợp để chuẩn bị cho Thang 40 (Min-Max Range)
        min_sub = min(subject_scores)
        max_sub = max(subject_scores)
        
        # Kiểm tra Điểm liệt
        has_diem_liet = any(score <= 1.0 for score in subject_scores)
        
        # Áp dụng công thức giảm ưu tiên khi >= 22.5 (Quy chế 2026)
        adjusted_bonus = calculate_adjusted_bonus(raw_total, bonus)
        total = round(raw_total + adjusted_bonus, 2)
        
        results.append({
            "code": code,
            "subjects": subjects,
            "subject_scores": subject_scores,
            "min_sub": min_sub,
            "max_sub": max_sub,
            "raw_total": raw_total,
            "raw_bonus": bonus,
            "bonus_applied": adjusted_bonus,
            "total": total,
            "has_diem_liet": has_diem_liet,
            "below_threshold": total < MIN_THRESHOLD or has_diem_liet,
        })

    # Sort descending by total
    results.sort(key=lambda x: x["total"], reverse=True)

    # Assign rank
    for i, item in enumerate(results):
        item["rank"] = i + 1

    return results


def get_top_k_combinations(scores: dict, k: int = 3, bonus: float = 0.0) -> list[dict]:
    """Trả về Top K tổ hợp mạnh nhất."""
    all_combos = calculate_all_combinations(scores, bonus)
    return all_combos[:k]


def get_strength_analysis(scores: dict) -> dict:
    """
    Phân tích điểm mạnh/yếu của học sinh.

    Returns:
        {
            "strongest": ["Toán", "Tiếng Anh"],     # Top 3 môn cao nhất
            "weakest": ["Vật lý", "Hóa học"],       # Top 2 môn thấp nhất
            "category": "Tự nhiên + Ngoại ngữ",     # Xu hướng năng lực
            "avg": 7.2,                              # Điểm trung bình
            "total_subjects": 9,                     # Số môn có điểm
        }
    """
    if not scores:
        return {"strongest": [], "weakest": [], "category": "Chưa xác định", "avg": 0, "total_subjects": 0}

    sorted_subjects = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    strongest = [s[0] for s in sorted_subjects[:3]]
    weakest = [s[0] for s in sorted_subjects[-2:]] if len(sorted_subjects) >= 2 else []
    avg = round(sum(scores.values()) / len(scores), 1)

    # Phân loại xu hướng
    natural_subjects = {"Toán", "Vật lý", "Hóa học", "Sinh học"}
    social_subjects = {"Ngữ văn", "Lịch sử", "Địa lý", "GDCD"}
    lang_subjects = {"Tiếng Anh"}

    natural_avg = _avg_for_group(scores, natural_subjects)
    social_avg = _avg_for_group(scores, social_subjects)
    lang_avg = _avg_for_group(scores, lang_subjects)

    categories = []
    if natural_avg >= 7.0:
        categories.append("Tự nhiên")
    if social_avg >= 7.0:
        categories.append("Xã hội")
    if lang_avg >= 7.5:
        categories.append("Ngoại ngữ")
    if not categories:
        categories.append("Đa năng" if avg >= 6.5 else "Cần cải thiện")

    return {
        "strongest": strongest,
        "weakest": weakest,
        "category": " + ".join(categories),
        "avg": avg,
        "total_subjects": len(scores),
        "natural_avg": natural_avg,
        "social_avg": social_avg,
        "lang_avg": lang_avg,
    }


def _avg_for_group(scores: dict, group: set) -> float:
    """Tính điểm trung bình cho một nhóm môn."""
    vals = [scores[s] for s in group if s in scores]
    return round(sum(vals) / len(vals), 1) if vals else 0.0


def format_combination_display(combo: dict) -> str:
    """Format tổ hợp để hiển thị trên UI. Hiển thị bonus nếu có."""
    parts = [f"{s}: {sc}" for s, sc in zip(combo["subjects"], combo["subject_scores"])]
    bonus = combo.get("bonus_applied", 0)
    if bonus and bonus > 0:
        return (
            f"{combo['code']} ({' + '.join(combo['subjects'])}) "
            f"= {combo.get('raw_total', combo['total'])} + {bonus}đ ưu tiên "
            f"= **{combo['total']}** điểm"
        )
    return f"{combo['code']} ({' + '.join(combo['subjects'])}) = {combo['total']} điểm"
