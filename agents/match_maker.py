# -*- coding: utf-8 -*-
"""
match_maker.py — Động cơ matching Top K trường/ngành phù hợp.
Sử dụng Pandas truy vấn trực tiếp data_diem_chuan_verified.csv.
"""
import os
import pandas as pd
from utils.score_calculator import (
    get_top_k_combinations,
    get_strength_analysis,
    normalize_scores,
    format_combination_display,
    MIN_THRESHOLD,
)
from utils.admission_matcher import find_top_k_schools_exam
from utils.method_normalizer import is_exam_method
from llm_client import call_llm

# ======================================================================
# LOAD DATA (Lazy singleton — chỉ load 1 lần)
# ======================================================================
_df_verified: pd.DataFrame | None = None

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "data_diem_chuan_verified.csv")

# Các phương thức xét tuyển sử dụng thang điểm 30 (3 môn x 10)
SCALE_30_METHODS = [
    "Xét điểm Học bạ THPT",
    "Xét điểm thi THPT",
]


def _load_verified_data() -> pd.DataFrame:
    """Load và cache DataFrame từ CSV."""
    global _df_verified
    if _df_verified is not None:
        return _df_verified

    if not os.path.exists(DATA_PATH):
        print(f"WARNING [MatchMaker]: File not found: {DATA_PATH}")
        _df_verified = pd.DataFrame()
        return _df_verified

    try:
        df = pd.read_csv(DATA_PATH, encoding="utf-8")
        # Chuẩn hóa tên cột (loại bỏ khoảng trắng thừa)
        df.columns = df.columns.str.strip()
        # Chuyển Điểm chuẩn sang float, bỏ NaN
        df["Điểm chuẩn"] = pd.to_numeric(df["Điểm chuẩn"], errors="coerce")
        _df_verified = df
        print(f"DEBUG [MatchMaker]: Loaded {len(df)} rows from verified DB")
        return _df_verified
    except Exception as e:
        print(f"ERROR [MatchMaker]: Failed to load data: {e}")
        _df_verified = pd.DataFrame()
        return _df_verified


def _parse_to_hop_column(to_hop_str: str) -> set[str]:
    """
    Parse cột 'Tổ hợp môn' thành set các mã khối.
    Xử lý cả 2 loại separator: dấu `;` (11,385 dòng) và dấu `,` (435 dòng).
    Lọc chỉ giữ mã tổ hợp hợp lệ (1 chữ cái + 2 chữ số, vd: A00, D01, X23).
    """
    import re
    if pd.isna(to_hop_str) or not str(to_hop_str).strip():
        return set()
    # Split bằng cả ; và , (khoảng trắng tùy chọn)
    raw_codes = re.split(r'[;,]\s*', str(to_hop_str))
    # Chỉ giữ mã hợp lệ: 1 chữ cái + 2-3 chữ số (A00, D01, AH2, DD2...)
    valid = set()
    for code in raw_codes:
        c = code.strip().upper()
        if re.match(r'^[A-Z]{1,2}\d{1,2}$', c):
            valid.add(c)
    return valid


