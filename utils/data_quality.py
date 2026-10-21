# -*- coding: utf-8 -*-
"""
Quality gate cho dữ liệu điểm chuẩn (diem_chuan_verified).

Vì sao cần: mỗi trường dùng phương thức và THANG ĐIỂM khác nhau (thi THPT thang 30/40,
học bạ, ĐGNL HN thang 150, ĐGNL HCM thang 1200, Tư duy thang 100, chứng chỉ quốc tế ...),
một trường lại có thể xuất hiện dưới nhiều tên, và file nguồn có điểm bị mất dấu thập phân
(250267 thay vì 25.0267). Nếu không chuẩn hoá thì "Top điểm cao nhất" trộn các thang với nhau.

Chính sách (theo data contract, docs/data_contract.md):
  CLEAN       sửa được, có quy tắc rõ ràng  -> vào bảng chính
  RECOVERED   khôi phục dấu thập phân khi CHỈ CÓ ĐÚNG MỘT cách chia hợp lệ -> vào bảng chính, gắn cờ
  QUARANTINE  không cứu được / mâu thuẫn / mơ hồ -> bảng quarantine, bot KHÔNG đọc
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

import pandas as pd

from utils.method_normalizer import normalize_method

# ---------------------------------------------------------------- văn bản / tên trường

def nfc(text) -> str:
    """Chuẩn hoá Unicode NFC (bắt buộc với tiếng Việt để hai chuỗi giống hệt nhìn mắt thì cũng khớp)."""
    if text is None:
        return ""
    if isinstance(text, float) and pd.isna(text):
        return ""
    return unicodedata.normalize("NFC", str(text)).strip()


def _strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    plain = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return plain.replace("đ", "d").replace("Đ", "D")


def school_key(name) -> str:
    """Khoá so khớp tên trường: gộp các biến thể chỉ khác cách viết (hoa/thường, dấu câu, ĐH/Đại học, TP.HCM...)
    nhưng GIỮ phần phân biệt cơ sở (CS2, Miền Bắc/Nam, Phân hiệu, tỉnh...)."""
    text = _strip_accents(nfc(name)).lower()
    text = re.sub(r"^\d+[\.\-\s]+", "", text)
    text = re.sub(r"[\(\)\[\]\.,_\-–/:]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^truong\s+", "", text)
    text = re.sub(r"\bdh\b", "dai hoc", text)
    text = re.sub(r"\bhv\b", "hoc vien", text)
    text = re.sub(r"\b(tp ho chi minh|ho chi minh|tp hcm|hcm|tphcm)\b", "tphcm", text)
    text = re.sub(r"\bhn\b", "ha noi", text)
    text = re.sub(r"\bcs\s*(\d)\b", r"co so \1", text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------- phương thức & thang điểm

# (cận trên cứng, cận dưới "hợp lý" dùng khi khôi phục dấu thập phân)
SCORE_RANGES = {
    "thpt": (40.0, 10.0),        # thang 30; tới 40 cho ngành năng khiếu nhân hệ số
    "hoc_ba": (40.0, 10.0),
    "dgnl_sphn": (40.0, 10.0),   # ĐGNL của ĐH Sư phạm HN đã quy về thang 30
    "ket_hop": (100.0, 10.0),
    "thi_rieng": (100.0, 10.0),
    "xt_thang": (100.0, 10.0),
    "xt_som": (100.0, 10.0),
    "dgnl_hn": (150.0, 30.0),    # ĐGNL ĐHQG Hà Nội thang 150
    "dgnl_hcm": (1200.0, 200.0),  # ĐGNL ĐHQG TPHCM thang 1200
    "tu_duy": (100.0, 20.0),     # Đánh giá tư duy ĐH Bách khoa HN thang 100
    "chung_chi": (1600.0, 10.0),  # IELTS/SAT/quy đổi: thang không đồng nhất
}

METHOD_GROUP_LABELS = {
    "thpt": "Điểm thi tốt nghiệp THPT",
    "hoc_ba": "Xét học bạ THPT",
    "dgnl_hn": "ĐGNL ĐHQG Hà Nội (thang 150)",
    "dgnl_hcm": "ĐGNL ĐHQG TPHCM (thang 1200)",
    "dgnl_sphn": "ĐGNL ĐH Sư phạm Hà Nội",
    "tu_duy": "Đánh giá tư duy (thang 100)",
    "chung_chi": "Chứng chỉ quốc tế",
    "ket_hop": "Xét tuyển kết hợp",
    "thi_rieng": "Điểm thi riêng của trường",
    "xt_thang": "Ưu tiên xét tuyển / xét tuyển thẳng",
    "xt_som": "Xét tuyển sớm",
    "khac": "Chưa xác định",
}


def classify_method(method_raw, sheet_title: str = "") -> str:
    """Gom ~28 cách viết phương thức xét tuyển về nhóm chuẩn (method_group)."""
    k = normalize_method(f"{method_raw or ''} {sheet_title or ''}")
    if "dgnl" in k or "danh gia nang luc" in k:
        if re.search(r"\b(hcm|tphcm|sai gon)\b", k):
            return "dgnl_hcm"
        if re.search(r"\b(dhsp|sp|su pham)\b", k):
            return "dgnl_sphn"
        return "dgnl_hn"
    if "tu duy" in k or "dgtd" in k:
        return "tu_duy"
    if "hoc ba" in k or re.search(r"\bhb\b", k):
        return "hoc_ba"
    if "thi rieng" in k:
        return "thi_rieng"
    if "chung chi" in k or "quoc te" in k or "ielts" in k or re.search(r"\bsat\b", k):
        return "chung_chi"
    if "ket hop" in k:
        return "ket_hop"
    if re.search(r"\b(utxt|uxt|xt thang|xet tuyen thang|uu tien)\b", k):
        return "xt_thang"
    if "xet tuyen som" in k or re.search(r"\bsom\b", k):
        return "xt_som"
    if "thpt" in k or "diem thi" in k:
        return "thpt"
    return "khac"


def score_scale(group: str, value: float) -> str:
    """Thang điểm thực tế của một dòng (để không bao giờ so sánh chéo thang)."""
    if group == "dgnl_hn":
        return "150"
    if group == "dgnl_hcm":
        return "1200"
    if group == "tu_duy":
        return "100"
    if group in {"thpt", "hoc_ba", "dgnl_sphn"}:
        return "30" if value <= 30 else "40"
    if group == "chung_chi":
        return "mixed"
    return "30" if value <= 30 else ("40" if value <= 40 else "100")


def infer_scale(group: str, value: float):
    """Suy ra thang khi giá trị nằm NGOÀI thang tự nhiên của nhóm nhưng có dạng quen thuộc.
    Ví dụ sheet "ĐGNL HN" của nhiều trường chứa điểm đã quy đổi về thang 30. Trả về nhãn thang hoặc None."""
    if group in {"dgnl_hn", "dgnl_hcm", "tu_duy"} and 10 <= value <= 30:
        return "30"
    if group == "hoc_ba" and 4 <= value <= 10:
        return "10"
    if group == "thpt" and 40 < value <= 100:
        return "100"
    return None


def parse_score(value):
    """Đọc điểm từ ô gốc. Trả về float hoặc None. Hỗ trợ dấu phẩy thập phân kiểu Việt Nam ("25,5")."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return None if pd.isna(value) else float(value)
    text = str(value).strip().replace(" ", "")
    if not text or text.lower() in {"nan", "none", "-", "n/a"}:
        return None
    if re.fullmatch(r"\d+,\d{1,4}", text):
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def recover_decimal(value: float, group: str):
    """Khôi phục điểm bị mất dấu thập phân (250267 -> 25.0267).

    Chỉ khôi phục khi là số nguyên VÀ có DUY NHẤT một luỹ thừa 10 đưa giá trị về khoảng hợp lệ của nhóm.
    Trả về (giá trị, 'ok') | (None, 'ambiguous') | (None, 'impossible')."""
    hi, lo = SCORE_RANGES.get(group, (None, None))
    # Mất dấu thập phân chỉ sinh ra số nguyên rất lớn (>= 5 chữ số). Giá trị như 101 trong học bạ là
    # dữ liệu khác thang/sai nghiệp vụ, KHÔNG được đoán.
    if hi is None or not float(value).is_integer() or value < 10000:
        return None, "impossible"
    candidates = [value / (10 ** k) for k in range(1, 6) if lo <= value / (10 ** k) <= hi]
    if len(candidates) == 1:
        return round(candidates[0], 2), "ok"
    return None, "ambiguous" if candidates else "impossible"


