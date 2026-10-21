# -*- coding: utf-8 -*-
"""Tests cho utils/data_quality.py: mỗi trường một thang điểm/phương thức khác nhau, tên trường nhiều biến thể."""
import pandas as pd
import pytest

from utils.data_quality import (
    classify_method,
    clean_verified,
    infer_scale,
    parse_score,
    recover_decimal,
    school_key,
    score_scale,
)


def _row(school="Đại học A", major="Công nghệ thông tin", method="Xét điểm thi THPT", score=25.5,
         code="7480201", combo="A00", note="", sheet=""):
    return {
        "Trường": school, "Mã ngành": code, "Tên ngành": major, "Phương thức xét tuyển": method,
        "Điểm chuẩn": score, "Tổ hợp môn": combo, "Ghi chú": note, "Sheet gốc": sheet, "Năm": 2025,
    }


@pytest.mark.parametrize("method,sheet,expected", [
    ("Xét điểm thi THPT", "", "thpt"),
    ("Xét học bạ", "", "hoc_ba"),
    ("Xét điểm ĐGNL ĐHQG Hà Nội", "", "dgnl_hn"),
    ("Xét điểm ĐGNL ĐHQG TPHCM", "", "dgnl_hcm"),
    ("Xét điểm ĐGNL ĐHSP Hà Nội", "", "dgnl_sphn"),
    ("Xét điểm đánh giá tư duy", "", "tu_duy"),
    ("Xét chứng chỉ quốc tế", "", "chung_chi"),
    ("", "Sheet1", "khac"),
])
def test_classify_method(method, sheet, expected):
    assert classify_method(method, sheet) == expected


def test_recover_decimal_only_when_unambiguous():
    assert recover_decimal(250267.0, "thpt") == (25.03, "ok")
    assert recover_decimal(25864.0, "thpt") == (25.86, "ok")
    # Số nhỏ (101 trong học bạ) KHÔNG được đoán
    assert recover_decimal(101.0, "hoc_ba")[0] is None


def test_infer_scale_for_converted_scores():
    assert infer_scale("dgnl_hn", 24.5) == "30"      # sheet ĐGNL chứa điểm đã quy đổi thang 30
    assert infer_scale("hoc_ba", 8.2) == "10"
    assert infer_scale("thpt", 85.0) == "100"
    assert infer_scale("thpt", 25.0) is None


def test_score_scale_never_mixes():
    assert score_scale("dgnl_hn", 110) == "150"
    assert score_scale("dgnl_hcm", 900) == "1200"
    assert score_scale("thpt", 27) == "30"
    assert score_scale("chung_chi", 7) == "mixed"


def test_parse_score_vietnamese_decimal_comma():
    assert parse_score("25,5") == 25.5
    assert parse_score("n/a") is None
    assert parse_score(None) is None


def test_school_key_merges_spelling_but_keeps_campus():
    assert school_key("Đại học Hải Phòng") == school_key("Đại Học Hải Phòng")
    assert school_key("ĐH Kinh tế TP.HCM") == school_key("Đại học Kinh tế TP Hồ Chí Minh")
    assert school_key("Học viện Công nghệ BCVT (Miền Bắc)") != school_key("Học viện Công nghệ BCVT (Miền Nam)")


def test_clean_verified_drops_exact_duplicates_and_quarantines_conflicts():
    df = pd.DataFrame([
        _row(),
        _row(),                                  # trùng hệt -> bỏ bản sao
        _row(major="Khoa học máy tính", score=26.0),
        _row(major="Khoa học máy tính", score=27.0),  # cùng khoá, khác điểm -> mâu thuẫn
    ])
    clean, quarantine, report = clean_verified(df)
    assert report["duplicates_dropped"] == 1
    assert (quarantine["quarantine_reason"] == "CONFLICT_DUPLICATE_KEY").sum() == 2
    assert len(clean) == 1


def test_clean_verified_keeps_different_combos_of_same_major():
    """Bug cũ: drop_duplicates bỏ khoá Tổ hợp môn nên mất các dòng hợp lệ."""
    df = pd.DataFrame([_row(combo="A00", score=25), _row(combo="D01", score=24)])
    clean, quarantine, _ = clean_verified(df)
    assert len(clean) == 2 and quarantine.empty


def test_clean_verified_flags_recovered_and_scale():
    df = pd.DataFrame([
        _row(score=250267, major="Ngành 1", code="1"),
        _row(method="Xét điểm ĐGNL ĐHQG Hà Nội", score=110, major="Ngành 2", code="2"),
        _row(method="Xét điểm ĐGNL ĐHQG Hà Nội", score=24.5, major="Ngành 3", code="3"),
        _row(score=0, major="Ngành 4", code="4"),
    ])
    clean, quarantine, _ = clean_verified(df)
    by_major = clean.set_index("Tên ngành")
    assert by_major.loc["Ngành 1", "quality_flag"] == "RECOVERED_DECIMAL"
    assert by_major.loc["Ngành 2", "score_scale"] == "150"
    assert by_major.loc["Ngành 3", "score_scale"] == "30"
    assert by_major.loc["Ngành 3", "quality_flag"] == "SCALE_INFERRED"
    assert list(quarantine["Tên ngành"]) == ["Ngành 4"]
