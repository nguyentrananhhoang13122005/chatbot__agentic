# -*- coding: utf-8 -*-
"""Test chuẩn hoá tên trường từ tên file DATS (etl_pdf_to_db.extract_school_name)."""
import pytest

from etl_pdf_to_db import extract_school_name, merge_same_school


@pytest.mark.parametrize("filename,expected", [
    ("221. DH công nghệ - ĐH Quốc gia 2025-QHI.pdf", "Đại học công nghệ - Đại học Quốc gia"),
    ("189. ĐH Mở HN-2025.pdf", "Đại học Mở HN"),
    ("30. ĐH Ngoại ngữ- ĐH Đà Nẵng_2025.07.07-Thong-tin-tuyen-sinh-nam-2025.pdf", "Đại học Ngoại ngữ- Đại học Đà Nẵng"),
    ("168.học viện kỹ thuật mật mã2024.pdf", "học viện kỹ thuật mật mã"),
    ("134. HV Hành chính quốc gia_Thong_tin_tuyen_sinh_2025.pdf", "Học viện Hành chính quốc gia"),
    ("316. Trường Đại học Thành Tây (Phennika).pdf", "Trường Đại học Thành Tây (Phennika)"),
])
def test_extract_school_name(filename, expected):
    assert extract_school_name(filename) == expected


def test_same_school_different_year_suffix_gets_same_name():
    assert extract_school_name("7. Trường si-quan-dac-cong 2024.pdf") == extract_school_name("7. Trường si-quan-dac-cong 2025.pdf")


def test_merge_same_school_concatenates_instead_of_dropping():
    records = [
        {"Trường": "Đại học A", "Năm": 2025, "File gốc": "a1.pdf", "Nội dung": "phần 1"},
        {"Trường": "Đại học a", "Năm": 2025, "File gốc": "a2.pdf", "Nội dung": "phần 2"},
        {"Trường": "Đại học B", "Năm": 2025, "File gốc": "b.pdf", "Nội dung": "b"},
    ]
    merged, notes = merge_same_school(records)
    assert len(merged) == 2 and len(notes) == 1
    assert "phần 1" in merged[0]["Nội dung"] and "phần 2" in merged[0]["Nội dung"]