# ---------------------------------------------------------------- quality gate chính

TEXT_COLUMNS = ["Trường", "Mã ngành", "Tên ngành", "Phương thức xét tuyển", "Tổ hợp môn", "Ghi chú"]
NEW_COLUMNS = ["school_id", "method_group", "score_scale", "quality_flag", "Điểm chuẩn_raw"]


def _normalize_combo(value) -> str:
    text = nfc(value).upper()
    if not text:
        return ""
    parts = [p.strip() for p in re.split(r"[;,/|]+", text) if p.strip()]
    return ", ".join(sorted(dict.fromkeys(parts)))


def clean_verified(df: pd.DataFrame, sheet_column: str = "Sheet gốc"):
    """Áp quality gate. Trả về (clean_df, quarantine_df, report_dict)."""
    work = df.copy()
    work.columns = [nfc(c) for c in work.columns]
    for col in TEXT_COLUMNS:
        if col not in work.columns:
            work[col] = ""
        work[col] = work[col].map(nfc)
    if "Năm" not in work.columns:
        work["Năm"] = 2025
    sheet = work[sheet_column].map(nfc) if sheet_column in work.columns else pd.Series("", index=work.index)

    work["Điểm chuẩn_raw"] = work["Điểm chuẩn"] if "Điểm chuẩn" in work.columns else None
    work["_value"] = work["Điểm chuẩn_raw"].map(parse_score)
    work["method_group"] = [classify_method(m, s) for m, s in zip(work["Phương thức xét tuyển"], sheet)]

    # --- thống nhất tên trường: nhiều cách viết -> một school_id, một tên hiển thị (tên phổ biến nhất) ---
    work["school_id"] = work["Trường"].map(school_key)
    display = (
        work.groupby("school_id")["Trường"]
        .agg(lambda s: Counter(s).most_common(1)[0][0])
        .to_dict()
    )
    renamed = int((work["Trường"] != work["school_id"].map(display)).sum())
    work["Trường"] = work["school_id"].map(display)

    reasons, flags, finals, scales = [], [], [], []
    for value, group in zip(work["_value"], work["method_group"]):
        reason, flag, final, override = "", "", value, None
        hi = SCORE_RANGES.get(group, (None, None))[0]
        if group == "khac":
            reason = "UNKNOWN_METHOD"
        elif value is None or value <= 0:
            reason = "MISSING_SCORE"
        elif value < SCORE_RANGES[group][1]:
            override = infer_scale(group, value)
            if override:
                flag = "SCALE_INFERRED"
            else:
                reason = "OUT_OF_RANGE"
        elif value > hi:
            recovered, status = recover_decimal(value, group)
            if status == "ok":
                final, flag = recovered, "RECOVERED_DECIMAL"
            else:
                override = infer_scale(group, value)
                if override:
                    flag = "SCALE_INFERRED"
                else:
                    reason = "AMBIGUOUS_DECIMAL" if status == "ambiguous" else "OUT_OF_RANGE"
        if not reason and group == "chung_chi":
            flag = flag or "SCALE_MIXED"
        reasons.append(reason)
        flags.append(flag)
        finals.append(final)
        scales.append("" if reason else (override or score_scale(group, final)))
    work["_final"] = finals
    work["quality_flag"] = flags
    work["score_scale"] = scales
    work["_reason"] = reasons

    work.loc[work["Tên ngành"] == "", "_reason"] = work["_reason"].where(work["_reason"] != "", "EMPTY_MAJOR")

    # --- trùng khoá: giống hệt -> bỏ bản sao; cùng khoá khác điểm -> mâu thuẫn, quarantine ---
    work["_combo"] = work["Tổ hợp môn"].map(_normalize_combo)
    key_cols = ["school_id", "Mã ngành", "_major_key", "method_group", "_combo", "Ghi chú"]
    work["_major_key"] = work["Tên ngành"].map(lambda v: _strip_accents(nfc(v)).lower())
    ok_mask = (work["_reason"] == "") & (work["method_group"] != "chung_chi")
    ok = work[ok_mask]
    nunique = ok.groupby(key_cols)["_final"].transform("nunique")
    conflict_idx = ok.index[nunique > 1]
    work.loc[conflict_idx, "_reason"] = "CONFLICT_DUPLICATE_KEY"
    ok = work[work["_reason"] == ""]
    dup_mask = ok.duplicated(subset=key_cols + ["_final"], keep="first")
    duplicates_dropped = int(dup_mask.sum())
    clean = ok[~dup_mask].copy()

    clean["Điểm chuẩn"] = clean["_final"]
    clean["Tổ hợp môn"] = clean["_combo"]
    drop_cols = [c for c in clean.columns if c.startswith("_")]
    clean = clean.drop(columns=drop_cols).reset_index(drop=True)

    quarantine = work[work["_reason"] != ""].copy()
    quarantine["quarantine_reason"] = quarantine["_reason"]
    quarantine = quarantine.drop(columns=[c for c in quarantine.columns if c.startswith("_")]).reset_index(drop=True)

    report = {
        "rows_in": int(len(df)),
        "rows_clean": int(len(clean)),
        "rows_quarantined": int(len(quarantine)),
        "rows_recovered_decimal": int((clean["quality_flag"] == "RECOVERED_DECIMAL").sum()),
        "duplicates_dropped": duplicates_dropped,
        "school_name_variants_merged": renamed,
        "schools": int(clean["school_id"].nunique()),
        "quarantine_by_reason": dict(Counter(quarantine["quarantine_reason"])),
        "rows_by_method_group": dict(Counter(clean["method_group"])),
        "rows_by_scale": dict(Counter(clean["score_scale"])),
    }
    return clean, quarantine, report