def _find_top_k_schools_legacy(
    student_scores: dict,
    methods: list[str] | None = None,
    k: int = 5,
    bonus: float = 0.0,
    year_priority: list[int] | None = None,
    top_n_combos: int = 5,
    province: str | None = None,
    major: str | None = None,
) -> dict:
    """
    Tìm Top K trường/ngành phù hợp nhất dựa trên điểm số học sinh.

    Args:
        student_scores: {"Toán": 9, "Ngữ văn": 7, ...} (raw hoặc normalized)
        methods: Danh sách phương thức xét tuyển (mặc định: Học bạ + Thi THPT)
        k: Số trường/ngành trả về (mặc định: 5)
        bonus: Điểm ưu tiên
        year_priority: Thứ tự ưu tiên năm (mặc định: [2025, 2024])
        top_n_combos: Số tổ hợp mạnh nhất để tìm kiếm (mặc định: 5)

    Returns:
        {
            "scores": {...},              # Điểm đã normalize
            "top_combinations": [...],    # Top tổ hợp mạnh nhất
            "strength": {...},            # Phân tích điểm mạnh/yếu
            "matched_schools": DataFrame, # Bảng Top K trường
            "warnings": [...],            # Cảnh báo (nếu có)
        }
    """
    if methods is None:
        methods = SCALE_30_METHODS
    if year_priority is None:
        year_priority = [2025, 2024]

    # --- Normalize scores ---
    scores = normalize_scores(student_scores)
    if not scores:
        return {"error": "Không có dữ liệu điểm hợp lệ."}

    # --- Tính tổ hợp ---
    top_combos = get_top_k_combinations(scores, k=top_n_combos, bonus=bonus)
    if not top_combos:
        return {"error": "Không tìm được tổ hợp khối thi phù hợp. Vui lòng nhập đủ ít nhất 3 môn."}

    combo_codes = {c["code"] for c in top_combos}

    # --- Phân tích điểm mạnh ---
    strength = get_strength_analysis(scores)

    # --- Cảnh báo ---
    warnings = []
    diem_liet_combos = [c for c in top_combos if c.get("has_diem_liet")]
    if diem_liet_combos:
        codes = ", ".join(c["code"] for c in diem_liet_combos)
        warnings.append(
            f"🚨 CẢNH BÁO ĐỎ: Tổ hợp {codes} có môn bị Điểm Liệt (<= 1.0). "
            f"Theo quy chế của Bộ GD&ĐT, bạn không đủ điều kiện tốt nghiệp và xét tuyển Đại học bằng tổ hợp này."
        )
    
    below_threshold_combos = [c for c in top_combos if c.get("below_threshold") and not c.get("has_diem_liet")]
    if below_threshold_combos:
        codes = ", ".join(c["code"] for c in below_threshold_combos)
        warnings.append(
            f"⚠️ Tổ hợp {codes} có tổng điểm dưới ngưỡng tối thiểu {MIN_THRESHOLD} điểm "
            f"theo quy chế 2026."
        )

    # --- Load data ---
    df = _load_verified_data()
    if df.empty:
        return {
            "scores": scores,
            "top_combinations": top_combos,
            "strength": strength,
            "matched_schools": pd.DataFrame(),
            "warnings": warnings + ["⚠️ Dữ liệu điểm chuẩn chưa sẵn sàng."],
        }

    # --- Filter Step 1: Phương thức xét tuyển ---
    method_lower = [m.lower().strip() for m in methods]
    mask_method = df["Phương thức xét tuyển"].str.lower().str.strip().isin(method_lower)
    df_filtered = df[mask_method].copy()

    # --- Filter Step 2: Lọc bỏ ĐGNL (>40), giữ thang 30 và 40 ---
    df_filtered = df_filtered[df_filtered["Điểm chuẩn"] <= 40.0].copy()
    df_filtered = df_filtered[df_filtered["Điểm chuẩn"] > 0.0].copy()

    # --- Lọc theo Ngành (Major) ---
    if major:
        from utils.method_normalizer import normalize_method
        major_norm = normalize_method(major)
        mask_major = df_filtered["Tên ngành"].apply(lambda x: major_norm in normalize_method(x))
        df_filtered = df_filtered[mask_major].copy()
        
    # --- Lọc theo Tỉnh/Thành phố ---
    if province:
        try:
            import json
            json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "university_provinces.json")
            with open(json_path, 'r', encoding='utf-8') as f:
                prov_map = json.load(f)
            # Map province vào dataframe, fillna bằng "Khác"
            df_filtered["Tỉnh/Thành phố"] = df_filtered["Trường"].map(prov_map).fillna("Khác")
            df_filtered = df_filtered[df_filtered["Tỉnh/Thành phố"] == province].copy()
        except Exception as e:
            warnings.append(f"⚠️ Không thể tải dữ liệu Tỉnh/Thành phố: {e}")

    if df_filtered.empty:
        return {
            "scores": scores,
            "top_combinations": top_combos,
            "strength": strength,
            "matched_schools": pd.DataFrame(),
            "warnings": warnings + ["⚠️ Không tìm thấy dữ liệu phù hợp cho phương thức xét tuyển đã chọn."],
        }

    # --- Filter Step 3: Năm ưu tiên ---
    df_year = pd.DataFrame()
    for year in year_priority:
        df_y = df_filtered[df_filtered["Năm"] == year]
        if not df_y.empty:
            df_year = df_y
            break

    if df_year.empty:
        df_year = df_filtered  # Fallback: dùng tất cả các năm

    # --- Filter Step 4: Tổ hợp môn khớp ---
    def has_matching_combo(to_hop_str):
        school_combos = _parse_to_hop_column(to_hop_str)
        return bool(school_combos & combo_codes)

    df_combo = df_year[df_year["Tổ hợp môn"].apply(has_matching_combo)].copy()

    if df_combo.empty:
        warnings.append("⚠️ Không tìm thấy trường nào xét tuyển các tổ hợp mạnh nhất của bạn. Đang mở rộng tìm kiếm...")
        # Fallback: mở rộng sang tất cả tổ hợp có thể tính được
        all_combos = get_top_k_combinations(scores, k=20, bonus=bonus)
        all_codes = {c["code"] for c in all_combos}

        def has_any_combo(to_hop_str):
            school_combos = _parse_to_hop_column(to_hop_str)
            return bool(school_combos & all_codes)

        df_combo = df_year[df_year["Tổ hợp môn"].apply(has_any_combo)].copy()
        combo_codes.update(all_codes)
        top_combos = all_combos

    # --- Lọc bỏ thang điểm ĐGNL (>40) ---
    # Thang điểm > 40 là điểm Đánh giá năng lực (scale 1200), không thể match bằng điểm THPT
    df_combo = df_combo[df_combo["Điểm chuẩn"] <= 40].copy()

    if df_combo.empty:
        return {
            "scores": scores,
            "top_combinations": top_combos,
            "strength": strength,
            "matched_schools": pd.DataFrame(),
            "warnings": warnings + ["⚠️ Không tìm thấy trường THPT/Học bạ phù hợp (chỉ còn điểm ĐGNL)."],
        }

    # --- Tính Delta cho mỗi dòng ---
    # combo_score_map giờ lưu: (total, raw_total, raw_bonus)
    # Loại bỏ TẤT CẢ các tổ hợp có Điểm Liệt khỏi việc so khớp (Fail-safe)
    combo_score_map = {
        c["code"]: (c["total"], c.get("raw_total", 0), c.get("raw_bonus", 0)) 
        for c in top_combos if not c.get("has_diem_liet")
    }
    # Lấy điểm môn cao nhất và thấp nhất trong từng tổ hợp (dùng cho Zero-Guesswork Min-Max Range)
    combo_max_subject_map = {c["code"]: c.get("max_sub", 0) for c in top_combos}
    combo_min_subject_map = {c["code"]: c.get("min_sub", 0) for c in top_combos}

    def calc_best_delta(row):
        """Tìm tổ hợp khớp tốt nhất (Delta cao nhất) cho mỗi trường."""
        school_combos = _parse_to_hop_column(row["Tổ hợp môn"])
        matching = school_combos & set(combo_score_map.keys())
        if not matching:
            return None, None, None, None, False
            
        best_code = None
        best_delta = -999
        is_scale_40 = False
        major_name = str(row.get("Tên ngành", "")).lower()
        
        # Suy luận Rule-based (Trường hợp 1: Thang 40 rõ ràng do điểm chuẩn > 30)
        if row["Điểm chuẩn"] > 30:
            is_scale_40 = True
        # Suy luận Rule-based (Trường hợp 2: Bắt từ khóa các ngành THƯỜNG XUYÊN nhân đôi môn chính)
        elif any(kw in major_name for kw in [
            "ngôn ngữ", "sư phạm tiếng", "kiến trúc", "mỹ thuật", 
            "thiết kế đồ họa", "thiết kế nội thất", "thiết kế thời trang", "thiết kế mỹ thuật", "thiết kế công nghiệp",
            "mầm non", "âm nhạc", "thanh nhạc", "thể dục", "thể thao"
        ]):
            is_scale_40 = True
            
        for code in matching:
            student_total, raw_total, raw_bonus = combo_score_map[code]
            
            # Xử lý chuẩn hóa Delta
            if is_scale_40:
                # Kịch bản tốt nhất: Trường nhân đôi môn có điểm cao nhất của thí sinh
                max_sub = combo_max_subject_map.get(code, 0)
                raw_40_max = raw_total + max_sub
                
                # Áp dụng công thức Bộ GD&ĐT cho điểm ưu tiên thang 40
                bonus_40_max = raw_bonus * (4/3)
                if raw_40_max >= 30:
                    adjusted_bonus_40_max = max(0.0, ((40.0 - raw_40_max) / 10.0) * bonus_40_max)
                else:
                    adjusted_bonus_40_max = bonus_40_max
                    
                student_total_40_max = raw_40_max + adjusted_bonus_40_max
                delta = student_total_40_max - row["Điểm chuẩn"]
            else:
                delta = student_total - row["Điểm chuẩn"]
                
            if delta > best_delta:
                best_delta = delta
                best_code = code
                
        # Trả về điểm student_total tương ứng với thang điểm của trường
        if not best_code:
            return None, None, None, None, False
            
        student_total, raw_total, raw_bonus = combo_score_map.get(best_code, (0,0,0))
        if is_scale_40:
            # Kịch bản tốt nhất (Max)
            max_sub = combo_max_subject_map.get(best_code, 0)
            raw_40_max = raw_total + max_sub
            bonus_40_max = raw_bonus * (4/3)
            if raw_40_max >= 30:
                adjusted_bonus_40_max = max(0.0, ((40.0 - raw_40_max) / 10.0) * bonus_40_max)
            else:
                adjusted_bonus_40_max = bonus_40_max
            final_max_total = raw_40_max + adjusted_bonus_40_max

            # Kịch bản xấu nhất (Min)
            min_sub = combo_min_subject_map.get(best_code, 0)
            raw_40_min = raw_total + min_sub
            if raw_40_min >= 30:
                adjusted_bonus_40_min = max(0.0, ((40.0 - raw_40_min) / 10.0) * bonus_40_max)
            else:
                adjusted_bonus_40_min = bonus_40_max
            final_min_total = raw_40_min + adjusted_bonus_40_min

            return best_code, round(final_min_total, 2), round(final_max_total, 2), round(best_delta, 2), True
        else:
            return best_code, round(student_total, 2), round(student_total, 2), round(best_delta, 2), False

    results = df_combo.apply(calc_best_delta, axis=1, result_type="expand")
    df_combo["Tổ hợp khớp"] = results[0]
    df_combo["Điểm min"] = results[1]
    df_combo["Điểm của bạn"] = results[2]
    df_combo["Delta"] = results[3]
    df_combo["Thang_40"] = results[4]

    # Loại bỏ rows không có Delta
    df_combo = df_combo.dropna(subset=["Delta"])

    # --- Filter Step 5: Delta >= -2.0 (mở rộng vùng thử thách) ---
    df_result = df_combo[df_combo["Delta"] >= -2.0].copy()

    # --- Phân tier ---
    def assign_tier(delta):
        if delta >= 1.5:
            return "✅ AN TOÀN"
        elif delta >= 0:
            return "⚡ VỪA SỨC"
        else:
            return "🎯 THỬ THÁCH"

    df_result["Tier"] = df_result["Delta"].apply(assign_tier)

    # --- Deduplicate: Mỗi trường chỉ giữ 1 ngành khớp nhất ---
    df_result = df_result.drop_duplicates(subset=["Trường", "Tên ngành"], keep="first")

    # --- MAJOR #3 FIX: Phân bổ tier đa dạng để chiến lược nguyện vọng hợp lý ---
    # Đảm bảo kết quả có cả 3 mức: AN TOÀN + VỪA SỨC + THỬ THÁCH
    df_safe = df_result[df_result["Tier"] == "✅ AN TOÀN"].sort_values("Delta", ascending=True)
    df_fit = df_result[df_result["Tier"] == "⚡ VỪA SỨC"].sort_values("Delta", ascending=True)
    df_challenge = df_result[df_result["Tier"] == "🎯 THỬ THÁCH"].sort_values("Delta", ascending=False)

    # Tính quota tối thiểu mỗi tier dựa trên k
    if k <= 3:
        min_safe, min_fit, min_challenge = 1, 1, 1
    elif k <= 5:
        min_safe, min_fit, min_challenge = 1, 2, 1
    elif k <= 10:
        min_safe, min_fit, min_challenge = 2, 4, 2
    else:
        min_safe, min_fit, min_challenge = 3, 6, 3

    # Lấy quota tối thiểu từ mỗi tier
    selected = pd.DataFrame()
    taken_safe = df_safe.head(min(min_safe, len(df_safe)))
    taken_fit = df_fit.head(min(min_fit, len(df_fit)))
    taken_challenge = df_challenge.head(min(min_challenge, len(df_challenge)))
    selected = pd.concat([taken_fit, taken_safe, taken_challenge], ignore_index=True)

    # Nếu chưa đủ k, bổ sung từ pool còn lại (ưu tiên VỪA SỨC → AN TOÀN → THỬ THÁCH)
    remaining_slots = k - len(selected)
    if remaining_slots > 0:
        used_indices = set(selected.index.tolist())
        # Sắp xếp toàn bộ pool theo tier rồi Delta
        tier_order = {"⚡ VỪA SỨC": 0, "✅ AN TOÀN": 1, "🎯 THỬ THÁCH": 2}
        df_rest = df_result[~df_result.index.isin(
            pd.concat([taken_safe, taken_fit, taken_challenge]).index
        )].copy()
        df_rest["_tier_order"] = df_rest["Tier"].map(tier_order)
        df_rest = df_rest.sort_values(by=["_tier_order", "Delta"], ascending=[True, True])
        extra = df_rest.head(remaining_slots)
        if "_tier_order" in extra.columns:
            extra = extra.drop(columns=["_tier_order"])
        selected = pd.concat([selected, extra], ignore_index=True)

    df_top_k = selected.head(k).copy()

    # Dọn dẹp cột hiển thị
    display_columns = ["Trường", "Mã ngành", "Tên ngành", "Phương thức xét tuyển",
                       "Điểm chuẩn", "Tổ hợp khớp", "Điểm min", "Điểm của bạn", "Delta", "Tier", "Năm", "Thang_40"]
    existing_cols = [c for c in display_columns if c in df_top_k.columns]
    df_top_k = df_top_k[existing_cols].reset_index(drop=True)

    # Drop internal columns
    for col in ["_tier_order"]:
        if col in df_top_k.columns:
            df_top_k = df_top_k.drop(columns=[col])

    return {
        "scores": scores,
        "top_combinations": top_combos[:top_n_combos],
        "strength": strength,
        "matched_schools": df_top_k,
        "total_found": len(df_result),
        "warnings": warnings,
    }


