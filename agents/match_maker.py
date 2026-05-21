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


def find_top_k_schools(
    student_scores: dict,
    methods: list[str] | None = None,
    k: int = 5,
    bonus: float = 0.0,
    year_priority: list[int] | None = None,
    top_n_combos: int = 5,
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


def build_analysis_prompt(result: dict) -> str:
    """
    Xây dựng System Prompt cho LLM phân tích kết quả matching.
    """
    scores = result.get("scores", {})
    strength = result.get("strength", {})
    top_combos = result.get("top_combinations", [])
    df = result.get("matched_schools", pd.DataFrame())

    # Format điểm số
    score_lines = "\n".join(f"  - {subj}: {score}" for subj, score in scores.items())

    # Format tổ hợp
    combo_lines = "\n".join(
        f"  {i+1}. {format_combination_display(c)}"
        for i, c in enumerate(top_combos[:5])
    )

    # Format bảng trường
    if not df.empty:
        school_lines = df.to_string(index=False)
    else:
        school_lines = "(Không có dữ liệu)"

    # Format warnings
    warnings = result.get("warnings", [])
    warning_text = "\n".join(warnings) if warnings else "Không có cảnh báo."

    prompt = f"""Bạn là CHUYÊN GIA TƯ VẤN TUYỂN SINH ĐẠI HỌC SENIOR với 15+ năm kinh nghiệm.

## DỮ LIỆU HỌC SINH
### Bảng điểm:
{score_lines}

### Điểm trung bình: {strength.get('avg', 0)}
### Xu hướng năng lực: {strength.get('category', 'Chưa xác định')}
### Môn mạnh nhất: {', '.join(strength.get('strongest', []))}
### Môn yếu nhất: {', '.join(strength.get('weakest', []))}

### Top tổ hợp khối thi mạnh nhất:
{combo_lines}

## BẢNG TOP TRƯỜNG PHÙ HỢP (từ dữ liệu điểm chuẩn thực tế):
{school_lines}

## CẢNH BÁO:
{warning_text}

## NHIỆM VỤ CỦA BẠN:
Hãy phân tích và tư vấn CHI TIẾT cho học sinh theo cấu trúc sau:

1. **📊 Phân tích Học lực**: Đánh giá thế mạnh/điểm yếu dựa trên bảng điểm. Em mạnh nhóm môn nào?
2. **🏆 Giải thích Top Trường**: Với MỖI trường trong bảng, giải thích TẠI SAO nó phù hợp. So sánh Delta (khoảng cách điểm), mức độ an toàn.
3. **💡 Chiến lược Xét tuyển**: Gợi ý cách phân bổ nguyện vọng thông minh (trường an toàn + trường vừa sức + trường thử thách).
4. **⚠️ Lưu ý**: Nhắc về quy chế 2026 nếu có điều quan trọng.

QUY TẮC:
- KHÔNG được bịa thêm tên trường hay con số ngoài bảng dữ liệu.
- Dùng emoji vừa phải, ngôn ngữ thân thiện, dễ hiểu.
- Viết bằng tiếng Việt."""

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
        max_tokens=2000,
    )
