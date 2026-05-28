# -*- coding: utf-8 -*-
"""Exam-mode admission matcher built on SQLite repository and parsed rules."""

from __future__ import annotations

import csv
import logging
import os
import re

import pandas as pd

from utils.admission_models import StudentProfile
from utils.admission_repository import AdmissionRepository, AdmissionRow
from utils.admission_rule_parser import (
    PARSER_VERSION,
    build_annotation,
    parse_admission_rule,
    rule_from_json,
    rule_to_json,
)
from utils.combo_validator import validate_combo_inputs
from utils.eligibility_evaluator import evaluate_eligibility
from utils.score_calculator import (
    COMBINATIONS,
    MIN_THRESHOLD,
    calc_exam_score,
    get_strength_analysis,
    get_top_k_combinations,
    normalize_scores,
)


LOGGER = logging.getLogger(__name__)


def find_top_k_schools_exam(
    student_scores: dict,
    k: int,
    bonus: float,
    year_priority: list[int] | None,
    top_n_combos: int,
    province: str | None = None,
    major: str | None = None,
) -> dict:
    """Run the deterministic exam-mode matching pipeline."""
    scores = normalize_scores(_extract_score_mapping(student_scores))
    if not scores:
        return {"error": "Không có dữ liệu điểm hợp lệ."}

    profile = _build_student_profile(student_scores, scores)
    strength = get_strength_analysis(scores)
    top_combos = get_top_k_combinations(scores, k=top_n_combos, bonus=bonus)
    warnings = _build_score_warnings(top_combos)

    try:
        repo = AdmissionRepository()
        data_version = repo.get_row_version()
        rows = _select_exam_rows_for_year_policy(repo, year_priority)
    except Exception as exc:
        return {
            "scores": scores,
            "top_combinations": top_combos,
            "strength": strength,
            "matched_schools": pd.DataFrame(),
            "warnings": warnings + [f"⚠️ Dữ liệu điểm chuẩn chưa sẵn sàng: {exc}"],
        }

    if not rows:
        return {
            "scores": scores,
            "top_combinations": top_combos,
            "strength": strength,
            "matched_schools": pd.DataFrame(),
            "warnings": warnings + ["⚠️ Không tìm thấy dữ liệu điểm thi THPT phù hợp."],
        }
        
    # --- Lọc theo Ngành (Major) ---
    if major:
        rows = [r for r in rows if major.lower() in r.ten_nganh.lower()]
        
    # --- Lọc theo Tỉnh/Thành phố ---
    if province:
        try:
            import json
            json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "university_provinces.json")
            with open(json_path, 'r', encoding='utf-8') as f:
                prov_map = json.load(f)
            # Map province, fallback to "Khác"
            rows = [r for r in rows if prov_map.get(r.truong, "Khác") == province]
        except Exception as e:
            warnings.append(f"⚠️ Không thể tải dữ liệu Tỉnh/Thành phố: {e}")

    if not rows:
        return {
            "scores": scores,
            "top_combinations": top_combos,
            "strength": strength,
            "matched_schools": pd.DataFrame(),
            "warnings": warnings + ["⚠️ Không tìm thấy trường/ngành nào phù hợp với bộ lọc Tỉnh thành & Ngành học."],
        }

    missing_inputs: list[str] = []
    result_rows: list[dict] = []
    unresolved_rules: list[tuple[AdmissionRow, object]] = []
    rule_cache = _load_rule_cache_for_rows(repo, rows, data_version)
    for row in rows:
        rule = _get_parsed_rule(repo, row, data_version, rule_cache)
        if rule.unsupported_reason or rule.unresolved_reason or rule.confidence == "regex_fail":
            unresolved_rules.append((row, rule))
            continue

        eligibility = evaluate_eligibility(rule, profile)
        if eligibility.status == "unknown":
            _extend_unique(missing_inputs, eligibility.missing_inputs)
            continue
        if eligibility.status != "eligible":
            continue

        best = _best_exam_match_for_row(row, rule, profile, bonus, missing_inputs)
        if best:
            result_rows.append(best)

    _write_unresolved_report(unresolved_rules)

    if not result_rows:
        return {
            "scores": scores,
            "top_combinations": top_combos,
            "strength": strength,
            "matched_schools": pd.DataFrame(),
            "total_found": 0,
            "warnings": warnings + ["⚠️ Không tìm thấy ngành phù hợp sau khi kiểm tra điều kiện tuyển sinh."],
            "missing_inputs": missing_inputs,
        }

    df_result = pd.DataFrame(result_rows)
    df_result = df_result[df_result["Delta"] >= -2.0].copy()
    if df_result.empty:
        return {
            "scores": scores,
            "top_combinations": top_combos,
            "strength": strength,
            "matched_schools": pd.DataFrame(),
            "total_found": 0,
            "warnings": warnings + ["⚠️ Không có ngành nào nằm trong vùng điểm thử thách hiện tại."],
            "missing_inputs": missing_inputs,
        }

    df_result = df_result.sort_values("Delta", ascending=False)
    df_result = df_result.drop_duplicates(subset=["Trường", "Mã ngành", "Tên ngành"], keep="first")
    selected = _select_balanced_tiers(df_result, k)
    display_columns = [
        "Trường",
        "Mã ngành",
        "Tên ngành",
        "Phương thức xét tuyển",
        "Điểm chuẩn",
        "Tổ hợp khớp",
        "Điểm min",
        "Điểm của bạn",
        "Delta",
        "Tier",
        "Năm",
        "Thang_40",
        "Chú thích",
        "Công thức",
    ]
    df_top_k = selected[[col for col in display_columns if col in selected.columns]].reset_index(drop=True)
    return {
        "scores": scores,
        "top_combinations": top_combos,
        "strength": strength,
        "matched_schools": df_top_k,
        "total_found": len(df_result),
        "warnings": warnings,
        "missing_inputs": missing_inputs,
    }