def find_top_k_schools(
    student_scores: dict,
    methods: list[str] | None = None,
    k: int = 5,
    bonus: float = 0.0,
    year_priority: list[int] | None = None,
    top_n_combos: int = 5,
    province: str | None = None,
    major: str | None = None,
) -> dict:
    """
    Route exam-only analysis through the deterministic SQLite pipeline.

    Transcript and mixed-mode requests intentionally keep the existing legacy
    behavior until the UI phase separates modes.
    """
    if methods and _is_exam_only(methods):
        return find_top_k_schools_exam(student_scores, k, bonus, year_priority, top_n_combos, province, major)
    return _find_top_k_schools_legacy(student_scores, methods, k, bonus, year_priority, top_n_combos, province, major)


def _is_exam_only(methods: list[str]) -> bool:
    return bool(methods) and all(is_exam_method(method) for method in methods)


def _to_number(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _format_number(value) -> str:
    number = _to_number(value)
    if number is None:
        return _safe_text(value, "")
    return f"{number:.2f}".rstrip("0").rstrip(".")


def _safe_text(value, default: str = "Không rõ") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return default
    return text


def _format_student_admission_score(row) -> str:
    min_score = _to_number(row.get("Điểm min"))
    max_score = _to_number(row.get("Điểm của bạn"))
    if min_score is not None and max_score is not None and abs(min_score - max_score) > 0.001:
        return f"{_format_number(min_score)} - {_format_number(max_score)}"
    return _format_number(row.get("Điểm của bạn")) or "Không rõ"


def _format_cutoff_score(row) -> str:
    cutoff = _format_number(row.get("Điểm chuẩn"))
    if not cutoff:
        return "Không rõ"
    year = _safe_text(row.get("Năm"), "")
    return f"{cutoff} ({year})" if year else cutoff


def _format_admission_gap(row) -> str:
    gap = _to_number(row.get("Delta"))
    if gap is None:
        return "chưa đủ dữ liệu để so sánh điểm"
    if abs(gap) < 0.05:
        return "xấp xỉ điểm chuẩn"
    if gap > 0:
        return f"cao hơn điểm chuẩn {_format_number(abs(gap))} điểm"
    return f"thấp hơn điểm chuẩn {_format_number(abs(gap))} điểm"


def _format_opportunity_label(row) -> str:
    tier = _safe_text(row.get("Tier"), "")
    gap = _to_number(row.get("Delta"))
    if "AN TOÀN" in tier:
        return "cơ hội cao"
    if "VỪA SỨC" in tier:
        return "cạnh tranh vừa"
    if "THỬ THÁCH" in tier:
        if gap is not None and gap >= -1.0:
            return "rủi ro có cơ sở"
        return "rủi ro cao"
    return "cần kiểm tra thêm"


def _format_list(items, empty_text: str) -> str:
    if not items:
        return empty_text
    return "\n".join(f"- {_safe_text(item)}" for item in items)


def _format_user_filters(filters: dict) -> str:
    if not filters:
        return "- Chưa có bộ lọc nâng cao."
    mode_map = {
        "exam": "Xét điểm thi THPT",
        "transcript": "Xét điểm học bạ THPT",
    }
    mode = mode_map.get(filters.get("mode"), _safe_text(filters.get("mode"), "Không rõ"))
    province = _safe_text(filters.get("province"), "Tất cả")
    major = _safe_text(filters.get("major"), "Không chọn")
    top_k = _safe_text(filters.get("top_k"), "Không rõ")
    return "\n".join(
        [
            f"- Phương thức/mode: {mode}",
            f"- Top K người dùng chọn: {top_k}",
            f"- Tỉnh/thành: {province}",
            f"- Ngành mong muốn: {major}",
        ]
    )


def _format_combo_for_prompt(combo: dict) -> str:
    try:
        return format_combination_display(combo)
    except (KeyError, TypeError):
        code = _safe_text(combo.get("code") if isinstance(combo, dict) else None)
        total = _format_number(combo.get("total") if isinstance(combo, dict) else None)
        subjects = combo.get("subjects", []) if isinstance(combo, dict) else []
        subject_text = " + ".join(str(item) for item in subjects) if subjects else "chưa rõ môn"
        return f"{code}: {subject_text} = {total or 'không rõ'} điểm"


def _condition_risk_score(row) -> int:
    text = " ".join(
        _safe_text(row.get(col), "")
        for col in ["Chú thích", "Công thức"]
    ).lower()
    risk_terms = [
        "thiếu",
        "chưa rõ",
        "không rõ",
        "cần",
        "ielts",
        "toefl",
        "sat",
        "chứng chỉ",
        "học bạ",
        "năng khiếu",
    ]
    return int(any(term in text for term in risk_terms))


def _combo_rank(row, top_combos: list[dict]) -> int:
    combo = _safe_text(row.get("Tổ hợp khớp"), "")
    for index, item in enumerate(top_combos):
        if combo and combo == _safe_text(item.get("code"), ""):
            return index
    return len(top_combos) + 1


def _filter_match_score(row, filters: dict) -> int:
    score = 0
    major = _safe_text(filters.get("major"), "").lower() if filters else ""
    province = _safe_text(filters.get("province"), "").lower() if filters else ""
    if major and major in _safe_text(row.get("Tên ngành"), "").lower():
        score += 1
    if province and province in _safe_text(row.get("Tỉnh/Thành phố"), "").lower():
        score += 1
    return score


def _planner_work_frame(result: dict) -> pd.DataFrame:
    df = result.get("matched_schools", pd.DataFrame())
    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()
    filters = result.get("user_filters", {}) or {}
    top_combos = result.get("top_combinations", []) or []
    work = df.copy().reset_index(drop=True)
    work["__planner_id"] = range(len(work))
    work["__original_pos"] = range(len(work))
    work["__gap"] = work["Delta"].apply(_to_number) if "Delta" in work.columns else None
    work["__filter_score"] = work.apply(lambda row: _filter_match_score(row, filters), axis=1)
    work["__condition_risk"] = work.apply(_condition_risk_score, axis=1)
    work["__combo_rank"] = work.apply(lambda row: _combo_rank(row, top_combos), axis=1)
    return work


def _clean_planner_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    internal_cols = [col for col in df.columns if str(col).startswith("__")]
    return df.drop(columns=internal_cols, errors="ignore").reset_index(drop=True)


def _sort_focus_candidates(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df.sort_values(
        by=["__filter_score", "__condition_risk", "__combo_rank", "__gap", "__original_pos"],
        ascending=[False, True, True, False, True],
    )


def _priority_role(row) -> int:
    tier = _safe_text(row.get("Tier"), "")
    gap = _to_number(row.get("__gap"))
    if "THỬ THÁCH" in tier:
        return 0 if gap is not None and gap >= -1.0 else 3
    if "VỪA SỨC" in tier:
        return 1
    if "AN TOÀN" in tier:
        return 2
    return 4


def _sort_priority_order(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    work = df.copy()
    work["__priority_role"] = work.apply(_priority_role, axis=1)
    return work.sort_values(
        by=[
            "__priority_role",
            "__filter_score",
            "__condition_risk",
            "__combo_rank",
            "__gap",
            "__original_pos",
        ],
        ascending=[True, False, True, True, False, True],
    )


def _select_focus_schools(result: dict, limit: int = 5, strategy: str = "balanced") -> dict:
    work = _planner_work_frame(result)
    if work.empty:
        empty = pd.DataFrame()
        return {
            "focus_schools": empty,
            "reference_schools": empty,
            "priority_order": empty,
            "planner_notes": ["Không có dữ liệu trường/ngành để phân tích sâu."],
        }

    limit = max(1, min(limit, len(work)))
    if len(work) <= limit:
        priority = _sort_priority_order(work)
        return {
            "focus_schools": _clean_planner_columns(priority),
            "reference_schools": pd.DataFrame(),
            "priority_order": _clean_planner_columns(priority),
            "planner_notes": [
                f"Số kết quả thực tế là {len(work)}, nên phân tích toàn bộ danh sách.",
                f"Chiến lược xếp thứ tự đang dùng: {strategy}.",
            ],
        }

    selected_ids: list[int] = []
    selected_schools: set[str] = set()

    def add_from(pool: pd.DataFrame, desired: int, allow_same_school: bool = False) -> None:
        if desired <= 0 or pool.empty:
            return
        added = 0
        for _, row in _sort_focus_candidates(pool).iterrows():
            if len(selected_ids) >= limit or added >= desired:
                return
            row_id = int(row["__planner_id"])
            school = _safe_text(row.get("Trường"), "")
            if row_id in selected_ids:
                continue
            if not allow_same_school and school and school in selected_schools:
                continue
            selected_ids.append(row_id)
            if school:
                selected_schools.add(school)
            added += 1

    challenge = work[
        work["Tier"].astype(str).str.contains("THỬ THÁCH", na=False)
        & (work["__gap"].fillna(-999) >= -1.0)
    ]
    fit = work[work["Tier"].astype(str).str.contains("VỪA SỨC", na=False)]
    safe = work[work["Tier"].astype(str).str.contains("AN TOÀN", na=False)]

    add_from(challenge, 1)
    add_from(fit, min(3, max(0, limit - len(selected_ids))))
    add_from(safe, min(1, max(0, limit - len(selected_ids))))

    remaining = work[~work["__planner_id"].isin(selected_ids)]
    add_from(remaining, limit - len(selected_ids))
    if len(selected_ids) < limit:
        add_from(remaining, limit - len(selected_ids), allow_same_school=True)

    focus = work[work["__planner_id"].isin(selected_ids)]
    priority = _sort_priority_order(focus)
    reference = _sort_focus_candidates(work[~work["__planner_id"].isin(selected_ids)])
    challenge_count = len(focus[focus["Tier"].astype(str).str.contains("THỬ THÁCH", na=False)])
    fit_count = len(focus[focus["Tier"].astype(str).str.contains("VỪA SỨC", na=False)])
    safe_count = len(focus[focus["Tier"].astype(str).str.contains("AN TOÀN", na=False)])

    return {
        "focus_schools": _clean_planner_columns(priority),
        "reference_schools": _clean_planner_columns(reference),
        "priority_order": _clean_planner_columns(priority),
        "planner_notes": [
            f"Số kết quả thực tế là {len(work)}, hệ thống chọn {len(focus)} lựa chọn để phân tích sâu.",
            (
                "Chiến lược mặc định balanced: ưu tiên có lựa chọn thử thách có cơ sở, "
                "nhóm vừa sức làm nòng cốt và nhóm an toàn làm backup."
            ),
            (
                "Cơ cấu danh sách phân tích sâu: "
                f"{challenge_count} thử thách, {fit_count} vừa sức, {safe_count} an toàn."
            ),
            "Ngưỡng thử thách có cơ sở: thấp hơn điểm chuẩn không quá 1.0 điểm.",
        ],
    }


def _format_school_rows(df: pd.DataFrame, empty_text: str = "(Không có dữ liệu)") -> str:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return empty_text
    lines: list[str] = []
    for index, (_, row) in enumerate(df.iterrows(), start=1):
        school = _safe_text(row.get("Trường"))
        major = _safe_text(row.get("Tên ngành"))
        method = _safe_text(row.get("Phương thức xét tuyển"))
        combo = _safe_text(row.get("Tổ hợp khớp"))
        tier = _safe_text(row.get("Tier"))
        note = _safe_text(row.get("Chú thích"), "")
        formula = _safe_text(row.get("Công thức"), "")
        detail_parts = [
            f"Phương thức: {method}",
            f"Tổ hợp khớp: {combo}",
            f"Điểm của học sinh: {_format_student_admission_score(row)}",
            f"Điểm chuẩn: {_format_cutoff_score(row)}",
            f"Chênh lệch điểm: {_format_admission_gap(row)}",
            f"Nhóm: {tier}",
            f"Mức cơ hội định tính: {_format_opportunity_label(row)}",
        ]
        if note:
            detail_parts.append(f"Chú thích: {note}")
        if formula:
            detail_parts.append(f"Công thức: {formula}")
        lines.append(f"{index}. {school} - {major}\n   - " + "\n   - ".join(detail_parts))
    return "\n".join(lines)


def _format_reference_rows(df: pd.DataFrame) -> str:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return "Không có danh sách tham khảo thêm."
    lines = []
    for index, (_, row) in enumerate(df.iterrows(), start=1):
        lines.append(
            f"{index}. {_safe_text(row.get('Trường'))} - {_safe_text(row.get('Tên ngành'))} "
            f"({_safe_text(row.get('Tier'))}; {_format_admission_gap(row)})"
        )
    return "\n".join(lines)


def _format_priority_order(df: pd.DataFrame) -> str:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return "Không có thứ tự nguyện vọng đề xuất."
    lines = []
    for index, (_, row) in enumerate(df.iterrows(), start=1):
        lines.append(
            f"{index}. {_safe_text(row.get('Trường'))} - {_safe_text(row.get('Tên ngành'))}: "
            f"{_format_opportunity_label(row)}, {_format_admission_gap(row)}"
        )
    return "\n".join(lines)


def build_analysis_prompt(result: dict) -> str:
    """
    Xây dựng System Prompt cho LLM phân tích kết quả matching.
    """
    scores = result.get("scores", {})
    strength = result.get("strength", {})
    top_combos = result.get("top_combinations", [])
    df = result.get("matched_schools", pd.DataFrame())
    planner = _select_focus_schools(result)

    score_lines = "\n".join(
        f"- {subject}: {_format_number(score)}"
        for subject, score in scores.items()
    ) or "- Không có dữ liệu điểm."

    combo_lines = "\n".join(
        f"{i + 1}. {_format_combo_for_prompt(combo)}"
        for i, combo in enumerate(top_combos[:5])
    ) or "Không có tổ hợp đủ dữ liệu."

    total_displayed = len(df) if isinstance(df, pd.DataFrame) else 0
    total_found = result.get("total_found", total_displayed)
    filters_text = _format_user_filters(result.get("user_filters", {}) or {})
    warning_text = _format_list(result.get("warnings", []), "Không có cảnh báo.")
    missing_text = _format_list(result.get("missing_inputs", []), "Không có dữ liệu điều kiện còn thiếu.")
    focus_lines = _format_school_rows(planner["focus_schools"])
    reference_lines = _format_reference_rows(planner["reference_schools"])
    priority_lines = _format_priority_order(planner["priority_order"])
    planner_notes = _format_list(planner["planner_notes"], "Không có ghi chú planner.")

    prompt = f"""Bạn là chuyên gia tư vấn tuyển sinh đại học cho học sinh lớp 12.

Mục tiêu: giúp học sinh hiểu nên ưu tiên trường/ngành nào, vì sao phù hợp, mức cạnh tranh ra sao và cần backup thế nào. Chỉ tư vấn dựa trên dữ liệu bên dưới.

## Dữ liệu học sinh
### Bảng điểm
{score_lines}

### Tổng quan năng lực
- Điểm trung bình: {_format_number(strength.get('avg', 0))}
- Xu hướng năng lực: {_safe_text(strength.get('category'), 'Chưa xác định')}
- Môn mạnh nhất: {', '.join(strength.get('strongest', [])) or 'Chưa xác định'}
- Môn yếu nhất: {', '.join(strength.get('weakest', [])) or 'Chưa xác định'}

### Top tổ hợp mạnh nhất
{combo_lines}

### Bối cảnh người dùng đã chọn
{filters_text}

## Dữ liệu trường/ngành
- Số kết quả đang hiển thị theo Top K: {total_displayed}
- Tổng số trường/ngành phù hợp trước khi cắt Top K: {total_found}

### Danh sách phân tích sâu do hệ thống chọn
{focus_lines}

### Danh sách tham khảo/dự phòng còn lại
{reference_lines}

### Thứ tự nguyện vọng đề xuất bởi hệ thống
{priority_lines}

### Ghi chú planner
{planner_notes}

## Cảnh báo và điều kiện phụ
### Cảnh báo
{warning_text}

### Điều kiện/dữ liệu còn thiếu
{missing_text}

## Nhiệm vụ trả lời
Viết tư vấn bằng tiếng Việt, hướng tới học sinh lớp 12. Cấu trúc bắt buộc:

1. **Tóm tắt năng lực**: nêu môn mạnh, tổ hợp lợi thế và điểm cần lưu ý.
2. **Phân tích các lựa chọn chính**: phân tích từng lựa chọn trong "Danh sách phân tích sâu"; giải thích vì sao phù hợp hoặc vì sao rủi ro dựa trên ngành, tổ hợp, điểm chuẩn, Chênh lệch điểm, nhóm cạnh tranh, phương thức xét tuyển và điều kiện phụ.
3. **Thứ tự nguyện vọng nên ưu tiên**: dùng đúng thứ tự hệ thống đề xuất, kèm lý do ngắn cho từng dòng.
4. **Roadmap backup**: nêu nhóm an toàn/vừa sức/thử thách nên dùng thế nào, và nhắc ngắn các lựa chọn tham khảo nếu có.
5. **Lưu ý cần kiểm tra**: nhắc cảnh báo, điều kiện phụ, dữ liệu còn thiếu hoặc quy chế liên quan nếu có.

## Quy tắc bắt buộc
- Không tự chọn lại danh sách phân tích sâu.
- Không tự đảo thứ tự nguyện vọng đề xuất, trừ khi phát hiện mâu thuẫn dữ liệu nghiêm trọng; nếu có mâu thuẫn, phải nói rõ mâu thuẫn.
- Không thêm trường, ngành, học phí, ranking, danh tiếng, chỉ tiêu hoặc số liệu ngoài dữ liệu đã cung cấp.
- Không đưa xác suất đỗ dạng phần trăm. Nếu nói về cơ hội, chỉ dùng mức định tính: cơ hội cao, cạnh tranh vừa, rủi ro có cơ sở, rủi ro cao.
- Luôn gọi khoảng cách điểm là `Chênh lệch điểm`; không dùng thuật ngữ kỹ thuật nội bộ.
- Giữ đúng 3 nhóm cạnh tranh hiện có: an toàn, vừa sức, thử thách.
- Không kết luận chắc chắn đỗ/trượt; chỉ tư vấn chiến lược dựa trên dữ liệu điểm chuẩn.
- Viết ngắn gọn nhưng đủ lý do, ưu tiên tính hành động."""

    return prompt


def generate_analysis_stream(result: dict, chat_history: list = None):
    """
    Gọi LLM phân tích kết quả và trả về generator stream.
    """
    from llm_client import call_llm_stream, OPENROUTER_FALLBACK_MODELS

    prompt = build_analysis_prompt(result)
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Hãy phân tích bảng điểm và danh sách trường phù hợp ở trên cho em."},
    ]

    return call_llm_stream(
        messages=messages,
        model=OPENROUTER_FALLBACK_MODELS[0],
        temperature=0.3,
        max_tokens=3000,
    )
