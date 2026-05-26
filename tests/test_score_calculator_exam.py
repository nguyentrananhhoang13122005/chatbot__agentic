# -*- coding: utf-8 -*-

import pytest

from utils.admission_models import AdmissionRule, Multiplier
from utils.score_calculator import calc_exam_score


def test_normal_30_score():
    rule = AdmissionRule(30, False, "normal_30")
    result = calc_exam_score({"Toán": 8, "Vật lý": 7, "Tiếng Anh": 9}, "A01", rule, 0)
    assert result.final_score == 24


def test_weighted_convert_30_score():
    rule = AdmissionRule(30, True, "weighted_convert_30", [Multiplier("exact", "Toán", [], 2)])
    result = calc_exam_score({"Toán": 8, "Vật lý": 7, "Tiếng Anh": 9}, "A01", rule, 0)
    assert result.final_score == pytest.approx(24.0)


def test_weighted_40_score():
    rule = AdmissionRule(40, False, "weighted_40", [Multiplier("exact", "Toán", [], 2)])
    result = calc_exam_score({"Toán": 8, "Vật lý": 7, "Tiếng Anh": 9}, "A01", rule, 0)
    assert result.final_score == 32


def test_weighted_40_range_uses_lower_bound_for_ranking():
    rule = AdmissionRule(40, False, "weighted_40_range")
    result = calc_exam_score({"Toán": 8, "Vật lý": 7, "Tiếng Anh": 9}, "A01", rule, 0)
    assert result.score_min == 31
    assert result.score_max == 33
    assert result.ranking_score == 31


def test_none_score_requires_validated_subjects():
    rule = AdmissionRule(30, False, "normal_30")
    with pytest.raises(ValueError, match="subjects must be validated"):
        calc_exam_score({"Toán": 8, "Vật lý": None, "Tiếng Anh": 9}, "A01", rule, 0)


def test_aptitude_score_can_be_calculated_when_merged_by_caller():
    rule = AdmissionRule(30, False, "normal_30")
    result = calc_exam_score({"Toán": 8, "Ngữ văn": 7, "Vẽ": 9}, "H01", rule, 0)
    assert result.final_score == 24


def test_normal_30_priority_reduction_applies_after_threshold():
    rule = AdmissionRule(30, False, "normal_30")
    result = calc_exam_score({"Toán": 9, "Vật lý": 8, "Tiếng Anh": 8}, "A01", rule, 1.5)
    assert result.raw_score == 25
    assert result.priority_adjusted == 1.0
    assert result.final_score == 26.0


def test_weighted_convert_30_priority_uses_converted_score():
    rule = AdmissionRule(30, True, "weighted_convert_30", [Multiplier("exact", "Tiếng Anh", [], 1.5)])
    result = calc_exam_score({"Toán": 8, "Ngữ văn": 7, "Tiếng Anh": 9}, "D01", rule, 1.5)
    assert result.raw_score == pytest.approx(24.43)
    assert result.priority_adjusted == pytest.approx(1.11)


def test_weighted_40_priority_scales_to_40():
    rule = AdmissionRule(40, False, "weighted_40", [Multiplier("exact", "Toán", [], 2)])
    result = calc_exam_score({"Toán": 8, "Vật lý": 7, "Tiếng Anh": 9}, "A01", rule, 1.5)
    assert result.raw_score == 32
    assert result.priority_adjusted == 1.6
    assert result.final_score == 33.6


def test_weighted_40_range_upper_bound_does_not_change_ranking():
    rule = AdmissionRule(40, False, "weighted_40_range")
    result = calc_exam_score({"Toán": 8, "Vật lý": 7, "Tiếng Anh": 9}, "A01", rule, 1.5)
    assert result.score_max > result.score_min
    assert result.ranking_score == result.score_min
