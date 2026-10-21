# -*- coding: utf-8 -*-
"""Test phân loại dự phòng của router (không gọi LLM)."""
import pytest

from router import _heuristic_classify


@pytest.mark.parametrize("query,intent", [
    ("Học phí Đại học FPT năm 2025", "RECOMMENDER"),
    ("Điểm chuẩn PTIT 2025 ngành CNTT", "RECOMMENDER"),
    ("Chỉ tiêu ĐH Tôn Đức Thắng 2024", "RECOMMENDER"),
    ("So sánh chất lượng đào tạo Bách khoa và Ngoại thương", "GENERAL"),
    ("Tư vấn hướng nghiệp theo tính cách của mình", "COUNSELOR"),
])
def test_heuristic_intent(query, intent):
    assert _heuristic_classify(query)["intent"] == intent


def test_heuristic_extracts_year_and_abbreviation():
    result = _heuristic_classify("Điểm chuẩn PTIT 2024")
    assert result["year"] == 2024 and result["school"] == "PTIT"


def test_heuristic_unknown_school_stays_all():
    assert _heuristic_classify("Cho mình hỏi điểm chuẩn các ngành")["school"] == "ALL"
