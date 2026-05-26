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