def _extract_score_mapping(student_scores: dict) -> dict:
    if "exam_scores" in student_scores and isinstance(student_scores["exam_scores"], dict):
        merged = dict(student_scores["exam_scores"])
        merged.update(student_scores.get("aptitude_scores", {}) or {})
        return merged
    ignored = {
        "not_taken_subjects",
        "ielts",
        "toefl",
        "toeic",
        "has_ccta",
        "gpa_12",
        "gpa_subject_12",
        "academic_rank_12",
        "aptitude_scores",
    }
    return {key: value for key, value in student_scores.items() if key not in ignored}


def _build_student_profile(raw_input: dict, scores: dict[str, float]) -> StudentProfile:
    aptitude_scores = {
        subject: score
        for subject, score in scores.items()
        if subject.startswith("Năng khiếu") or subject.startswith("Vẽ")
    }
    exam_scores = {subject: score for subject, score in scores.items() if subject not in aptitude_scores}
    aptitude_scores.update(raw_input.get("aptitude_scores", {}) or {})
    gpa_subject_12 = raw_input.get("gpa_subject_12", {}) or {}

    normalized_not_taken = set()
    for subject in raw_input.get("not_taken_subjects", set()) or set():
        normalized = normalize_scores({subject: 0.0})
        normalized_not_taken.add(next(iter(normalized.keys()), str(subject)))

    normalized_gpa_subjects = {}
    for key, value in gpa_subject_12.items():
        normalized = normalize_scores({key: 0.0})
        subject = next(iter(normalized.keys()), str(key))
        parsed = _optional_float(value)
        if parsed is not None:
            normalized_gpa_subjects[subject] = parsed

    normalized_aptitude_scores = {}
    for key, value in aptitude_scores.items():
        parsed = _optional_float(value)
        if parsed is not None:
            normalized_aptitude_scores[key] = parsed

    return StudentProfile(
        exam_scores=exam_scores,
        not_taken_subjects=normalized_not_taken,
        ielts=_optional_float(raw_input.get("ielts")),
        toefl=_optional_float(raw_input.get("toefl")),
        toeic=_optional_float(raw_input.get("toeic")),
        has_ccta=raw_input.get("has_ccta"),
        gpa_12=_optional_float(raw_input.get("gpa_12")),
        gpa_subject_12=normalized_gpa_subjects,
        academic_rank_12=raw_input.get("academic_rank_12"),
        aptitude_scores=normalized_aptitude_scores,
    )


