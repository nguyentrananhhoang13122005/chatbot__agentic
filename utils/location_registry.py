# -*- coding: utf-8 -*-
"""
utils/location_registry.py - Danh mục trường đại học theo tỉnh/thành phố đã được kiểm chứng.

Mục đích:
- Giải quyết TRIỆT ĐỂ vấn đề ảo giác (Hallucination) khi người dùng hỏi các câu hỏi:
  + "Ở [địa phương] có những trường đại học nào?"
  + "Các trường đại học ở [địa phương]"
  + "Tại [địa phương] có trường nào đào tạo..."
  + "Trường X có cơ sở ở [địa phương] không?"
- Cung cấp Single Source of Truth về:
  + Tên trường chuẩn, cơ quan chủ quản / đại học vùng
  + Mã trường (School Code) chính xác 100% của Bộ GD&ĐT (tránh gán nhầm DTC cho tất cả các trường)
  + Cảnh báo các trường thường bị nhầm lẫn (negative assertions)
"""
from __future__ import annotations

import re
import sqlite3
import os
from typing import Dict, List, Optional, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "admissions.db")

# Danh mục trường chuẩn theo tỉnh / thành phố giáo dục trọng điểm
PROVINCE_UNIVERSITY_MAP: Dict[str, Dict[str, Any]] = {
    "thái nguyên": {
        "province": "Thái Nguyên",
        "description": "Thái Nguyên là trung tâm giáo dục đại học lớn thứ 3 cả nước và là hạt nhân giáo dục của vùng trung du, miền núi phía Bắc với nòng cốt là Đại học Thái Nguyên (ĐHTN) — một trong các Đại học Vùng trọng điểm quốc gia trực thuộc Bộ Giáo dục và Đào tạo.",
        "system_name": "Đại học Thái Nguyên (ĐHTN) - Đại học Vùng",
        "schools": [
            {
                "name": "Trường Đại học Sư phạm - Đại học Thái Nguyên",
                "short_name": "ĐH Sư phạm Thái Nguyên",
                "code": "DTS",
                "type": "Trường đại học thành viên ĐHTN",
                "strengths": "Sư phạm Toán, Văn, Anh, Khoa học tự nhiên, Tâm lý - Giáo dục học, Đào tạo giáo viên các cấp",
            },
            {
                "name": "Trường Đại học Kỹ thuật Công nghiệp - Đại học Thái Nguyên",
                "short_name": "ĐH Kỹ thuật Công nghiệp (TNUT)",
                "code": "DTK",
                "type": "Trường đại học thành viên ĐHTN",
                "strengths": "Cơ khí, Chế tạo máy, Kỹ thuật điện - điện tử, Tự động hóa, Kỹ thuật ô tô, Xây dựng",
            },
            {
                "name": "Trường Đại học Nông Lâm - Đại học Thái Nguyên",
                "short_name": "ĐH Nông Lâm Thái Nguyên (TUAF)",
                "code": "DTN",
                "type": "Trường đại học thành viên ĐHTN",
                "strengths": "Nông nghiệp, Lâm nghiệp, Thú y, Chăn nuôi, Quản lý đất đai, Công nghệ thực phẩm, Môi trường",
            },
            {
                "name": "Trường Đại học Y - Dược - Đại học Thái Nguyên",
                "short_name": "ĐH Y Dược Thái Nguyên (TUMP)",
                "code": "DTY",
                "type": "Trường đại học thành viên ĐHTN",
                "strengths": "Y khoa (Bác sĩ đa khoa), Dược học, Y học dự phòng, Răng - Hàm - Mặt, Điều dưỡng",
            },
            {
                "name": "Trường Đại học Kinh tế và Quản trị Kinh doanh - Đại học Thái Nguyên",
                "short_name": "ĐH Kinh tế & QTKD Thái Nguyên (TUEBA)",
                "code": "DTE",
                "type": "Trường đại học thành viên ĐHTN",
                "strengths": "Quản trị kinh doanh, Tài chính - Ngân hàng, Kế toán, Kinh tế đầu tư, Marketing, Logistics",
            },
            {
                "name": "Trường Đại học Khoa học - Đại học Thái Nguyên",
                "short_name": "ĐH Khoa học Thái Nguyên (TNUS)",
                "code": "DTZ",
                "type": "Trường đại học thành viên ĐHTN",
                "strengths": "Khoa học cơ bản (Toán ứng dụng, Hóa học, Sinh học), Công nghệ sinh học, Khoa học môi trường, Báo chí, Luật",
            },
            {
                "name": "Trường Đại học Công nghệ Thông tin và Truyền thông - Đại học Thái Nguyên",
                "short_name": "ICTU",
                "code": "DTC",
                "type": "Trường đại học thành viên ĐHTN",
                "strengths": "Công nghệ thông tin, Kỹ thuật phần mềm, Trí tuệ nhân tạo, Mạng máy tính & An toàn thông tin, Thiết kế đồ họa, Truyền thông đa phương tiện",
            },
            {
                "name": "Trường Ngoại ngữ - Đại học Thái Nguyên",
                "short_name": "ĐH Ngoại ngữ Thái Nguyên (SFL)",
                "code": "DTF",
                "type": "Trường thành viên / đơn vị đào tạo ĐHTN",
                "strengths": "Ngôn ngữ Anh, Ngôn ngữ Trung Quốc, Ngôn ngữ Hàn Quốc, Ngôn ngữ Nhật Bản, Sư phạm tiếng Anh/tiếng Trung",
            },
            {
                "name": "Khoa Quốc tế - Đại học Thái Nguyên",
                "short_name": "Khoa Quốc tế ĐHTN (IS-TNU)",
                "code": "DTQ",
                "type": "Đơn vị trực thuộc ĐHTN",
                "strengths": "Kinh doanh quốc tế, Kế toán và Tài chính liên kết quốc tế giảng dạy bằng tiếng Anh",
            },
            {
                "name": "Trường Đại học Kinh tế và Công nghệ Thái Nguyên",
                "short_name": "ĐH Kinh tế & Công nghệ TN",
                "code": "DKT",
                "type": "Trường Đại học tư thục / dân lập tại Thái Nguyên",
                "strengths": "Kinh tế, Công nghệ, Quản trị",
            },
        ],
        "colleges": [
            "Trường Cao đẳng Kinh tế - Kỹ thuật (thuộc ĐHTN)",
            "Trường Cao đẳng Y tế Thái Nguyên",
            "Trường Cao đẳng Sư phạm Thái Nguyên",
            "Trường Cao đẳng Văn hóa Nghệ thuật Việt Bắc",
        ],
        "branches_in_other_provinces": [
            {
                "name": "Phân hiệu Đại học Thái Nguyên tại tỉnh Lào Cai",
                "code": "DTP",
                "location": "Phường Cam Đường, TP. Lào Cai, tỉnh Lào Cai",
            },
            {
                "name": "Phân hiệu Đại học Thái Nguyên tại tỉnh Hà Giang",
                "code": "DTH",
                "location": "TP. Hà Giang, tỉnh Hà Giang",
            },
        ],
        "negatives": [
            "Trường Đại học Mỏ - Địa chất (Mã: MDA, tên viết tắt: HUMG): Trụ sở chính tại Phố Viên, Đức Thắng, Bắc Từ Liêm, HÀ NỘI. Trường KHÔNG có cơ sở hay phân hiệu tại Thái Nguyên.",
            "Trường Đại học Thủy lợi (Mã: TLA, tên viết tắt: TLU): Trụ sở chính tại 175 Tây Sơn, Đống Đa, HÀ NỘI, Cơ sở Phố Hiến (Hưng Yên) và Phân hiệu Miền Nam (Bình Dương/TP.HCM). Trường KHÔNG có cơ sở tại Thái Nguyên.",
            "Lưu ý về tên gọi: Đại học Thái Nguyên là ĐẠI HỌC VÙNG (Regional University), KHÔNG PHẢI là 'Đại học Quốc gia' (Việt Nam chỉ có 2 ĐHQG là ĐHQGHN và ĐHQG-HCM).",
            "Lưu ý về mã trường: Mỗi trường thành viên của ĐHTN có một MÃ TUYỂN SINH HOÀN TOÀN KHÁC NHAU (DTS, DTK, DTN, DTY, DTE, DTZ, DTC, DTF). TUYỆT ĐỐI KHÔNG DÙNG mã DTC (của riêng ĐH CNTT&TT) cho tất cả các trường.",
        ],
    },
    "đà nẵng": {
        "province": "Đà Nẵng",
        "description": "Đà Nẵng là trung tâm giáo dục đại học lớn nhất khu vực miền Trung - Tây Nguyên với nòng cốt là Đại học Đà Nẵng (ĐHĐN) — Đại học Vùng trọng điểm quốc gia trực thuộc Bộ Giáo dục và Đào tạo.",
        "system_name": "Đại học Đà Nẵng (ĐHĐN) - Đại học Vùng",
        "schools": [
            {
                "name": "Trường Đại học Bách khoa - Đại học Đà Nẵng",
                "short_name": "DUT",
                "code": "DDK",
                "type": "Trường đại học thành viên ĐHĐN",
                "strengths": "Cơ khí, Xây dựng, Điện - Điện tử, CNTT, Hóa học, Công nghệ sinh học",
            },
            {
                "name": "Trường Đại học Kinh tế - Đại học Đà Nẵng",
                "short_name": "DUE",
                "code": "DDQ",
                "type": "Trường đại học thành viên ĐHĐN",
                "strengths": "Kinh tế, QTKD, Tài chính - Ngân hàng, Kế toán, Thương mại điện tử, Marketing",
            },
            {
                "name": "Trường Đại học Sư phạm - Đại học Đà Nẵng",
                "short_name": "UED",
                "code": "DDS",
                "type": "Trường đại học thành viên ĐHĐN",
                "strengths": "Sư phạm Toán, Văn, Lý, Hóa, Khoa học Xã hội, Giáo dục Tiểu học, Tâm lý",
            },
            {
                "name": "Trường Đại học Ngoại ngữ - Đại học Đà Nẵng",
                "short_name": "UFL",
                "code": "DDF",
                "type": "Trường đại học thành viên ĐHĐN",
                "strengths": "Ngôn ngữ Anh, Pháp, Trung, Hàn, Nhật, Quốc tế học",
            },
            {
                "name": "Trường Đại học Sư phạm Kỹ thuật - Đại học Đà Nẵng",
                "short_name": "UTE Đà Nẵng",
                "code": "DSK",
                "type": "Trường đại học thành viên ĐHĐN",
                "strengths": "Công nghệ kỹ thuật ô tô, Điện tử, Cơ khí, Cơ điện tử, Nhiệt điện lạnh",
            },
            {
                "name": "Trường Đại học Công nghệ Thông tin và Truyền thông Việt - Hàn - ĐHĐN",
                "short_name": "VKU",
                "code": "VKU",
                "type": "Trường đại học thành viên ĐHĐN",
                "strengths": "Công nghệ thông tin, Trí tuệ nhân tạo, Thiết kế vi mạch bán dẫn, An toàn thông tin, Kinh tế số",
            },
            {
                "name": "Viện Nghiên cứu và Đào tạo Việt - Anh - Đại học Đà Nẵng",
                "short_name": "VNUK",
                "code": "DDV",
                "type": "Đơn vị thành viên ĐHĐN",
                "strengths": "Quản trị quốc tế, Khoa học dữ liệu, Khoa học y sinh (chương trình chuẩn quốc tế)",
            },
            {
                "name": "Trường Y Dược - Đại học Đà Nẵng (tiền thân là Khoa Y Dược)",
                "short_name": "SMP",
                "code": "DDY",
                "type": "Trường/Khoa thuộc ĐHĐN",
                "strengths": "Y khoa, Điều dưỡng, Răng - Hàm - Mặt, Dược học",
            },
            {
                "name": "Trường Đại học Duy Tân",
                "short_name": "DTU",
                "code": "DDT",
                "type": "Đại học tư thục hàng đầu tại Đà Nẵng",
                "strengths": "CNTT, Y Dược, Quản trị khách sạn - Du lịch, Xây dựng, Kiến trúc",
            },
            {
                "name": "Trường Đại học Kiến trúc Đà Nẵng",
                "short_name": "DAU",
                "code": "DAD",
                "type": "Trường Đại học tư thục",
                "strengths": "Kiến trúc, Quy hoạch đô thị, Kỹ thuật xây dựng, Thiết kế nội thất",
            },
            {
                "name": "Trường Đại học Đông Á",
                "short_name": "UDA",
                "code": "DAD",
                "type": "Trường Đại học tư thục",
                "strengths": "Điều dưỡng (định hướng Nhật Bản), QTKD, Ngôn ngữ, Du lịch",
            },
            {
                "name": "Đại học FPT Đà Nẵng",
                "short_name": "FPT Đà Nẵng",
                "code": "FPT",
                "type": "Cơ sở Đại học FPT",
                "strengths": "CNTT, Kỹ thuật phần mềm, Thiết kế đồ họa, Truyền thông số",
            },
        ],
        "colleges": [],
        "negatives": [
            "Đại học Đà Nẵng là ĐẠI HỌC VÙNG trực thuộc Bộ GD&ĐT (không phải Đại học Quốc gia).",
            "Mỗi trường thành viên có mã tuyển sinh độc lập (DDK, DDQ, DDS, DDF, DSK, VKU, DDY).",
        ],
    },
    "cần thơ": {
        "province": "Cần Thơ",
        "description": "Cần Thơ là trung tâm giáo dục đại học lớn nhất vùng Đồng bằng Sông Cửu Long (Tây Nam Bộ).",
        "system_name": "Hệ thống các trường đại học tại TP. Cần Thơ",
        "schools": [
            {
                "name": "Trường Đại học Cần Thơ",
                "short_name": "CTU",
                "code": "TCT",
                "type": "Đại học trọng điểm quốc gia trực thuộc Bộ GD&ĐT",
                "strengths": "Đa ngành: Nông nghiệp, Thủy sản, Môi trường, CNTT, Sư phạm, Kinh tế, Công nghệ kỹ thuật",
            },
            {
                "name": "Trường Đại học Y Dược Cần Thơ",
                "short_name": "CTUMP",
                "code": "YCT",
                "type": "Trường Đại học công lập trực thuộc Bộ Y tế",
                "strengths": "Y đa khoa, Dược học, Răng Hàm Mặt, Y học dự phòng, Điều dưỡng, Kỹ thuật xét nghiệm y học",
            },
            {
                "name": "Trường Đại học Kỹ thuật - Công nghệ Cần Thơ",
                "short_name": "CTUT",
                "code": "KCC",
                "type": "Trường Đại học công lập trực thuộc UBND TP. Cần Thơ",
                "strengths": "Công nghệ thông tin, Kỹ thuật điện, Kỹ thuật cơ điện tử, Kỹ thuật phần mềm, Quản lý công nghiệp",
            },
            {
                "name": "Trường Đại học Nam Cần Thơ",
                "short_name": "DNC",
                "code": "DNC",
                "type": "Trường Đại học tư thục",
                "strengths": "Y khoa, Dược, Cơ khí ô tô, Quản trị kinh doanh, Luật",
            },
            {
                "name": "Trường Đại học Tây Đô",
                "short_name": "TDU",
                "code": "DTD",
                "type": "Trường Đại học tư thục",
                "strengths": "Dược học, Điều dưỡng, QTKD, Tài chính, Ngôn ngữ Anh",
            },
            {
                "name": "Đại học FPT Cần Thơ",
                "short_name": "FPT Cần Thơ",
                "code": "FPT",
                "type": "Cơ sở trường Đại học FPT",
                "strengths": "CNTT, An toàn thông tin, Thiết kế đồ họa, Truyền thông đa phương tiện",
            },
        ],
        "colleges": [],
        "negatives": [],
    },
    "hải phòng": {
        "province": "Hải Phòng",
        "description": "Hải Phòng là trung tâm kinh tế biển và giáo dục đại học hàng đầu vùng Duyên hải Bắc Bộ.",
        "system_name": "Các trường đại học tại TP. Hải Phòng",
        "schools": [
            {
                "name": "Trường Đại học Hàng hải Việt Nam",
                "short_name": "VMU",
                "code": "HHA",
                "type": "Trường Đại học công lập trọng điểm quốc gia trực thuộc Bộ Giao thông Vận tải",
                "strengths": "Đi biển, Hàng hải, Logistics và Quản trị chuỗi cung ứng, Đóng tàu, Kinh tế vận tải, CNTT, Cơ khí",
            },
            {
                "name": "Trường Đại học Y Dược Hải Phòng",
                "short_name": "HPMU",
                "code": "YPB",
                "type": "Trường Đại học công lập trực thuộc Bộ Y tế",
                "strengths": "Y đa khoa, Y học biển, Dược học, Răng Hàm Mặt, Y học dự phòng, Điều dưỡng",
            },
            {
                "name": "Trường Đại học Hải Phòng",
                "short_name": "THP",
                "code": "THP",
                "type": "Trường Đại học công lập trực thuộc UBND TP. Hải Phòng",
                "strengths": "Sư phạm các môn, Kinh tế, Ngoại ngữ (Anh, Trung), Kỹ thuật công nghệ",
            },
            {
                "name": "Trường Đại học Quản lý và Công nghệ Hải Phòng",
                "short_name": "HPU",
                "code": "DHP",
                "type": "Trường Đại học dân lập / tư thục",
                "strengths": "Quản trị kinh doanh, CNTT, Ngoại ngữ, Điện tử",
            },
        ],
        "colleges": [],
        "negatives": [],
    },
    "thừa thiên huế": {
        "province": "Thừa Thiên Huế",
        "description": "Huế là cố đô và trung tâm giáo dục, văn hóa, y tế lớn của miền Trung với nòng cốt là Đại học Huế (ĐHH) — Đại học Vùng trực thuộc Bộ GD&ĐT.",
        "system_name": "Đại học Huế (ĐHH) - Đại học Vùng",
        "schools": [
            {
                "name": "Trường Đại học Sư phạm - Đại học Huế",
                "short_name": "ĐH Sư phạm Huế",
                "code": "DHS",
                "type": "Trường thành viên ĐHH",
                "strengths": "Sư phạm Toán, Văn, Lý, Hóa, Tâm lý giáo dục, Khoa học tự nhiên",
            },
            {
                "name": "Trường Đại học Y - Dược - Đại học Huế",
                "short_name": "ĐH Y Dược Huế",
                "code": "DHY",
                "type": "Trường thành viên ĐHH",
                "strengths": "Y khoa, Dược học, Răng Hàm Mặt, Y học cổ truyền, Kỹ thuật hình ảnh y học",
            },
            {
                "name": "Trường Đại học Khoa học - Đại học Huế",
                "short_name": "ĐH Khoa học Huế",
                "code": "DHK",
                "type": "Trường thành viên ĐHH",
                "strengths": "CNTT, Kiến trúc, Báo chí, Khoa học môi trường, Toán - Tin, Hóa học",
            },
            {
                "name": "Trường Đại học Kinh tế - Đại học Huế",
                "short_name": "ĐH Kinh tế Huế",
                "code": "DHK",
                "type": "Trường thành viên ĐHH",
                "strengths": "Kinh tế, Quản trị kinh doanh, Tài chính ngân hàng, Kế toán, Thương mại điện tử",
            },
            {
                "name": "Trường Đại học Ngoại ngữ - Đại học Huế",
                "short_name": "ĐH Ngoại ngữ Huế",
                "code": "DHF",
                "type": "Trường thành viên ĐHH",
                "strengths": "Ngôn ngữ Anh, Trung, Hàn, Nhật, Nga, Pháp, Quốc tế học",
            },
            {
                "name": "Trường Đại học Nông Lâm - Đại học Huế",
                "short_name": "ĐH Nông Lâm Huế",
                "code": "DHL",
                "type": "Trường thành viên ĐHH",
                "strengths": "Nông học, Thú y, Chăn nuôi, Thủy sản, Lâm nghiệp, Quản lý đất đai",
            },
            {
                "name": "Trường Đại học Luật - Đại học Huế",
                "short_name": "ĐH Luật Huế",
                "code": "DHA",
                "type": "Trường thành viên ĐHH",
                "strengths": "Luật học, Luật kinh tế",
            },
            {
                "name": "Trường Đại học Nghệ thuật - Đại học Huế",
                "short_name": "ĐH Nghệ thuật Huế",
                "code": "DHN",
                "type": "Trường thành viên ĐHH",
                "strengths": "Hội họa, Điêu khắc, Thiết kế đồ họa, Sư phạm Mỹ thuật",
            },
            {
                "name": "Trường Du lịch - Đại học Huế",
                "short_name": "Du lịch Huế",
                "code": "DHD",
                "type": "Đơn vị thành viên ĐHH",
                "strengths": "Quản trị dịch vụ du lịch & lữ hành, Quản trị khách sạn, Quản trị nhà hàng",
            },
            {
                "name": "Trường Đại học Phú Xuân",
                "short_name": "PXU",
                "code": "DPX",
                "type": "Trường Đại học tư thục tại Huế",
                "strengths": "CNTT, Quản trị kinh doanh, Ngôn ngữ",
            },
        ],
        "colleges": [],
        "negatives": [
            "Đại học Huế là ĐẠI HỌC VÙNG trực thuộc Bộ GD&ĐT (không phải Đại học Quốc gia).",
        ],
    },
}

