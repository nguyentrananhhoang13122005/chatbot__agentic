# -*- coding: utf-8 -*-
"""
GOLD TEST SET — Bộ câu hỏi chuẩn để đo lường chất lượng chatbot sau mỗi lần sửa code.

Mỗi test case gồm:
  - query: Câu hỏi của người dùng
  - category: Loại test (routing | school_match | answer_quality | follow_up)
  - expected_intent: RECOMMENDER hoặc COUNSELOR
  - expected_school_contains: Từ khoá BẮT BUỘC phải có trong tên trường được match
  - expected_school_not_contains: Từ khoá KHÔNG ĐƯỢC có (tránh nhầm trường)
  - expected_answer_contains: Từ khoá BẮT BUỘC phải có trong câu trả lời cuối cùng
  - chat_history: Lịch sử hội thoại (cho test follow-up)
  - difficulty: easy | medium | hard
"""

GOLD_QUERIES = [
    # ============================================================
    # NHÓM 1: ROUTING — Kiểm tra Analyzer phân loại intent đúng
    # ============================================================
    {
        "id": "R01",
        "query": "điểm chuẩn bưu chính viễn thông 2024",
        "category": "routing",
        "expected_intent": "RECOMMENDER",
        "difficulty": "easy",
    },
    {
        "id": "R02",
        "query": "tôi có điểm toán 8, lý 7, hóa 6.5, nên học ngành gì",
        "category": "routing",
        "expected_intent": "RECOMMENDER",
        "difficulty": "medium",
    },
    {
        "id": "R03",
        "query": "hãy đánh giá CV của tôi và tư vấn hướng nghiệp",
        "category": "routing",
        "expected_intent": "COUNSELOR",
        "difficulty": "easy",
    },
    {
        "id": "R04",
        "query": "xin chào",
        "category": "routing",
        "expected_intent": "RECOMMENDER",  # Chit-chat -> mặc định RECOMMENDER
        "difficulty": "easy",
    },

    # ============================================================
    # NHÓM 2: SCHOOL MATCHING — Kiểm tra Hybrid Matcher tìm đúng trường
    # ============================================================
    {
        "id": "S01",
        "query": "điểm chuẩn bưu chính viễn thông",
        "category": "school_match",
        "expected_intent": "RECOMMENDER",
        "expected_school_contains": ["bưu chính"],
        "expected_school_not_contains": [],
        "difficulty": "easy",
    },
    {
        "id": "S02",
        "query": "điểm chuẩn dệt may 2024",
        "category": "school_match",
        "expected_intent": "RECOMMENDER",
        "expected_school_contains": ["dệt may"],
        "expected_school_not_contains": [],
        "difficulty": "easy",
    },
    {
        "id": "S03",
        "query": "điểm chuẩn kinh tế quốc dân",
        "category": "school_match",
        "expected_intent": "RECOMMENDER",
        "expected_school_contains": ["kinh tế", "quốc dân"],
        "expected_school_not_contains": ["quốc gia"],
        "difficulty": "medium",
    },
    {
        "id": "S04",
        "query": "điểm chuẩn HUST 2024",
        "category": "school_match",
        "expected_intent": "RECOMMENDER",
        "expected_school_contains": ["bách khoa"],
        "expected_school_not_contains": ["đà nẵng", "tphcm"],
        "difficulty": "hard",
    },
    {
        "id": "S05",
        "query": "điểm chuẩn y dược buôn ma thuột",
        "category": "school_match",
        "expected_intent": "RECOMMENDER",
        "expected_school_contains": ["y dược", "buôn ma"],
        "expected_school_not_contains": [],
        "difficulty": "easy",
    },
    {
        "id": "S06",
        "query": "các ngành đại học sư phạm hà nội",
        "category": "school_match",
        "expected_intent": "RECOMMENDER",
        "expected_school_contains": ["sư phạm", "hà nội"],
        "expected_school_not_contains": ["tphcm", "tp hcm", "kỹ thuật"],
        "difficulty": "medium",
    },
    {
        "id": "S07",
        "query": "điểm chuẩn đại học điện lực",
        "category": "school_match",
        "expected_intent": "RECOMMENDER",
        "expected_school_contains": ["điện lực"],
        "expected_school_not_contains": [],
        "difficulty": "easy",
    },
    {
        "id": "S08",
        "query": "điểm chuẩn đại học công nghiệp hà nội",
        "category": "school_match",
        "expected_intent": "RECOMMENDER",
        "expected_school_contains": ["công nghiệp"],
        "expected_school_not_contains": ["tphcm", "tp hcm", "vinh"],
        "difficulty": "medium",
    },

    # ============================================================
    # NHÓM 3: ANSWER QUALITY — Kiểm tra câu trả lời cuối cùng có data đúng
    # ============================================================
    {
        "id": "A01",
        "query": "điểm chuẩn ngành y khoa đại học y dược buôn ma thuột 2024",
        "category": "answer_quality",
        "expected_intent": "RECOMMENDER",
        "expected_answer_contains": ["24", "7720101"],  # Điểm 24.00, mã ngành
        "difficulty": "easy",
    },
    {
        "id": "A02",
        "query": "điểm chuẩn ngành công nghệ thông tin PTIT 2024",
        "category": "answer_quality",
        "expected_intent": "RECOMMENDER",
        "expected_answer_contains": ["7480201", "22.82"],  # Mã ngành CNTT + điểm verified
        "difficulty": "medium",
    },
    {
        "id": "A03",
        "query": "các ngành của bưu chính viễn thông",
        "category": "answer_quality",
        "expected_intent": "RECOMMENDER",
        "expected_answer_contains": ["7480201", "7340101"],  # CNTT + QTKD
        "difficulty": "medium",
    },
    {
        "id": "A04",
        "query": "điểm chuẩn ngành dược học y dược buôn ma thuột 2024",
        "category": "answer_quality",
        "expected_intent": "RECOMMENDER",
        "expected_answer_contains": ["21", "7720201"],  # Điểm 21.00, mã ngành dược
        "difficulty": "medium",
    },

    # ============================================================
    # NHÓM 4: FOLLOW-UP — Kiểm tra khả năng hiểu ngữ cảnh hội thoại
    # ============================================================
    {
        "id": "F01",
        "query": "trường này ngành công nghệ may lấy bao nhiêu điểm",
        "category": "follow_up",
        "expected_intent": "RECOMMENDER",
        "expected_school_contains": ["dệt may"],
        "chat_history": [
            {"role": "user", "content": "điểm chuẩn dệt may"},
            {"role": "assistant", "content": "Đây là điểm ĐH Công nghiệp Dệt May Hà Nội..."},
        ],
        "difficulty": "hard",
    },
    {
        "id": "F02",
        "query": "ngành marketing lấy bao nhiêu",
        "category": "follow_up",
        "expected_intent": "RECOMMENDER",
        "expected_school_contains": ["bưu chính"],
        "expected_answer_contains": ["7340115"],  # Mã ngành Marketing
        "chat_history": [
            {"role": "user", "content": "điểm chuẩn PTIT 2024"},
            {"role": "assistant", "content": "Đây là điểm Học viện Bưu chính Viễn thông..."},
        ],
        "difficulty": "hard",
    },
]