def _optional_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _select_exam_rows_for_year_policy(repo: AdmissionRepository, year_priority: list[int] | None) -> list[AdmissionRow]:
    if year_priority:
        for year in year_priority:
            rows = list(repo.iter_exam_rows([year]))
            if rows:
                return rows
        return []
    latest = repo.get_latest_exam_year()
    return list(repo.iter_exam_rows([latest])) if latest else []


def _load_rule_cache_for_rows(repo: AdmissionRepository, rows: list[AdmissionRow], data_version: str) -> dict[str, object]:
    cached_payloads = repo.load_cached_rules((row.row_hash for row in rows), PARSER_VERSION, data_version)
    parsed: dict[str, object] = {}
    for row_hash, payload in cached_payloads.items():
        rule = rule_from_json(payload)
        if rule:
            parsed[row_hash] = rule
    return parsed


def _get_parsed_rule(
    repo: AdmissionRepository,
    row: AdmissionRow,
    data_version: str,
    rule_cache: dict[str, object],
):
    if row.row_hash in rule_cache:
        return rule_cache[row.row_hash]

    cached = repo.load_cached_rule(row.row_hash, PARSER_VERSION, data_version)
    if cached:
        rule = rule_from_json(cached)
        if rule:
            rule_cache[row.row_hash] = rule
            return rule
    rule = parse_admission_rule(row.ghi_chu, row)
    repo.save_cached_rule(row.row_hash, rule_to_json(rule), PARSER_VERSION, data_version)
    rule_cache[row.row_hash] = rule
    return rule


def _best_exam_match_for_row(
    row: AdmissionRow,
    rule,
    profile: StudentProfile,
    bonus: float,
    missing_inputs: list[str],
) -> dict | None:
    school_combos = _parse_to_hop_column(row.to_hop_mon)
    known_combos = [code for code in school_combos if code in COMBINATIONS]
    subject_scores = _profile_subject_scores(profile)
    best: dict | None = None

    for combo_code in known_combos:
        validation = validate_combo_inputs(combo_code, profile, rule)
        if validation.not_taken_subjects:
            continue
        if validation.missing_inputs:
            _extend_unique(missing_inputs, validation.missing_inputs)
            continue
        try:
            score_result = calc_exam_score(subject_scores, combo_code, rule, bonus)
        except ValueError:
            continue

        delta = round(score_result.ranking_score - row.diem_chuan_num, 2)
        candidate = {
            "Trường": row.truong,
            "Mã ngành": row.ma_nganh,
            "Tên ngành": row.ten_nganh,
            "Phương thức xét tuyển": row.phuong_thuc,
            "Điểm chuẩn": round(row.diem_chuan_num, 2),
            "Tổ hợp khớp": combo_code,
            "Điểm min": round(score_result.score_min or score_result.final_score, 2),
            "Điểm của bạn": round(score_result.score_max or score_result.final_score, 2),
            "Delta": delta,
            "Tier": _assign_tier(delta),
            "Năm": row.nam_num,
            "Thang_40": score_result.mode in {"weighted_40", "weighted_40_range"},
            "Chú thích": build_annotation(rule),
            "Công thức": score_result.explanation,
            "_ranking_score": score_result.ranking_score,
        }
        if best is None or candidate["Delta"] > best["Delta"]:
            best = candidate
    return best


def _profile_subject_scores(profile: StudentProfile) -> dict[str, float]:
    scores = dict(profile.exam_scores)
    scores.update(profile.aptitude_scores)
    return scores


def _parse_to_hop_column(to_hop_str: str) -> set[str]:
    if pd.isna(to_hop_str) or not str(to_hop_str).strip():
        return set()
    raw_codes = re.split(r"[;,]\s*", str(to_hop_str))
    valid = set()
    for code in raw_codes:
        value = code.strip().upper()
        if re.match(r"^[A-Z]{1,2}\d{1,2}$", value):
            valid.add(value)
    return valid


def _assign_tier(delta: float) -> str:
    if delta >= 1.5:
        return "✅ AN TOÀN"
    if delta >= 0:
        return "⚡ VỪA SỨC"
    return "🎯 THỬ THÁCH"