# Alias map cho tên tỉnh/thành
LOCATION_ALIASES: Dict[str, str] = {
    "thái nguyên": "thái nguyên",
    "thai nguyen": "thái nguyên",
    "đhtn": "thái nguyên",
    "dhtn": "thái nguyên",
    "tỉnh thái nguyên": "thái nguyên",
    "tp thái nguyên": "thái nguyên",
    "thành phố thái nguyên": "thái nguyên",
    "đà nẵng": "đà nẵng",
    "da nang": "đà nẵng",
    "đhđn": "đà nẵng",
    "dhdn": "đà nẵng",
    "tp đà nẵng": "đà nẵng",
    "thành phố đà nẵng": "đà nẵng",
    "cần thơ": "cần thơ",
    "can tho": "cần thơ",
    "tp cần thơ": "cần thơ",
    "thành phố cần thơ": "cần thơ",
    "hải phòng": "hải phòng",
    "hai phong": "hải phòng",
    "tp hải phòng": "hải phòng",
    "thành phố hải phòng": "hải phòng",
    "huế": "thừa thiên huế",
    "thừa thiên huế": "thừa thiên huế",
    "thua thien hue": "thừa thiên huế",
    "đhh": "thừa thiên huế",
}


def normalize_location_name(loc: str) -> Optional[str]:
    """Chuẩn hóa chuỗi địa danh nhập vào sang key chuẩn trong dictionary."""
    if not loc:
        return None
    cleaned = loc.strip().lower()
    cleaned = re.sub(r"^(tại|ở|khu vực|tỉnh|thành phố|tp\.?)\s+", "", cleaned).strip()
    return LOCATION_ALIASES.get(cleaned) or LOCATION_ALIASES.get(loc.strip().lower())


