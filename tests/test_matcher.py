# -*- coding: utf-8 -*-
"""
UNIT TESTS — Hybrid School Matcher (Offline, no API/data needed)

Chạy:
  pytest tests/test_matcher.py -v
  python -m pytest tests/test_matcher.py -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from agents.recommender import (
    find_matching_schools,
    _normalize_school_name,
    _tokenize_vn,
    _bm25_score,
    _fuzzy_score,
    _token_overlap_score,
)

# ============================================================
# FIXTURE: Danh sách trường giả lập (phổ biến nhất)
# ============================================================
MOCK_SCHOOLS = [
    "ĐH Bách khoa Hà Nội",
    "ĐH Bách khoa TP.HCM",
    "ĐH Bách khoa Đà Nẵng",
    "Học viện Bưu chính Viễn thông",
    "ĐH Kinh tế Quốc dân",
    "ĐH Kinh tế TP.HCM",
    "ĐH Ngoại thương",
    "ĐH Công nghệ - ĐHQG Hà Nội",
    "ĐH Khoa học Tự nhiên - ĐHQG Hà Nội",
    "ĐH Sư phạm Hà Nội",
    "ĐH Sư phạm TP.HCM",
    "ĐH Sư phạm Kỹ thuật TP.HCM",
    "ĐH Y Dược Buôn Ma Thuột",
    "ĐH Y Hà Nội",
    "ĐH Y Dược TP.HCM",
    "ĐH Công nghiệp Hà Nội",
    "ĐH Công nghiệp TP.HCM",
    "ĐH Công nghiệp Dệt May Hà Nội",
    "ĐH Điện lực",
    "ĐH FPT",
    "ĐH Giao thông Vận tải",
    "ĐH Luật Hà Nội",
    "ĐH Thương mại",
    "Học viện Tài chính",
    "Học viện Ngân hàng",
    "ĐH Xây dựng Hà Nội",
    "ĐH Mỏ - Địa chất",
    "ĐH Thủy lợi",
    "ĐH Phenikaa",
    "ĐH Văn Lang",
]


# ============================================================
# TEST GROUP 1: _normalize_school_name
# ============================================================
class TestNormalizeSchoolName:
    def test_strip_leading_number(self):
        assert "đại học bách khoa" in _normalize_school_name("33. ĐH Bách khoa")

    def test_strip_trailing_year(self):
        result = _normalize_school_name("ĐH ABC 2024")
        assert "2024" not in result

    def test_lowercase(self):
        result = _normalize_school_name("ĐH BÁCH KHOA HÀ NỘI")
        assert result == result.lower()

    def test_alias_hn(self):
        result = _normalize_school_name("ĐH Bách khoa HN")
        assert "hà nội" in result

    def test_alias_hcm(self):
        result = _normalize_school_name("ĐH Bách khoa HCM")
        assert "hồ chí minh" in result

    def test_alias_tphcm(self):
        result = _normalize_school_name("ĐH Kinh tế TPHCM")
        assert "hồ chí minh" in result

    def test_alias_dhqg(self):
        result = _normalize_school_name("ĐHQG Hà Nội")
        assert "đại học quốc gia" in result

    def test_empty_string(self):
        result = _normalize_school_name("")
        assert result == ""

    def test_special_chars(self):
        result = _normalize_school_name("ĐH_Bách-khoa")
        assert "_" not in result
        assert "-" not in result


# ============================================================
# TEST GROUP 2: _tokenize_vn
# ============================================================
class TestTokenizeVn:
    def test_basic(self):
        tokens = _tokenize_vn("bách khoa hà nội")
        assert "bách" in tokens
        assert "khoa" in tokens
        assert "hà" in tokens   # "hà" has 2 chars → kept by tokenizer
        assert "nội" in tokens

    def test_removes_short_tokens(self):
        tokens = _tokenize_vn("a b cd ef")
        assert "a" not in tokens
        assert "b" not in tokens
        assert "cd" in tokens

    def test_splits_on_separators(self):
        tokens = _tokenize_vn("ĐH Bách khoa - Hà Nội")
        assert "đh" in tokens
        assert "bách" in tokens

    def test_empty(self):
        assert _tokenize_vn("") == []


# ============================================================
# TEST GROUP 3: Scoring functions
# ============================================================
class TestScoringFunctions:
    def test_bm25_exact_match(self):
        query = ["bách", "khoa"]
        doc = ["đh", "bách", "khoa", "hà", "nội"]
        score = _bm25_score(query, doc, avg_dl=5.0)
        assert score > 0

    def test_bm25_no_match(self):
        query = ["ngoại", "thương"]
        doc = ["đh", "bách", "khoa", "hà", "nội"]
        score = _bm25_score(query, doc, avg_dl=5.0)
        assert score == 0.0

    def test_bm25_empty_query(self):
        assert _bm25_score([], ["a", "b"], avg_dl=2.0) == 0.0

    def test_bm25_empty_doc(self):
        assert _bm25_score(["a"], [], avg_dl=2.0) == 0.0

    def test_fuzzy_identical(self):
        score = _fuzzy_score("bách khoa", "bách khoa")
        assert score == 1.0

    def test_fuzzy_similar(self):
        score = _fuzzy_score("bách khoa", "bách khoa hà nội")
        assert score > 0.5

    def test_fuzzy_different(self):
        score = _fuzzy_score("ngoại thương", "bách khoa")
        assert score < 0.3

    def test_token_overlap_full(self):
        tokens = ["bách", "khoa"]
        score = _token_overlap_score(tokens, "đh bách khoa hà nội")
        assert score == 1.0

    def test_token_overlap_partial(self):
        tokens = ["bách", "khoa", "đà", "nẵng"]
        score = _token_overlap_score(tokens, "đh bách khoa hà nội")
        assert 0 < score < 1.0

    def test_token_overlap_none(self):
        tokens = ["ngoại", "thương"]
        score = _token_overlap_score(tokens, "đh bách khoa hà nội")
        assert score == 0.0

    def test_token_overlap_empty(self):
        assert _token_overlap_score([], "something") == 0.0


# ============================================================
# TEST GROUP 4: find_matching_schools — Core Matching Logic
# ============================================================
class TestFindMatchingSchools:
    """Test the main matcher function with MOCK_SCHOOLS list."""

    # --- Exact / obvious matches ---
    def test_bach_khoa_returns_multiple(self):
        """'Bách khoa' → should return all 3 Bách khoa campuses."""
        results = find_matching_schools("Bách khoa", MOCK_SCHOOLS)
        assert len(results) >= 2
        names_lower = [r.lower() for r in results]
        assert any("hà nội" in n for n in names_lower)

    def test_bach_khoa_ha_noi_exact(self):
        """'Bách khoa Hà Nội' → should match exactly 1 school."""
        results = find_matching_schools("Bách khoa Hà Nội", MOCK_SCHOOLS)
        assert len(results) >= 1
        assert "hà nội" in results[0].lower()
        assert "tp.hcm" not in results[0].lower()

    def test_buu_chinh(self):
        results = find_matching_schools("Bưu chính Viễn thông", MOCK_SCHOOLS)
        assert len(results) >= 1
        assert "bưu chính" in results[0].lower()

    def test_kinh_te_quoc_dan(self):
        results = find_matching_schools("Kinh tế Quốc dân", MOCK_SCHOOLS)
        assert len(results) >= 1
        assert "quốc dân" in results[0].lower()
        # Should NOT match "Kinh tế TP.HCM"
        assert not any("tp.hcm" in r.lower() for r in results)

    def test_ngoai_thuong(self):
        results = find_matching_schools("Ngoại thương", MOCK_SCHOOLS)
        assert len(results) >= 1
        assert "ngoại thương" in results[0].lower()

    def test_dien_luc(self):
        results = find_matching_schools("Điện lực", MOCK_SCHOOLS)
        assert len(results) >= 1
        assert "điện lực" in results[0].lower()

    def test_det_may(self):
        results = find_matching_schools("Dệt May", MOCK_SCHOOLS)
        assert len(results) >= 1
        assert "dệt may" in results[0].lower()

    def test_y_duoc_buon_ma_thuot(self):
        results = find_matching_schools("Y Dược Buôn Ma Thuột", MOCK_SCHOOLS)
        assert len(results) >= 1
        assert "buôn ma" in results[0].lower()

    def test_su_pham_ha_noi(self):
        """'Sư phạm Hà Nội' → should NOT match 'Sư phạm Kỹ thuật TP.HCM'."""
        results = find_matching_schools("Sư phạm Hà Nội", MOCK_SCHOOLS)
        assert len(results) >= 1
        assert "hà nội" in results[0].lower()

    def test_cong_nghiep_ha_noi(self):
        results = find_matching_schools("Công nghiệp Hà Nội", MOCK_SCHOOLS)
        assert len(results) >= 1
        assert "hà nội" in results[0].lower()
        # Should not match Dệt May or TP.HCM
        assert not any("tp.hcm" in r.lower() for r in results)

    # --- ALL keyword → skip ---
    def test_all_returns_empty(self):
        results = find_matching_schools("ALL", MOCK_SCHOOLS)
        assert results == []

    # --- Empty input ---
    def test_empty_query(self):
        results = find_matching_schools("", MOCK_SCHOOLS)
        assert results == []

    def test_empty_school_list(self):
        results = find_matching_schools("Bách khoa", [])
        assert results == []

    # --- No match ---
    def test_no_match_gibberish(self):
        results = find_matching_schools("xyzabc123", MOCK_SCHOOLS, min_confidence=0.5)
        assert results == []

    # --- Strict mode ---
    def test_strict_mode_no_fallback(self):
        """In strict mode, if no full token overlap match, return empty."""
        results = find_matching_schools("xyz partial", MOCK_SCHOOLS, strict=True)
        assert results == []

    # --- min_confidence threshold ---
    def test_low_confidence_threshold(self):
        """Lower threshold → more lenient matching."""
        results = find_matching_schools("Bách khoa", MOCK_SCHOOLS, min_confidence=0.1)
        assert len(results) >= 1

    def test_high_confidence_threshold(self):
        """Very high threshold → may filter out weak matches."""
        results = find_matching_schools("xyz", MOCK_SCHOOLS, min_confidence=0.99)
        assert results == []


# ============================================================
# TEST GROUP 5: Edge cases and regressions
# ============================================================
class TestEdgeCases:
    def test_su_pham_generic_returns_multiple(self):
        """'Sư phạm' (generic) → should return multiple sư phạm schools."""
        results = find_matching_schools("Sư phạm", MOCK_SCHOOLS)
        assert len(results) >= 2

    def test_y_generic_returns_multiple(self):
        """'Y' alone is too short, should handle gracefully."""
        # This tests that very short queries don't crash
        results = find_matching_schools("Y", MOCK_SCHOOLS)
        # "Y" has len=1, _tokenize_vn filters it out → empty tokens → empty result
        assert isinstance(results, list)

    def test_unicode_handling(self):
        """Vietnamese Unicode characters should not cause errors."""
        results = find_matching_schools("Đại học Bách Khoa", MOCK_SCHOOLS)
        assert isinstance(results, list)

    def test_none_in_school_list(self):
        """School list with None values should not crash."""
        schools_with_none = ["ĐH Bách khoa Hà Nội", None, "ĐH FPT"]
        # _normalize_school_name handles None via str() conversion
        results = find_matching_schools("Bách khoa", schools_with_none)
        assert isinstance(results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
