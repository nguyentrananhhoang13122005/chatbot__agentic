# -*- coding: utf-8 -*-
"""Shared dataclasses for the admission exam advising pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


SUBJECT_INPUT_MISSING = "missing"
SUBJECT_INPUT_NOT_TAKEN = "not_taken"


@dataclass
class Multiplier:
    subject_role: str
    subject: str | None
    candidates: list[str] = field(default_factory=list)
    factor: float = 1.0
    confidence: str = "high"


@dataclass
class Condition:
    condition_type: str
    subject: str | None
    operator: str
    value: float
    source: str
    alternative: Condition | None = None
    evaluatable: bool = True


@dataclass
class AdmissionRule:
    score_scale: int | None
    converted_to_30: bool
    mode: str
    multipliers: list[Multiplier] = field(default_factory=list)
    conditions: list[Condition] = field(default_factory=list)
    confidence: str = "high"
    unsupported_reason: str | None = None
    unresolved_reason: str | None = None
    raw_note: str = ""
    data_year: int | None = None
    regulation_version: str | None = "2026"


@dataclass
class StudentProfile:
    exam_scores: dict[str, float] = field(default_factory=dict)
    not_taken_subjects: set[str] = field(default_factory=set)
    ielts: float | None = None
    toefl: float | None = None
    toeic: float | None = None
    has_ccta: bool | None = None
    gpa_12: float | None = None
    gpa_subject_12: dict[str, float] = field(default_factory=dict)
    academic_rank_12: str | None = None
    aptitude_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class ScoreResult:
    mode: str
    raw_score: float
    priority_adjusted: float
    final_score: float
    score_min: float | None
    score_max: float | None
    ranking_score: float
    explanation: str


@dataclass
class ComboValidationResult:
    valid: bool
    missing_inputs: list[str] = field(default_factory=list)
    not_taken_subjects: list[str] = field(default_factory=list)
    reason: str | None = None


@dataclass
class EligibilityResult:
    status: str
    failed_conditions: list[str] = field(default_factory=list)
    unknown_conditions: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)


@dataclass
class MatchResult:
    tier: str
    delta: float
    rule: AdmissionRule
    eligibility: EligibilityResult
    score_result: ScoreResult
    data_year: int
    warning_tag: str | None = None
    missing_inputs: list[str] = field(default_factory=list)
    blocked_reason: str | None = None
