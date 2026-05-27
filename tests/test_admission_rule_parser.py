# -*- coding: utf-8 -*-

import pytest

from utils.admission_rule_parser import build_annotation, normalize_note, parse_admission_rule, rule_from_json, rule_to_json


def test_normalize_note_expands_common_abbreviations():
    assert "Tiếng Anh" in normalize_note("TA >= 5.00; Toán nhân 2")
    assert "≥ 5.0" in normalize_note("TA >= 5.00; Toán nhân 2")


def test_empty_note_defaults_to_normal_30():
    rule = parse_admission_rule("", {"Điểm chuẩn_Num": 24, "Năm_Num": 2025})
    assert rule.mode == "normal_30"
    assert rule.confidence == "high"


def test_multiplier_without_scale_is_conservative_convert_30():
    rule = parse_admission_rule("Toán nhân 2", {"Điểm chuẩn_Num": 24, "Năm_Num": 2025})
    assert rule.mode == "weighted_convert_30"
    assert rule.confidence == "medium"
    assert rule.multipliers[0].subject == "Toán"
    assert rule.multipliers[0].factor == 2


def test_thang_40_without_multiplier_is_range():
    rule = parse_admission_rule("Thang điểm 40", {"Điểm chuẩn_Num": 32})
    assert rule.mode == "weighted_40_range"
    assert rule.score_scale == 40
    assert rule.confidence == "medium"


def test_certificates_or_conditions_and_annotation():
    rule = parse_admission_rule("IELTS ≥ 5.5 (tương đương), Toán nhân 2", {"Điểm chuẩn_Num": 24})
    assert rule.conditions[0].condition_type == "certificate"
    assert rule.conditions[0].subject == "IELTS"
    assert "IELTS" in build_annotation(rule)


def test_or_condition_is_linked():
    rule = parse_admission_rule("Sinh ≥ 5.00 hoặc ĐTB lớp 12 môn Sinh ≥ 6.0, Sinh nhân 2")
    assert rule.conditions[0].alternative is not None


def test_unsupported_cases():
    assert parse_admission_rule("Thang điểm 35, Môn Anh nhân 1.5").unsupported_reason == "scale_35"
    assert (
        parse_admission_rule("Điểm thi THPT và năng lực TA, Toán hệ số 2, Quy về thang 30").unsupported_reason
        == "english_competency_component"
    )


def test_rule_cache_json_rejects_invalid_mode_and_confidence():
    valid_rule = parse_admission_rule("", {"Điểm chuẩn_Num": 24})
    assert rule_from_json(rule_to_json(valid_rule)) is not None

    invalid_mode = rule_to_json(valid_rule).replace('"mode": "normal_30"', '"mode": "not_a_mode"')
    assert rule_from_json(invalid_mode) is None

    invalid_confidence = rule_to_json(valid_rule).replace('"confidence": "high"', '"confidence": "unknown"')
    assert rule_from_json(invalid_confidence) is None


def test_rule_cache_json_rejects_invalid_nested_shapes():
    payload = '{"mode":"normal_30","confidence":"high","multipliers":{},"conditions":[]}'
    assert rule_from_json(payload) is None


def test_rule_cache_json_accepts_deterministic_unsupported_rules():
    rule = parse_admission_rule("Thang điểm 35, Môn Anh nhân 1.5")
    cached = rule_from_json(rule_to_json(rule))
    assert cached is not None
    assert cached.unsupported_reason == "scale_35"