def _select_balanced_tiers(df_result: pd.DataFrame, k: int) -> pd.DataFrame:
    df_safe = df_result[df_result["Tier"] == "✅ AN TOÀN"].sort_values("Delta", ascending=True)
    df_fit = df_result[df_result["Tier"] == "⚡ VỪA SỨC"].sort_values("Delta", ascending=True)
    df_challenge = df_result[df_result["Tier"] == "🎯 THỬ THÁCH"].sort_values("Delta", ascending=False)

    if k <= 3:
        min_safe, min_fit, min_challenge = 1, 1, 1
    elif k <= 5:
        min_safe, min_fit, min_challenge = 1, 2, 1
    elif k <= 10:
        min_safe, min_fit, min_challenge = 2, 4, 2
    else:
        min_safe, min_fit, min_challenge = 3, 6, 3

    selected_parts = [
        df_fit.head(min(min_fit, len(df_fit))),
        df_safe.head(min(min_safe, len(df_safe))),
        df_challenge.head(min(min_challenge, len(df_challenge))),
    ]
    selected = pd.concat(selected_parts, ignore_index=False)
    remaining_slots = k - len(selected)
    if remaining_slots > 0:
        used_indices = set(selected.index.tolist())
        tier_order = {"⚡ VỪA SỨC": 0, "✅ AN TOÀN": 1, "🎯 THỬ THÁCH": 2}
        rest = df_result[~df_result.index.isin(used_indices)].copy()
        rest["_tier_order"] = rest["Tier"].map(tier_order)
        rest = rest.sort_values(by=["_tier_order", "Delta"], ascending=[True, True])
        selected = pd.concat([selected, rest.head(remaining_slots)], ignore_index=False)
    return selected.head(k).drop(columns=["_tier_order"], errors="ignore").copy()


def _build_score_warnings(top_combos: list[dict]) -> list[str]:
    warnings = []
    diem_liet_combos = [c for c in top_combos if c.get("has_diem_liet")]
    if diem_liet_combos:
        codes = ", ".join(c["code"] for c in diem_liet_combos)
        warnings.append(f"🚨 CẢNH BÁO ĐỎ: Tổ hợp {codes} có môn bị Điểm Liệt (<= 1.0).")
    below_threshold_combos = [c for c in top_combos if c.get("below_threshold") and not c.get("has_diem_liet")]
    if below_threshold_combos:
        codes = ", ".join(c["code"] for c in below_threshold_combos)
        warnings.append(f"⚠️ Tổ hợp {codes} có tổng điểm dưới ngưỡng tối thiểu {MIN_THRESHOLD} điểm theo quy chế 2026.")
    return warnings


def _extend_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        if value and value not in target:
            target.append(value)


def _write_unresolved_report(unresolved_rules: list[tuple[AdmissionRow, object]]) -> None:
    try:
        os.makedirs("logs", exist_ok=True)
        path = os.path.join("logs", "unresolved_admission_rules.csv")
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "row_hash",
                    "truong",
                    "ma_nganh",
                    "ten_nganh",
                    "nam",
                    "phuong_thuc",
                    "diem_chuan",
                    "to_hop_mon",
                    "ghi_chu",
                    "unresolved_reason",
                ]
            )
            for row, rule in unresolved_rules:
                writer.writerow(
                    [
                        row.row_hash,
                        row.truong,
                        row.ma_nganh,
                        row.ten_nganh,
                        row.nam_num,
                        row.phuong_thuc,
                        _format_unresolved_cutoff(row, rule),
                        row.to_hop_mon,
                        row.ghi_chu,
                        rule.unresolved_reason or rule.unsupported_reason or rule.confidence,
                    ]
                )
    except OSError as exc:
        LOGGER.warning("Could not write unresolved admission report: %s", exc)


def _format_unresolved_cutoff(row: AdmissionRow, rule) -> str:
    scale = getattr(rule, "score_scale", None)
    if not scale:
        scale = 40 if row.diem_chuan_num > 30 else 30
    return f"{_format_report_number(row.diem_chuan_num)} / thang {scale} / {row.nam_num}"


def _format_report_number(value: float) -> str:
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return text or "0"
