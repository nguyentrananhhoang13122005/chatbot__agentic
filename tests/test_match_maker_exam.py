# -*- coding: utf-8 -*-

from utils.admission_repository import AdmissionRepository
from utils.admission_rule_parser import PARSER_VERSION, parse_admission_rule, rule_to_json


def test_exam_pipeline_filters_and_returns_annotations(admission_db, monkeypatch, tmp_path):
    import agents.match_maker as match_maker
    import utils.admission_matcher as admission_matcher

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(admission_matcher, "AdmissionRepository", lambda: AdmissionRepository(admission_db))
    result = match_maker.find_top_k_schools(
        {
            "Toán": 8.0,
            "Vật lý": 8.0,
            "Hóa học": 8.0,
            "Ngữ văn": 8.0,
            "Tiếng Anh": 8.0,
        },
        methods=["Xét điểm thi THPT"],
        k=5,
        bonus=0,
        year_priority=[2025],
    )

    df = result["matched_schools"]
    assert not df.empty
    schools = set(df["Trường"])
    assert "Trường A" in schools
    assert "Trường B" in schools
    assert "Trường C" not in schools
    assert "Trường D" not in schools
    assert "Trường E" not in schools
    assert "Trường F" not in schools
    assert "Trường G" not in schools
    assert "Trường H" not in schools
    assert "Chú thích" in df.columns
    assert "Công thức" in df.columns
    assert set(df["Năm"]) == {2025}
    assert any("IELTS" in item for item in result["missing_inputs"])


def test_exam_pipeline_honors_not_taken_without_missing_popup(admission_db, monkeypatch, tmp_path):
    import agents.match_maker as match_maker
    import utils.admission_matcher as admission_matcher

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(admission_matcher, "AdmissionRepository", lambda: AdmissionRepository(admission_db))
    result = match_maker.find_top_k_schools(
        {
            "Toán": 8.0,
            "Vật lý": 8.0,
            "Ngữ văn": 8.0,
            "Tiếng Anh": 8.0,
            "not_taken_subjects": {"Hóa học"},
        },
        methods=["Xét điểm thi THPT"],
        k=5,
        bonus=0,
        year_priority=[2025],
    )
    assert "Hóa học" not in result.get("missing_inputs", [])


def test_exam_pipeline_uses_aptitude_scores_for_matching(admission_db, monkeypatch, tmp_path):
    import agents.match_maker as match_maker
    import utils.admission_matcher as admission_matcher

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(admission_matcher, "AdmissionRepository", lambda: AdmissionRepository(admission_db))
    result = match_maker.find_top_k_schools(
        {
            "exam_scores": {"Toán": 8.0, "Ngữ văn": 8.0, "Vật lý": 7.0, "Hóa học": 7.0},
            "aptitude_scores": {"Vẽ": 9.0},
        },
        methods=["Xét điểm thi THPT"],
        k=10,
        bonus=0,
        year_priority=[2025],
    )
    assert "Trường J" in set(result["matched_schools"]["Trường"])