@pytest.mark.parametrize(
    ("note", "expected_mode", "mult_subject", "condition_subject"),
    [
        ("Toán nhân 2", "weighted_convert_30", "Toán", None),
        ("Toán hệ số 2", "weighted_convert_30", "Toán", None),
        ("Điểm môn Anh nhân hệ số 2", "weighted_convert_30", "Tiếng Anh", None),
        ("Môn Anh nhân 1.5", "weighted_convert_30", "Tiếng Anh", None),
        ("Ngoại ngữ nhân 2", "weighted_convert_30", None, None),
        ("Anh hoặc Trung nhân 2", "weighted_convert_30", None, None),
        ("Tiếng anh hệ số 2, quy về thang 30", "weighted_convert_30", "Tiếng Anh", None),
        ("Thang điểm 40", "weighted_40_range", None, None),
        ("Toán nhân 2, Thang điểm 40", "weighted_40", "Toán", None),
        ("IELTS ≥ 5.5 (tương đương), Toán nhân 2", "weighted_convert_30", "Toán", "IELTS"),
        ("Điểm ĐK tiếng Anh học bạ: 5, Toán nhân 2", "weighted_convert_30", "Toán", "ĐTB Tiếng Anh học bạ"),
        ("Toán ≥ 5.00, Toán nhân 2", "weighted_convert_30", "Toán", "Toán"),
        ("Văn nhân 2", "weighted_convert_30", "Ngữ văn", None),
        ("điểm năng khiếu x2, đạt tối thiểu 5 điểm trở lên", "weighted_convert_30", None, None),
        ("Vẽ HHMT nhân 2", "weighted_convert_30", "Vẽ HHMT", None),
        ("Năng khiếu SKĐA 2 nhân 2, môn Năng khiếu SKĐA 2 đạt từ 7", "weighted_convert_30", None, "Năng khiếu SKĐA 2"),
        ("Sinh ≥ 5.00", "normal_30", None, "Sinh học"),
        ("ĐTB lớp 12 môn Sinh ≥ 6.0", "normal_30", None, "ĐTB Sinh học lớp 12"),
        ("TOEFL ≥ 60", "normal_30", None, "TOEFL"),
        ("TOEIC ≥ 500", "normal_30", None, "TOEIC"),
    ],
)
def test_parser_plan_reference_cases(note, expected_mode, mult_subject, condition_subject):
    rule = parse_admission_rule(note, {"Điểm chuẩn_Num": 24})
    assert rule.mode == expected_mode
    if mult_subject:
        assert any(mult.subject == mult_subject for mult in rule.multipliers)
    if condition_subject:
        subjects = [cond.subject for cond in rule.conditions]
        subjects.extend(cond.alternative.subject for cond in rule.conditions if cond.alternative)
        assert condition_subject in subjects


def test_shared_or_condition_keeps_both_aptitude_branches():
    rule = parse_admission_rule("Vẽ HHMT hoặc Vẽ TTM ≥ 6.00, Vẽ HHMT nhân 2")
    condition = rule.conditions[0]
    assert condition.condition_type == "aptitude_score"
    assert condition.subject == "Vẽ HHMT"
    assert condition.alternative is not None
    assert condition.alternative.subject == "Vẽ TTM"


def test_compound_aptitude_and_literature_conditions_are_preserved():
    rule = parse_admission_rule(
        "Năng khiếu SKĐA 2 nhân 2; môn Năng khiếu SKĐA 1 và Ngữ văn đạt từ 5, "
        "môn Năng khiếu SKĐA 2 đạt từ 7."
    )
    subjects = [condition.subject for condition in rule.conditions]
    assert "Năng khiếu SKĐA 1" in subjects
    assert "Ngữ văn" in subjects
    assert "Năng khiếu SKĐA 2" in subjects


def test_or_multiplier_does_not_create_unknown_duplicate_multiplier():
    rule = parse_admission_rule("Anh ≥ 5.50 hoặc Trung ≥ 5.50, Anh hoặc Trung nhân 2")
    assert len(rule.multipliers) == 1
    assert rule.multipliers[0].candidates == ["Tiếng Anh", "Tiếng Trung"]


def test_external_assessment_notes_are_unsupported():
    rule = parse_admission_rule("Kết hợp điểm thi THPT và điểm ĐGNL BCA")

    assert rule.mode == "unsupported"
    assert rule.confidence == "unsupported"
    assert rule.unsupported_reason == "external_assessment_component"


def test_certificate_component_without_threshold_is_unsupported():
    rule = parse_admission_rule("Xét 2 môn thi TN và CCNNQT")

    assert rule.mode == "unsupported"
    assert rule.unsupported_reason == "certificate_component_without_threshold"


def test_transcript_combo_component_is_unsupported_for_exam_mode():
    rule = parse_admission_rule("Học bạ lớp 12 theo tổ hợp 3 môn")

    assert rule.mode == "unsupported"
    assert rule.unsupported_reason == "transcript_combo_component"


def test_academic_rank_condition_is_parsed_and_annotated():
    rule = parse_admission_rule("HL12 khá")

    assert rule.conditions[0].condition_type == "academic_rank"
    assert rule.conditions[0].value == 2.0
    assert "Học lực lớp 12 >= Khá" in build_annotation(rule)
