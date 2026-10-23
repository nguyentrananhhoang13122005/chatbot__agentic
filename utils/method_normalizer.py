# -*- coding: utf-8 -*-
"""Normalize admission method names by exact aliases."""

from __future__ import annotations

import re
import unicodedata


EXAM_METHOD_ALIASES = {"xet diem thi thpt", "diem thi"}
TRANSCRIPT_METHOD_ALIASES = {"xet diem hoc ba thpt"}
EXCLUDED_EXAM_METHOD_ALIASES = {"diem thi rieng", "xet tuyen diem thi rieng"}


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return without_marks.replace("đ", "d").replace("Đ", "D")


def normalize_method(raw: str | None) -> str:
    """Return a stable lowercase, accentless key for an admission method."""
    if raw is None:
        return ""
    text = _strip_accents(str(raw)).lower()
    text = re.sub(r"[^\w\s-]", " ", text, flags=re.UNICODE)
    text = re.sub(r"[-_]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_exam_method(raw: str | None) -> bool:
    """Return True only for exact THPT exam aliases, excluding private exams."""
    key = normalize_method(raw)
    return key in EXAM_METHOD_ALIASES and key not in EXCLUDED_EXAM_METHOD_ALIASES


def is_transcript_method(raw: str | None) -> bool:
    """Return True for exact transcript/admission-record aliases."""
    return normalize_method(raw) in TRANSCRIPT_METHOD_ALIASES
