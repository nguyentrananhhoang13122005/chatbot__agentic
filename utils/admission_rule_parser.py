# -*- coding: utf-8 -*-
"""Deterministic parser for admission-note rules."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict
from typing import Any

from utils.admission_models import AdmissionRule, Condition, Multiplier
from utils.score_calculator import normalize_subject_name


PARSER_VERSION = "regex-v2"
ALLOWED_CACHE_MODES = {"normal_30", "weighted_40", "weighted_convert_30", "weighted_40_range", "unsupported"}
ALLOWED_CACHE_CONFIDENCES = {"high", "medium", "regex_fail", "unsupported"}

FOREIGN_LANGUAGE_SUBJECTS = {
    "Tiếng Anh",
    "Tiếng Nga",
    "Tiếng Pháp",
    "Tiếng Trung",
    "Tiếng Đức",
    "Tiếng Nhật",
}

NOTE_SUBJECT_MAP = {
    "toán": "Toán",
    "toan": "Toán",
    "văn": "Ngữ văn",
    "van": "Ngữ văn",
    "ngữ văn": "Ngữ văn",
    "anh": "Tiếng Anh",
    "tiếng anh": "Tiếng Anh",
    "tieng anh": "Tiếng Anh",
    "ta": "Tiếng Anh",
    "lý": "Vật lý",
    "ly": "Vật lý",
    "vật lý": "Vật lý",
    "hóa": "Hóa học",
    "hoa": "Hóa học",
    "hóa học": "Hóa học",
    "sinh": "Sinh học",
    "sinh học": "Sinh học",
    "sử": "Lịch sử",
    "lịch sử": "Lịch sử",
    "địa": "Địa lý",
    "địa lý": "Địa lý",
    "gdcd": "GDCD",
    "trung": "Tiếng Trung",
    "tiếng trung": "Tiếng Trung",
    "nhật": "Tiếng Nhật",
    "tiếng nhật": "Tiếng Nhật",
    "pháp": "Tiếng Pháp",
    "tiếng pháp": "Tiếng Pháp",
    "đức": "Tiếng Đức",
    "tiếng đức": "Tiếng Đức",
    "nga": "Tiếng Nga",
    "tiếng nga": "Tiếng Nga",
    "ngoại ngữ": None,
    "vẽ": "Vẽ",
    "vẽ hhmt": "Vẽ HHMT",
    "vẽ ttm": "Vẽ TTM",
    "vẽ tttm": "Vẽ TTM",
    "năng khiếu": None,
}

INFLUENTIAL_KEYWORDS = (
    "nhân",
    "hệ số",
    "thang",
    "ielts",
    "toefl",
    "toeic",
    "điểm trung bình",
    "đtb",
    "đạt từ",
    "tối thiểu",
    "≥",
    "năng khiếu",
)

ACADEMIC_RANK_VALUES = {
    "trung bình": 1.0,
    "khá": 2.0,
    "giỏi": 3.0,
    "tốt": 3.0,
}


def normalize_note(raw: str | None) -> str:
    """Normalize a raw note without dropping admission information."""
    text = unicodedata.normalize("NFC", str(raw or "").strip())
    text = text.replace(";", ",").replace("：", ":")
    text = text.replace(">=", "≥").replace("≧", "≥")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([,:≥])\s*", r"\1 ", text)
    abbreviation_map = {
        r"\bT\.?\s*Anh\b": "Tiếng Anh",
        r"\bTA\b": "Tiếng Anh",
        r"\bNK\b": "Năng khiếu",
        r"\bĐTB\b": "Điểm trung bình",
        r"\bDTB\b": "Điểm trung bình",
        r"\bHL12\b": "Học lực lớp 12",
        r"\bHĐ\b": "Học lực",
        r"\bSKĐA\b": "SKĐA",
        r"\bHHMT\b": "HHMT",
        r"\bTTTM\b": "TTM",
        r"\bTTM\b": "TTM",
        r"\bTDTT\b": "TDTT",
    }
    for pattern, replacement in abbreviation_map.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"(\d+\.\d)0+\b", r"\1", text)
    return text.strip()


def parse_admission_rule(raw_note: str | None, row_context: Any = None) -> AdmissionRule:
    """Parse a note into an AdmissionRule using deterministic regex patterns."""
    raw = str(raw_note or "").strip()
    note = normalize_note(raw)
    lower = note.lower()
    cutoff = _context_float(row_context, "diem_chuan_num", "Điểm chuẩn_Num", "Điểm chuẩn")
    data_year = _context_int(row_context, "nam_num", "Năm_Num", "Năm")

    if re.search(r"năng lực\s+(tiếng anh|ta)", lower):
        return AdmissionRule(
            score_scale=None,
            converted_to_30=False,
            mode="unsupported",
            confidence="unsupported",
            unsupported_reason="english_competency_component",
            raw_note=raw,
            data_year=data_year,
        )

    if re.search(r"thang(?: điểm)?\s*35", lower):
        return AdmissionRule(
            score_scale=35,
            converted_to_30=False,
            mode="unsupported",
            confidence="unsupported",
            unsupported_reason="scale_35",
            raw_note=raw,
            data_year=data_year,
        )

    unsupported_note_reason = _unsupported_note_reason(lower)
    if unsupported_note_reason:
        return AdmissionRule(
            score_scale=None,
            converted_to_30=False,
            mode="unsupported",
            confidence="unsupported",
            unsupported_reason=unsupported_note_reason,
            raw_note=raw,
            data_year=data_year,
        )

    multipliers = _parse_multipliers(note)
    conditions = _parse_conditions(note)
    converted_to_30 = bool(re.search(r"quy\s+về\s+thang(?: điểm)?\s*30", lower))
    explicit_scale_40 = bool(re.search(r"thang(?: điểm)?\s*40", lower))
    inferred_scale_40 = cutoff is not None and cutoff > 30

    score_scale = 40 if explicit_scale_40 or inferred_scale_40 else 30
    confidence = "high"
    unsupported_reason = None
    unresolved_reason = None

    if converted_to_30:
        mode = "weighted_convert_30" if multipliers else "normal_30"
        score_scale = 30
    elif explicit_scale_40 or inferred_scale_40:
        mode = "weighted_40" if multipliers else "weighted_40_range"
        confidence = "medium" if not multipliers else "high"
    elif multipliers:
        mode = "weighted_convert_30"
        confidence = "medium"
    else:
        mode = "normal_30"

    if not raw and inferred_scale_40:
        mode = "weighted_40_range"
        confidence = "medium"
    elif not raw:
        mode = "normal_30"
        confidence = "high"
        score_scale = 30

    if raw and _looks_influential(lower) and not multipliers and not conditions and mode == "normal_30":
        confidence = "regex_fail"
        unresolved_reason = "influential_note_not_parsed"

    return AdmissionRule(
        score_scale=score_scale,
        converted_to_30=converted_to_30,
        mode=mode,
        multipliers=multipliers,
        conditions=conditions,
        confidence=confidence,
        unsupported_reason=unsupported_reason,
        unresolved_reason=unresolved_reason,
        raw_note=raw,
        data_year=data_year,
        regulation_version="2026",
    )


def build_annotation(rule: AdmissionRule) -> str:
    """Build a compact annotation string for result tables."""
    parts: list[str] = []
    for multiplier in rule.multipliers:
        if multiplier.subject:
            label = multiplier.subject
        elif multiplier.candidates:
            label = "/".join(multiplier.candidates)
        elif multiplier.subject_role == "foreign_language_in_combo":
            label = "Ngoại ngữ"
        else:
            label = "Năng khiếu"
        parts.append(f"📐 {label} ×{_format_number(multiplier.factor)}")

    if rule.mode in {"weighted_40", "weighted_40_range"}:
        parts.append("📊 Thang 40")
    if rule.converted_to_30:
        parts.append("📊 Quy đổi 30")

    for condition in rule.conditions:
        icon = "📜" if condition.condition_type == "certificate" else "⚠️"
        parts.append(f"{icon} {_condition_label(condition)}")

    if rule.confidence == "medium":
        parts.append("🔶 Ước lượng - thông tin chưa đầy đủ")
    if rule.unresolved_reason:
        parts.append("🔶 Chưa rõ quy tắc")
    if rule.unsupported_reason:
        parts.append(f"⚠️ Không hỗ trợ: {rule.unsupported_reason}")

    return " · ".join(parts)


def rule_to_json(rule: AdmissionRule) -> str:
    """Serialize an AdmissionRule to JSON for deterministic cache storage."""
    return json.dumps(asdict(rule), ensure_ascii=False, sort_keys=True)


def rule_from_json(payload: str) -> AdmissionRule | None:
    """Load and validate a cached AdmissionRule JSON payload."""
    try:
        data = json.loads(payload)
        required = {"mode", "confidence", "multipliers", "conditions"}
        if not required.issubset(data):
            return None
        if data.get("mode") not in ALLOWED_CACHE_MODES:
            return None
        if data.get("confidence") not in ALLOWED_CACHE_CONFIDENCES:
            return None
        if not isinstance(data.get("multipliers"), list) or not isinstance(data.get("conditions"), list):
            return None
        multipliers = [Multiplier(**item) for item in data.get("multipliers", [])]
        conditions = [_condition_from_dict(item) for item in data.get("conditions", [])]
        return AdmissionRule(
            score_scale=data.get("score_scale"),
            converted_to_30=bool(data.get("converted_to_30")),
            mode=str(data.get("mode")),
            multipliers=multipliers,
            conditions=conditions,
            confidence=str(data.get("confidence")),
            unsupported_reason=data.get("unsupported_reason"),
            unresolved_reason=data.get("unresolved_reason"),
            raw_note=str(data.get("raw_note", "")),
            data_year=data.get("data_year"),
            regulation_version=data.get("regulation_version"),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _parse_multipliers(note: str) -> list[Multiplier]:
    multipliers: list[Multiplier] = []
    seen: set[tuple[str, str | None, tuple[str, ...], float]] = set()

    for match in re.finditer(
        r"(?P<a>[A-Za-zÀ-ỹĐđ\s]+?)\s+hoặc\s+(?P<b>[A-Za-zÀ-ỹĐđ\s]+?)\s+"
        r"(?:nhân(?: hệ số)?|hệ số|x)\s*(?P<factor>\d+(?:[.,]\d+)?)",
        note,
        flags=re.IGNORECASE,
    ):
        candidates = [_normalize_note_subject(match.group("a")), _normalize_note_subject(match.group("b"))]
        candidates = [item for item in candidates if item]
        _add_multiplier(
            multipliers,
            seen,
            Multiplier("exact", None, candidates, _parse_number(match.group("factor")), "high"),
        )

    for match in re.finditer(
        r"(?:điểm\s+)?năng khiếu(?:\s+[A-Za-zÀ-ỹĐđ0-9]+)?\s*x\s*(?P<factor>\d+(?:[.,]\d+)?)",
        note,
        flags=re.IGNORECASE,
    ):
        _add_multiplier(
            multipliers,
            seen,
            Multiplier("aptitude_detail", None, [], _parse_number(match.group("factor")), "high"),
        )

    for match in re.finditer(
        r"(?P<subject>[A-Za-zÀ-ỹĐđ0-9\.\s]+?)\s+"
        r"(?:nhân(?: hệ số)?|hệ số)\s*(?P<factor>\d+(?:[.,]\d+)?)",
        note,
        flags=re.IGNORECASE,
    ):
        raw_subject = _clean_subject_phrase(match.group("subject"))
        if " hoặc " in raw_subject.lower():
            continue
        subject = _normalize_note_subject(raw_subject)
        factor = _parse_number(match.group("factor"))
        if raw_subject.lower() == "ngoại ngữ":
            item = Multiplier("foreign_language_in_combo", None, [], factor, "high")
        elif subject:
            item = Multiplier("exact", subject, [], factor, "high")
        elif "năng khiếu" in raw_subject.lower():
            item = Multiplier("aptitude_detail", None, [], factor, "high")
        else:
            item = Multiplier("exact", None, [], factor, "medium")
        _add_multiplier(multipliers, seen, item)

    return multipliers


def _parse_conditions(note: str) -> list[Condition]:
    conditions: list[Condition] = []
    for segment in [part.strip() for part in note.split(",") if part.strip()]:
        shared_or = _parse_shared_or_condition(segment)
        if shared_or:
            conditions.append(shared_or)
            continue

        compound = _parse_compound_condition(segment)
        if compound:
            conditions.extend(compound)
            continue

        if " hoặc " in segment.lower():
            left, right = re.split(r"\s+hoặc\s+", segment, maxsplit=1, flags=re.IGNORECASE)
            left_condition = _parse_single_condition(left)
            right_condition = _parse_single_condition(right)
            if left_condition and right_condition:
                left_condition.alternative = right_condition
                conditions.append(left_condition)
            else:
                if left_condition:
                    conditions.append(left_condition)
                if right_condition:
                    conditions.append(right_condition)
            continue
        condition = _parse_single_condition(segment)
        if condition:
            conditions.append(condition)
    return conditions


def _parse_shared_or_condition(text: str) -> Condition | None:
    match = re.search(
        r"(?P<a>[A-Za-zÀ-ỹĐđ0-9\.\s]+?)\s+hoặc\s+(?P<b>[A-Za-zÀ-ỹĐđ0-9\.\s]+?)\s*"
        r"(?:≥|>|đạt từ|đạt tối thiểu|tối thiểu)\s*(?P<value>\d+(?:[.,]\d+)?)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    first = _condition_for_subject(match.group("a"), match.group("value"))
    second = _condition_for_subject(match.group("b"), match.group("value"))
    if not first or not second:
        return None
    first.alternative = second
    return first


def _parse_compound_condition(text: str) -> list[Condition]:
    match = re.search(
        r"(?:môn\s+)?(?P<subjects>[A-Za-zÀ-ỹĐđ0-9\.\s]+?\s+và\s+[A-Za-zÀ-ỹĐđ0-9\.\s]+?)\s*"
        r"(?:≥|>|đạt từ|đạt tối thiểu|tối thiểu)\s*(?P<value>\d+(?:[.,]\d+)?)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return []
    subjects = re.split(r"\s+và\s+", match.group("subjects"), flags=re.IGNORECASE)
    return [item for item in (_condition_for_subject(subject, match.group("value")) for subject in subjects) if item]


def _parse_single_condition(text: str) -> Condition | None:
    lower = text.lower()
    academic_rank = _parse_academic_rank_condition(lower)
    if academic_rank:
        return academic_rank

    cert = re.search(r"\b(ielts|toefl|toeic)\b\s*(?:≥|>|:|đạt từ)?\s*(\d+(?:[.,]\d+)?)", lower)
    if cert:
        return Condition(
            condition_type="certificate",
            subject=cert.group(1).upper(),
            operator=">=",
            value=_parse_number(cert.group(2)),
            source="certificate",
        )

    school_record = re.search(
        r"(?:điểm\s+)?(?:đk\s+)?(?:điểm trung bình|đtb)?\s*(?:lớp\s*)?12?\s*"
        r"(?:môn\s+)?(?P<subject>[A-Za-zÀ-ỹĐđ\s]+?)?\s*(?:học bạ)?\s*(?:≥|:|đạt từ)\s*"
        r"(?P<value>\d+(?:[.,]\d+)?)",
        lower,
    )
    if school_record and ("điểm trung bình" in lower or "đtb" in lower or "học bạ" in lower):
        subject = _normalize_note_subject(school_record.group("subject") or "")
        label = f"ĐTB {subject} lớp 12" if subject else "ĐTB lớp 12"
        return Condition("school_record", label, ">=", _parse_number(school_record.group("value")), "transcript")

    dk_english = re.search(r"điểm\s+đk\s+tiếng anh\s+học bạ\s*:\s*(\d+(?:[.,]\d+)?)", lower)
    if dk_english:
        return Condition(
            "school_record",
            "ĐTB Tiếng Anh học bạ",
            ">=",
            _parse_number(dk_english.group(1)),
            "transcript",
        )

    threshold = re.search(
        r"(?P<subject>toán|văn|ngữ văn|anh|tiếng anh|trung|tiếng trung|lý|vật lý|hóa|hóa học|sinh|sinh học|sử|lịch sử|địa|địa lý|gdcd|vẽ hhmt|vẽ ttm|năng khiếu(?:\s+[a-zà-ỹđ0-9]+){0,4})\s*"
        r"(?:≥|>|đạt từ|đạt tối thiểu|tối thiểu)\s*(?P<value>\d+(?:[.,]\d+)?)",
        lower,
        flags=re.IGNORECASE,
    )
    if threshold:
        subject = _normalize_note_subject(threshold.group("subject"))
        condition_type = "aptitude_score" if threshold.group("subject").startswith(("vẽ", "năng khiếu")) else "subject_score"
        source = "aptitude" if condition_type == "aptitude_score" else "exam"
        return Condition(condition_type, subject, ">=", _parse_number(threshold.group("value")), source)

    generic_aptitude = re.search(r"(?:đạt\s+)?tối thiểu\s*(\d+(?:[.,]\d+)?)\s*điểm", lower)
    if generic_aptitude and "năng khiếu" in lower:
        return Condition("aptitude_score", None, ">=", _parse_number(generic_aptitude.group(1)), "aptitude")
    return None


def _parse_academic_rank_condition(lower: str) -> Condition | None:
    match = re.search(
        r"học lực(?:\s+lớp\s*12)?(?:\s+(?:xếp loại|loại|mức))?\s+"
        r"(?:từ\s+)?(?P<rank>giỏi|khá|trung bình|tốt)(?:\s+trở lên)?",
        lower,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    rank = match.group("rank").lower()
    return Condition(
        condition_type="academic_rank",
        subject="Học lực lớp 12",
        operator=">=",
        value=ACADEMIC_RANK_VALUES[rank],
        source="school_record",
    )


def _condition_for_subject(subject_text: str, value: str) -> Condition | None:
    subject_text = _clean_subject_phrase(subject_text)
    subject = _normalize_note_subject(subject_text)
    lower_subject = subject_text.lower()
    if not subject:
        return None
    condition_type = "aptitude_score" if lower_subject.startswith(("vẽ", "năng khiếu")) else "subject_score"
    source = "aptitude" if condition_type == "aptitude_score" else "exam"
    return Condition(condition_type, subject, ">=", _parse_number(value), source)


def _add_multiplier(
    multipliers: list[Multiplier],
    seen: set[tuple[str, str | None, tuple[str, ...], float]],
    item: Multiplier,
) -> None:
    key = (item.subject_role, item.subject, tuple(sorted(item.candidates)), item.factor)
    if key not in seen:
        multipliers.append(item)
        seen.add(key)


def _clean_subject_phrase(value: str) -> str:
    text = re.sub(r"^(điểm|môn|điểm môn)\s+", "", value.strip(), flags=re.IGNORECASE)
    text = re.split(r"[,.:]", text)[-1].strip()
    return text


def _normalize_note_subject(value: str) -> str | None:
    cleaned = _clean_subject_phrase(value).lower().strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return None
    if cleaned in NOTE_SUBJECT_MAP:
        return NOTE_SUBJECT_MAP[cleaned]
    if cleaned.startswith("năng khiếu skđa"):
        suffix = cleaned.removeprefix("năng khiếu skđa").strip()
        return f"Năng khiếu SKĐA {suffix}".strip()
    if cleaned.startswith("năng khiếu tdtt"):
        suffix = cleaned.removeprefix("năng khiếu tdtt").strip()
        return f"Năng khiếu TDTT {suffix}".strip()
    if cleaned.startswith("năng khiếu"):
        return " ".join(part.upper() if part in {"skđa", "tdtt"} else part.capitalize() for part in cleaned.split())
    normalized = normalize_subject_name(cleaned)
    return normalized if normalized != cleaned or cleaned[:1].isupper() else None


def _parse_number(value: str) -> float:
    return float(str(value).replace(",", "."))


def _looks_influential(lower_note: str) -> bool:
    return any(keyword in lower_note for keyword in INFLUENTIAL_KEYWORDS)


def _unsupported_note_reason(lower_note: str) -> str | None:
    if re.search(r"\b(?:đgnl|dgnl)\b|đánh giá năng lực", lower_note, flags=re.IGNORECASE):
        return "external_assessment_component"
    if re.search(r"\bccnnqt\b|chứng chỉ ngoại ngữ quốc tế", lower_note, flags=re.IGNORECASE):
        return "certificate_component_without_threshold"
    if "học bạ lớp 12 theo tổ hợp" in lower_note:
        return "transcript_combo_component"
    return None


def _context_float(row_context: Any, *names: str) -> float | None:
    value = _context_value(row_context, *names)
    try:
        return float(value) if value not in {None, ""} else None
    except (TypeError, ValueError):
        return None


def _context_int(row_context: Any, *names: str) -> int | None:
    value = _context_value(row_context, *names)
    try:
        return int(float(value)) if value not in {None, ""} else None
    except (TypeError, ValueError):
        return None


def _context_value(row_context: Any, *names: str) -> Any:
    if row_context is None:
        return None
    for name in names:
        if hasattr(row_context, name):
            return getattr(row_context, name)
        if isinstance(row_context, dict) and name in row_context:
            return row_context[name]
        try:
            return row_context[name]
        except Exception:
            pass
    return None


def _condition_label(condition: Condition) -> str:
    if condition.condition_type == "academic_rank":
        subject = condition.subject or "Học lực lớp 12"
        label = f"{subject} {condition.operator} {_academic_rank_label(condition.value)}"
        if condition.alternative:
            return f"{label} hoặc {_condition_label(condition.alternative)}"
        return label
    subject = condition.subject or "Điều kiện"
    if condition.alternative:
        return f"{subject} {condition.operator} {_format_number(condition.value)} hoặc {_condition_label(condition.alternative)}"
    return f"{subject} {condition.operator} {_format_number(condition.value)}"


def _format_number(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def _academic_rank_label(value: float) -> str:
    labels = {1.0: "Trung bình", 2.0: "Khá", 3.0: "Giỏi"}
    return labels.get(float(value), _format_number(value))


def _condition_from_dict(data: dict[str, Any]) -> Condition:
    alternative = data.get("alternative")
    return Condition(
        condition_type=data["condition_type"],
        subject=data.get("subject"),
        operator=data.get("operator", ">="),
        value=float(data.get("value", 0)),
        source=data.get("source", ""),
        alternative=_condition_from_dict(alternative) if isinstance(alternative, dict) else None,
        evaluatable=bool(data.get("evaluatable", True)),
    )
