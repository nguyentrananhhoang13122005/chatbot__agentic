# -*- coding: utf-8 -*-
"""
Bảng bí danh trường (alias) dùng chung cho mọi nơi so khớp tên trường.

Vấn đề thực tế: cùng một trường xuất hiện dưới nhiều tên khác nhau giữa các nguồn dữ liệu
(vd. "Học viện Công nghệ Bưu chính Viễn thông" ở DATS, "Học viện Công nghệ BCVT (Miền Bắc)" ở bảng điểm chuẩn),
và người dùng gõ viết tắt (PTIT, HUST, NEU ...). Cả TÊN TRƯỜNG lẫn CÂU HỎI đều được đưa qua cùng một hàm
`apply_aliases` trước khi so khớp, nên hai bên luôn gặp nhau ở một dạng chuẩn.

Chỉ liệt kê các bí danh CHẮC CHẮN. Tên mơ hồ ("Bách khoa", "Kinh tế") cố ý KHÔNG có ở đây: hệ thống phải hỏi lại
người dùng thay vì đoán.
"""
from __future__ import annotations

import re

# (mẫu regex trên văn bản đã lowercase, dạng chuẩn). Thứ tự quan trọng: mẫu dài trước mẫu ngắn.
_ALIAS_RULES: list[tuple[str, str]] = [
    (r"\bbưu chính,? viễn thông\b", "bcvt"),
    (r"\bbưu chính\b", "bcvt"),
    (r"\bptit\b", "bcvt"),
    (r"\bhust\b", "bách khoa hà nội"),
    (r"\bneu\b", "kinh tế quốc dân"),
    (r"\bftu\b", "ngoại thương"),
    (r"\buet\b", "công nghệ đại học quốc gia hà nội"),
    (r"\bhcmut\b", "bách khoa đại học quốc gia tp hồ chí minh"),
    (r"\bbku\b", "bách khoa đại học quốc gia tp hồ chí minh"),
    (r"\bhcmus\b", "khoa học tự nhiên đại học quốc gia tp hồ chí minh"),
    (r"\buit\b", "công nghệ thông tin đại học quốc gia tp hồ chí minh"),
    (r"\bkhtn\b", "khoa học tự nhiên"),
    (r"\bkhxh\s*&?\s*nv\b", "khoa học xã hội và nhân văn"),
    (r"\bspkt\b", "sư phạm kỹ thuật"),
    (r"\bictu\b", "công nghệ thông tin và truyền thông thái nguyên"),
    (r"\bdtc\b", "công nghệ thông tin và truyền thông thái nguyên"),
    (r"\bđh cntt &? tt thái nguyên\b", "công nghệ thông tin và truyền thông thái nguyên"),
    (r"\bđhqg\b", "đại học quốc gia"),
    (r"\bqghn\b", "đại học quốc gia hà nội"),
]

_COMPILED = [(re.compile(pattern), repl) for pattern, repl in _ALIAS_RULES]


def apply_aliases(text: str) -> str:
    """Đưa các cách gọi khác nhau của cùng một trường về một dạng chuẩn. Đầu vào nên đã lowercase."""
    out = text
    for pattern, repl in _COMPILED:
        out = pattern.sub(repl, out)
    return re.sub(r"\s+", " ", out).strip()
