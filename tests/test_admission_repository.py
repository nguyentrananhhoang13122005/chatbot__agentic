# -*- coding: utf-8 -*-

import pytest

from utils.admission_repository import AdmissionRepository


def test_repository_maps_vietnamese_columns(admission_db):
    repo = AdmissionRepository(admission_db)
    row = next(repo.iter_exam_rows([2025]))
    assert row.truong == "Trường A"
    assert row.ma_nganh == "7480201"
    assert row.ten_nganh == "Công nghệ thông tin"
    assert row.diem_chuan_num == 24


def test_repository_filters_exam_scope(admission_db):
    repo = AdmissionRepository(admission_db)
    rows = list(repo.iter_exam_rows([2025]))
    schools = {row.truong for row in rows}
    assert "Trường A" in schools
    assert "Trường B" in schools
    assert "Trường C" not in schools
    assert "Trường D" not in schools
    assert "Trường E" not in schools


def test_repository_year_filter_and_version(admission_db):
    repo = AdmissionRepository(admission_db)
    rows_2024 = list(repo.iter_exam_rows([2024]))
    assert [row.nam_num for row in rows_2024] == [2024]
    assert repo.get_row_version() == "fixture-v1"


def test_repository_missing_db_raises_in_production(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(FileNotFoundError):
        AdmissionRepository(tmp_path / "missing.db")