def test_unresolved_report_is_overwritten_per_run(admission_db, monkeypatch, tmp_path):
    import agents.match_maker as match_maker
    import utils.admission_matcher as admission_matcher

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(admission_matcher, "AdmissionRepository", lambda: AdmissionRepository(admission_db))
    payload = {
        "Toán": 8.0,
        "Vật lý": 8.0,
        "Hóa học": 8.0,
        "Ngữ văn": 8.0,
        "Tiếng Anh": 8.0,
    }
    for _ in range(2):
        match_maker.find_top_k_schools(payload, methods=["Xét điểm thi THPT"], k=5, bonus=0, year_priority=[2025])

    report = tmp_path / "logs" / "unresolved_admission_rules.csv"
    lines = report.read_text(encoding="utf-8").splitlines()
    assert lines[0].split(",") == [
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
    assert len(lines) == 2


def test_unresolved_report_write_error_does_not_block_runtime(admission_db, monkeypatch, tmp_path):
    import builtins
    import agents.match_maker as match_maker
    import utils.admission_matcher as admission_matcher

    def blocked_open(*args, **kwargs):
        raise PermissionError("blocked")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(admission_matcher, "AdmissionRepository", lambda: AdmissionRepository(admission_db))
    monkeypatch.setattr(builtins, "open", blocked_open)
    result = match_maker.find_top_k_schools(
        {"Toán": 8.0, "Vật lý": 8.0, "Hóa học": 8.0, "Ngữ văn": 8.0, "Tiếng Anh": 8.0},
        methods=["Xét điểm thi THPT"],
        k=5,
        bonus=0,
        year_priority=[2025],
    )
    assert not result["matched_schools"].empty


def test_invalid_cached_rule_is_ignored_and_rebuilt(admission_db, monkeypatch, tmp_path):
    import sqlite3
    import agents.match_maker as match_maker
    import utils.admission_matcher as admission_matcher

    repo = AdmissionRepository(admission_db)
    row = next(item for item in repo.iter_exam_rows([2025]) if item.truong == "Trường A")
    data_version = repo.get_row_version()
    invalid_payload = '{"mode":"bad_mode","confidence":"high","multipliers":[],"conditions":[]}'
    repo.save_cached_rule(row.row_hash, invalid_payload, PARSER_VERSION, data_version)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(admission_matcher, "AdmissionRepository", lambda: AdmissionRepository(admission_db))
    match_maker.find_top_k_schools(
        {"Toán": 8.0, "Vật lý": 8.0, "Hóa học": 8.0, "Ngữ văn": 8.0, "Tiếng Anh": 8.0},
        methods=["Xét điểm thi THPT"],
        k=5,
        bonus=0,
        year_priority=[2025],
    )

    conn = sqlite3.connect(admission_db)
    payload = conn.execute(
        "SELECT rule_json FROM admission_rule_cache WHERE row_hash = ?",
        (row.row_hash,),
    ).fetchone()[0]
    conn.close()
    assert payload == rule_to_json(parse_admission_rule(row.ghi_chu, row))


def test_year_policy_uses_latest_year_when_not_specified(admission_db, monkeypatch, tmp_path):
    import agents.match_maker as match_maker
    import utils.admission_matcher as admission_matcher

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(admission_matcher, "AdmissionRepository", lambda: AdmissionRepository(admission_db))
    result = match_maker.find_top_k_schools(
        {"Toán": 8.0, "Vật lý": 8.0, "Hóa học": 8.0, "Ngữ văn": 8.0, "Tiếng Anh": 8.0},
        methods=["Xét điểm thi THPT"],
        k=5,
        bonus=0,
        year_priority=None,
    )
    assert set(result["matched_schools"]["Năm"]) == {2025}


def test_dedup_keeps_single_school_major_code(admission_db, monkeypatch, tmp_path):
    import agents.match_maker as match_maker
    import utils.admission_matcher as admission_matcher

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(admission_matcher, "AdmissionRepository", lambda: AdmissionRepository(admission_db))
    result = match_maker.find_top_k_schools(
        {"Toán": 8.0, "Vật lý": 8.0, "Hóa học": 8.0, "Ngữ văn": 8.0, "Tiếng Anh": 8.0},
        methods=["Xét điểm thi THPT"],
        k=10,
        bonus=0,
        year_priority=None,
    )
    df = result["matched_schools"]
    assert not df.duplicated(subset=["Trường", "Mã ngành", "Tên ngành"]).any()


def test_regex_fail_is_logged_and_excluded(admission_db, monkeypatch, tmp_path):
    import agents.match_maker as match_maker
    import utils.admission_matcher as admission_matcher

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(admission_matcher, "AdmissionRepository", lambda: AdmissionRepository(admission_db))
    result = match_maker.find_top_k_schools(
        {"Toán": 8.0, "Vật lý": 8.0, "Hóa học": 8.0, "Ngữ văn": 8.0, "Tiếng Anh": 8.0},
        methods=["Xét điểm thi THPT"],
        k=10,
        bonus=0,
        year_priority=[2025],
    )

    assert "Trường H" not in set(result["matched_schools"]["Trường"])
    report = (tmp_path / "logs" / "unresolved_admission_rules.csv").read_text(encoding="utf-8")
    assert "Trường H" in report
    assert "24 / thang 30 / 2025" in report
    assert "influential_note_not_parsed" in report


def test_rule_cache_is_warmed_for_exam_rows(admission_db, monkeypatch, tmp_path):
    import sqlite3
    import agents.match_maker as match_maker
    import utils.admission_matcher as admission_matcher

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(admission_matcher, "AdmissionRepository", lambda: AdmissionRepository(admission_db))
    match_maker.find_top_k_schools(
        {"Toán": 8.0, "Vật lý": 8.0, "Hóa học": 8.0, "Ngữ văn": 8.0, "Tiếng Anh": 8.0},
        methods=["Xét điểm thi THPT"],
        k=5,
        bonus=0,
        year_priority=[2025],
    )

    conn = sqlite3.connect(admission_db)
    cache_count = conn.execute("SELECT count(*) FROM admission_rule_cache").fetchone()[0]
    conn.close()
    assert cache_count >= 6


def test_focus_school_planner_uses_balanced_strategy_without_risky_challenge():
    import pandas as pd
    import agents.match_maker as match_maker

    result = {
        "scores": {"Toán": 8.5, "Vật lý": 8.0, "Hóa học": 8.0},
        "top_combinations": [{"code": "A00", "total": 24.5, "subjects": ["Toán", "Vật lý", "Hóa học"]}],
        "user_filters": {"major": "Công nghệ", "province": None, "top_k": 10, "mode": "exam"},
        "matched_schools": pd.DataFrame(
            [
                ["Trường Mơ Ước", "Công nghệ thông tin", "Xét điểm thi THPT", 25.0, "A00", 24.5, 24.5, -0.5, "🎯 THỬ THÁCH", 2025],
                ["Trường Rủi Ro", "Công nghệ phần mềm", "Xét điểm thi THPT", 26.0, "A00", 24.5, 24.5, -1.5, "🎯 THỬ THÁCH", 2025],
                ["Trường Vừa 1", "Công nghệ dữ liệu", "Xét điểm thi THPT", 24.0, "A00", 24.5, 24.5, 0.5, "⚡ VỪA SỨC", 2025],
                ["Trường Vừa 2", "Công nghệ AI", "Xét điểm thi THPT", 23.8, "A00", 24.5, 24.5, 0.7, "⚡ VỪA SỨC", 2025],
                ["Trường Vừa 3", "Công nghệ máy tính", "Xét điểm thi THPT", 23.5, "A00", 24.5, 24.5, 1.0, "⚡ VỪA SỨC", 2025],
                ["Trường An Toàn", "Hệ thống thông tin", "Xét điểm thi THPT", 22.0, "A00", 24.5, 24.5, 2.5, "✅ AN TOÀN", 2025],
            ],
            columns=[
                "Trường",
                "Tên ngành",
                "Phương thức xét tuyển",
                "Điểm chuẩn",
                "Tổ hợp khớp",
                "Điểm min",
                "Điểm của bạn",
                "Delta",
                "Tier",
                "Năm",
            ],
        ),
    }

    planner = match_maker._select_focus_schools(result)
    focus = planner["focus_schools"]

    assert len(focus) == 5
    assert "Trường Mơ Ước" in set(focus["Trường"])
    assert "Trường Rủi Ro" not in set(focus["Trường"])
    assert len(planner["reference_schools"]) == 1


def test_analysis_prompt_uses_user_friendly_gap_and_no_percentage_probability():
    import pandas as pd
    import agents.match_maker as match_maker

    result = {
        "scores": {"Toán": 8.0, "Ngữ văn": 7.0, "Tiếng Anh": 8.5},
        "strength": {"avg": 7.83, "category": "Khá", "strongest": ["Tiếng Anh"], "weakest": ["Ngữ văn"]},
        "top_combinations": [{"code": "D01", "total": 23.5, "subjects": ["Toán", "Ngữ văn", "Tiếng Anh"]}],
        "warnings": ["Kiểm tra kỹ điều kiện phụ nếu trường yêu cầu chứng chỉ."],
        "missing_inputs": ["IELTS"],
        "user_filters": {"major": "Ngôn ngữ", "province": "Hà Nội", "top_k": 5, "mode": "exam"},
        "matched_schools": pd.DataFrame(
            [
                ["Trường A", "Ngôn ngữ Anh", "Xét điểm thi THPT", 23.0, "D01", 23.5, 23.5, 0.5, "⚡ VỪA SỨC", 2025],
                ["Trường B", "Ngôn ngữ Trung", "Xét điểm thi THPT", 22.0, "D01", 23.5, 23.5, 1.5, "✅ AN TOÀN", 2025],
            ],
            columns=[
                "Trường",
                "Tên ngành",
                "Phương thức xét tuyển",
                "Điểm chuẩn",
                "Tổ hợp khớp",
                "Điểm min",
                "Điểm của bạn",
                "Delta",
                "Tier",
                "Năm",
            ],
        ),
    }

    prompt = match_maker.build_analysis_prompt(result)

    assert "Delta" not in prompt
    assert "Chênh lệch điểm" in prompt
    assert "cao hơn điểm chuẩn 0.5 điểm" in prompt
    assert "phần trăm" in prompt
    assert "IELTS" in prompt
