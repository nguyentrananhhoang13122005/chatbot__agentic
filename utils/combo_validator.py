# -*- coding: utf-8 -*-
"""Validate subject availability before calculating an exam combo."""

from __future__ import annotations

from utils.admission_models import AdmissionRule, ComboValidationResult, StudentProfile
from utils.score_calculator import COMBINATIONS


def validate_combo_inputs(
    combo_code: str,
    profile: StudentProfile,
    rule: AdmissionRule | None = None,
) -> ComboValidationResult:
    """Validate missing/not-taken subjects for a combo and its hard conditions."""
    subjects = COMBINATIONS.get(combo_code)
    if not subjects:
        return ComboValidationResult(False, reason=f"Không hỗ trợ tổ hợp {combo_code}")

    missing: list[str] = []
    not_taken: list[str] = []
    for subject in dict.fromkeys(subjects):
        if subject in profile.not_taken_subjects:
            not_taken.append(subject)
        elif not _has_subject_score(profile, subject):
            missing.append(subject)

    if rule:
        for condition in rule.conditions:
            _collect_condition_subject(condition, profile, missing, not_taken)

    if not_taken:
        return ComboValidationResult(False, missing, not_taken, "Có môn học sinh xác nhận không thi")
    if missing:
        return ComboValidationResult(False, missing, not_taken, "Thiếu điểm môn trong tổ hợp")
    return ComboValidationResult(True, [], [], None)


def _collect_condition_subject(condition, profile: StudentProfile, missing: list[str], not_taken: list[str]) -> None:
    if condition.alternative and (
        _condition_branch_has_input(condition, profile) or _condition_branch_has_input(condition.alternative, profile)
    ):
        return
    if condition.condition_type not in {"subject_score", "aptitude_score"}:
        return
    subject = condition.subject
    if not subject:
        if condition.condition_type == "aptitude_score" and not profile.aptitude_scores and "Điểm năng khiếu" not in missing:
            missing.append("Điểm năng khiếu")
        return
    if subject in profile.not_taken_subjects and subject not in not_taken:
        not_taken.append(subject)
    elif not _has_subject_score(profile, subject) and subject not in missing:
        missing.append(subject)
    if condition.alternative:
        _collect_condition_subject(condition.alternative, profile, missing, not_taken)


def _has_subject_score(profile: StudentProfile, subject: str) -> bool:
    return subject in profile.exam_scores or subject in profile.aptitude_scores


def _condition_branch_has_input(condition, profile: StudentProfile) -> bool:
    if condition.condition_type == "subject_score" and condition.subject:
        return _has_subject_score(profile, condition.subject)
    if condition.condition_type == "aptitude_score":
        return bool(profile.aptitude_scores) if not condition.subject else _has_subject_score(profile, condition.subject)
    if condition.condition_type == "certificate":
        key = str(condition.subject or "").upper()
        return (
            (key == "IELTS" and profile.ielts is not None)
            or (key == "TOEFL" and profile.toefl is not None)
            or (key == "TOEIC" and profile.toeic is not None)
        )
    if condition.condition_type == "school_record":
        if not condition.subject or condition.subject == "ĐTB lớp 12":
            return profile.gpa_12 is not None
        for subject in profile.gpa_subject_12:
            if subject in condition.subject:
                return True
        return False
    return False
