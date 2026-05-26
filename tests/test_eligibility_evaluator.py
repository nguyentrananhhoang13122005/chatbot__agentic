# -*- coding: utf-8 -*-

from utils.admission_models import AdmissionRule, Condition, StudentProfile
from utils.eligibility_evaluator import evaluate_eligibility


def _rule(condition):
    return AdmissionRule(30, False, "normal_30", conditions=[condition])


def test_subject_condition_pass_fail_unknown():
    condition = Condition("subject_score", "Toán", ">=", 5.0, "exam")
    assert evaluate_eligibility(_rule(condition), StudentProfile(exam_scores={"Toán": 7})).status == "eligible"
    assert evaluate_eligibility(_rule(condition), StudentProfile(exam_scores={"Toán": 4.5})).status == "failed"
    result = evaluate_eligibility(_rule(condition), StudentProfile(exam_scores={}))
    assert result.status == "unknown"
    assert "Toán" in result.missing_inputs


def test_or_condition_passes_second_branch():
    condition = Condition(
        "subject_score",
        "Sinh học",
        ">=",
        5.0,
        "exam",
        alternative=Condition("school_record", "ĐTB Sinh học lớp 12", ">=", 6.0, "transcript"),
    )
    profile = StudentProfile(exam_scores={"Sinh học": 4.0}, gpa_subject_12={"Sinh học": 7.0})
    assert evaluate_eligibility(_rule(condition), profile).status == "eligible"


def test_certificate_missing_is_unknown():
    condition = Condition("certificate", "IELTS", ">=", 5.5, "certificate")
    result = evaluate_eligibility(_rule(condition), StudentProfile())
    assert result.status == "unknown"
    assert "IELTS" in result.missing_inputs[0]
