# -*- coding: utf-8 -*-
"""Evaluate parsed admission conditions against a student profile."""

from __future__ import annotations

import re

from utils.admission_models import AdmissionRule, Condition, EligibilityResult, StudentProfile


ACADEMIC_RANK_VALUES = {
    "trung bình": 1.0,
    "khá": 2.0,
    "giỏi": 3.0,
    "tốt": 3.0,
}
ACADEMIC_RANK_LABELS = {
    1.0: "Trung bình",
    2.0: "Khá",
    3.0: "Giỏi",
}


def evaluate_eligibility(rule: AdmissionRule, profile: StudentProfile) -> EligibilityResult:
    """Evaluate all hard conditions in a parsed admission rule."""
    if rule.unsupported_reason:
        return EligibilityResult("unsupported", failed_conditions=[rule.unsupported_reason])
    if rule.unresolved_reason:
        return EligibilityResult("unsupported", failed_conditions=[rule.unresolved_reason])

    failed: list[str] = []
    unknown: list[str] = []
    missing: list[str] = []

    for condition in rule.conditions:
        status, message, needed = _evaluate_with_alternative(condition, profile)
        if status == "failed":
            failed.append(message)
        elif status == "unknown":
            unknown.append(message)
            missing.extend(item for item in needed if item not in missing)

    if failed:
        return EligibilityResult("failed", failed, unknown, missing)
    if unknown:
        return EligibilityResult("unknown", failed, unknown, missing)
    return EligibilityResult("eligible", [], [], [])


def _evaluate_with_alternative(condition: Condition, profile: StudentProfile) -> tuple[str, str, list[str]]:
    first = _evaluate_condition(condition, profile)
    if condition.alternative is None:
        return first

    second = _evaluate_condition(condition.alternative, profile)
    if first[0] == "passed" or second[0] == "passed":
        return "passed", "", []
    if first[0] == "unknown" or second[0] == "unknown":
        messages = [item[1] for item in (first, second) if item[0] == "unknown"]
        missing = first[2] + [item for item in second[2] if item not in first[2]]
        return "unknown", " hoặc ".join(messages), missing
    return "failed", f"{first[1]} hoặc {second[1]}", []


def _evaluate_condition(condition: Condition, profile: StudentProfile) -> tuple[str, str, list[str]]:
    if not condition.evaluatable:
        label = _condition_label(condition)
        return "unknown", f"{label}: chưa có dữ liệu để đánh giá", [label]

    value = _profile_value(condition, profile)
    label = _condition_label(condition)
    if value is None:
        needed = _missing_label(condition)
        return "unknown", f"{label}: chưa nhập", [needed]

    passed = value >= condition.value if condition.operator == ">=" else value > condition.value
    if passed:
        return "passed", "", []
    return "failed", f"{label}: bạn có {value:g}", []


def _profile_value(condition: Condition, profile: StudentProfile) -> float | None:
    subject = condition.subject or ""
    if condition.condition_type == "subject_score":
        return profile.exam_scores.get(subject)
    if condition.condition_type == "certificate":
        key = subject.upper()
        if key == "IELTS":
            return profile.ielts
        if key == "TOEFL":
            return profile.toefl
        if key == "TOEIC":
            return profile.toeic
        return None
    if condition.condition_type == "school_record":
        if subject in {"", "ĐTB lớp 12"}:
            return profile.gpa_12
        parsed = _extract_subject_from_school_record(subject)
        if parsed:
            return profile.gpa_subject_12.get(parsed)
        return profile.gpa_12
    if condition.condition_type == "academic_rank":
        return _academic_rank_value(profile.academic_rank_12)
    if condition.condition_type == "aptitude_score":
        if subject:
            return profile.aptitude_scores.get(subject) or profile.exam_scores.get(subject)
        values = list(profile.aptitude_scores.values())
        return max(values) if values else None
    return None


def _extract_subject_from_school_record(label: str) -> str | None:
    match = re.search(r"ĐTB\s+(.+?)\s+(?:lớp\s*)?12", label)
    if match:
        return match.group(1).strip()
    if "Tiếng Anh" in label or "Anh" in label:
        return "Tiếng Anh"
    return None


def _condition_label(condition: Condition) -> str:
    if condition.condition_type == "academic_rank":
        return f"Học lực lớp 12 {condition.operator} {_academic_rank_label(condition.value)}"
    return f"{condition.subject or 'Điều kiện'} {condition.operator} {condition.value:g}"


def _missing_label(condition: Condition) -> str:
    if condition.condition_type == "certificate":
        return f"Điểm {condition.subject}"
    if condition.condition_type == "school_record":
        return condition.subject or "ĐTB lớp 12"
    if condition.condition_type == "academic_rank":
        return "Học lực lớp 12"
    if condition.condition_type == "aptitude_score":
        return condition.subject or "Điểm năng khiếu"
    return condition.subject or "Điểm môn bắt buộc"


def _academic_rank_value(rank: str | None) -> float | None:
    if not rank:
        return None
    return ACADEMIC_RANK_VALUES.get(str(rank).strip().lower())


def _academic_rank_label(value: float) -> str:
    return ACADEMIC_RANK_LABELS.get(float(value), f"{value:g}")
