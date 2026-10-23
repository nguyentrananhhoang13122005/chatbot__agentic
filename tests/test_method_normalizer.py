# -*- coding: utf-8 -*-

from utils.method_normalizer import is_exam_method, is_transcript_method, normalize_method


def test_exam_aliases_are_exact():
    assert is_exam_method("Xét điểm thi THPT")
    assert is_exam_method("  Điểm   thi  ")
    assert normalize_method("XÉT   ĐIỂM THI thpt") == "xet diem thi thpt"


def test_excluded_exam_aliases_do_not_match():
    assert not is_exam_method("Điểm thi riêng")
    assert not is_exam_method("xét tuyển điểm thi riêng")


def test_transcript_is_not_exam():
    assert is_transcript_method("Xét điểm Học bạ THPT")
    assert not is_exam_method("Xét điểm Học bạ THPT")


def test_mixed_case_and_accents_normalize_to_same_key():
    assert normalize_method("  xÉT   ĐiỂm   Thi   THPT ") == "xet diem thi thpt"


def test_punctuation_does_not_create_substring_match():
    assert not is_exam_method("Xét điểm thi THPT - kết hợp phỏng vấn")


def test_none_and_empty_are_not_exam():
    assert normalize_method(None) == ""
    assert not is_exam_method("")