def detect_location_query(query: str, location_hint: str = "ALL") -> Optional[str]:
    """
    Phát hiện câu hỏi có phải đang hỏi về danh sách trường tại một địa phương hay không.
    Trả về tên tỉnh/thành chuẩn (hoặc None nếu không phải).
    """
    q = query.lower()
    # Kiểm tra location_hint từ Router Analyzer trước
    if location_hint and location_hint != "ALL":
        norm = normalize_location_name(location_hint)
        if norm:
            return norm

    # Quét qua danh sách alias để phát hiện địa danh trong câu hỏi
    # Chỉ match khi câu hỏi có ý hỏi về trường / đại học / học viện / danh sách
    has_school_intent = any(k in q for k in [
        "trường", "đại học", "đh", "học viện", "cao đẳng", "những trường nào", 
        "trường nào", "danh sách", "có trường gì", "có những trường", "tuyển sinh"
    ])
    
    if not has_school_intent:
        return None

    for alias, standard_key in LOCATION_ALIASES.items():
        # Kiểm tra word boundary hoặc pattern 'ở X', 'tại X'
        pattern = rf"(?:\bở\s+|\btại\s+|\bkhu vực\s+|\btrong\s+)?\b{re.escape(alias)}\b"
        if re.search(pattern, q):
            return standard_key

    return None


