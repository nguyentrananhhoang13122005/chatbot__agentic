# -*- coding: utf-8 -*-

from utils.admission_models import AdmissionRule, Condition, StudentProfile
from utils.combo_validator import validate_combo_inputs


def test_valid_combo_inputs():
    profile = StudentProfile(exam_scores={"Toán": 8, "Vật lý": 7, "Hóa học": 9})
    assert validate_combo_inputs("A00", profile).valid


def test_missing_subject_is_reported():
    profile = StudentProfile(exam_scores={"Toán": 8, "Vật lý": 7})
    result = validate_combo_inputs("A00", profile)
    assert not result.valid
    assert result.missing_inputs == ["Hóa học"]


def test_not_taken_subject_blocks_without_popup():
    profile = StudentProfile(exam_scores={"Toán": 8, "Vật lý": 7}, not_taken_subjects={"Hóa học"})
    result = validate_combo_inputs("A00", profile)
    assert not result.valid
    assert result.not_taken_subjects == ["Hóa học"]


def test_rule_condition_subject_is_validated():
    profile = StudentProfile(exam_scores={"Toán": 8, "Vật lý": 7, "Hóa học": 9})
    rule = AdmissionRule(30, False, "normal_30", conditions=[Condition("subject_score", "Tiếng Anh", ">=", 5, "exam")])
    result = validate_combo_inputs("A00", profile, rule)
    assert not result.valid
    assert result.missing_inputs == ["Tiếng Anh"]


def test_aptitude_subject_can_come_from_aptitude_scores():
    profile = StudentProfile(
        exam_scores={"Toán": 8, "Ngữ văn": 7},
        aptitude_scores={"Vẽ": 9},
    )
    assert validate_combo_inputs("H01", profile).valid


def test_aptitude_condition_checks_aptitude_scores():
    profile = StudentProfile(
        exam_scores={"Toán": 8, "Ngữ văn": 7, "Vật lý": 7},
        aptitude_scores={"Vẽ": 9},
    )
    rule = AdmissionRule(30, False, "normal_30", conditions=[Condition("aptitude_score", "Vẽ", ">=", 6, "aptitude")])
    assert validate_combo_inputs("V00", profile, rule).valid


def test_or_condition_with_available_school_record_does_not_block_combo_validation():
    condition = Condition(
        "subject_score",
        "Sinh học",
        ">=",
        5,
        "exam",
        alternative=Condition("school_record", "ĐTB Sinh học lớp 12", ">=", 6, "transcript"),
    )
    profile = StudentProfile(
        exam_scores={"Toán": 8, "Vật lý": 7, "Hóa học": 7},
        gpa_subject_12={"Sinh học": 7},
    )
    result = validate_combo_inputs("A00", profile, AdmissionRule(30, False, "normal_30", conditions=[condition]))
    assert result.valid
    assert "Sinh học" not in result.missing_inputs