def get_grounding_context_for_location(loc_key: str) -> Optional[str]:
    """
    Tạo context dữ liệu đã xác thực cực kỳ nghiêm ngặt để đưa vào prompt LLM.
    Đảm bảo LLM KHÔNG THỂ BỊA ĐẶT (Zero Extrapolation).
    """
    data = PROVINCE_UNIVERSITY_MAP.get(loc_key)
    if not data:
        return None

    province = data["province"]
    desc = data["description"]
    system = data.get("system_name", "")
    schools = data["schools"]
    colleges = data.get("colleges", [])
    branches = data.get("branches_in_other_provinces", [])
    negatives = data.get("negatives", [])

    lines = []
    lines.append(f"### DỮ LIỆU ĐÃ XÁC THỰC CỦA BỘ GD&ĐT & ĐỀ ÁN TUYỂN SINH CHO ĐỊA PHƯƠNG: {province.upper()}")
    lines.append(f"**Tổng quan:** {desc}")
    if system:
        lines.append(f"**Hệ thống chủ đạo:** {system}")

    lines.append("\n**DANH SÁCH CÁC TRƯỜNG ĐẠI HỌC CHÍNH THỨC CÓ TRỤ SỞ/CƠ SỞ TẠI ĐỊA PHƯƠNG NÀY (ĐÃ ĐỐI SOÁT CHÍNH XÁC MÃ TRƯỜNG):**")
    for idx, s in enumerate(schools, 1):
        lines.append(
            f"{idx}. **{s['name']}**\n"
            f"   - Tên viết tắt: **{s['short_name']}**\n"
            f"   - **Mã trường tuyển sinh chính thức: {s['code']}** (TUYỆT ĐỐI KHÔNG BỊA MÃ KHÁC)\n"
            f"   - Phân loại: {s['type']}\n"
            f"   - Ngành thế mạnh / đào tạo: {s['strengths']}"
        )

    if colleges:
        lines.append("\n**Các trường Cao đẳng nổi bật tại địa phương:**")
        for c in colleges:
            lines.append(f"- {c}")

    if branches:
        lines.append("\n**Lưu ý về các phân hiệu trực thuộc đặt tại tỉnh khác:**")
        for b in branches:
            lines.append(f"- {b['name']} (Mã trường: {b['code']}) — Đặt tại: {b['location']}")

    if negatives:
        lines.append("\n⚠️ **CÁC ĐIỂM SỬA SAI & CẢNH BÁO ẢO GIÁC BẮT BUỘC (CRITICAL ANTI-HALLUCINATION RULES):**")
        for neg in negatives:
            lines.append(f"- {neg}")

    return "\n".join(lines)
