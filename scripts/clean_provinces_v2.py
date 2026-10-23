# -*- coding: utf-8 -*-
import json
import os

JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "university_provinces.json")

# Bộ quy tắc (Dictionary) dọn dẹp triệt để các lỗi Phường/Xã của API 
NOISE_MAP = {
    "Phường Lê Chân": "Hải Phòng",
    "Phường Thành Sen": "Hà Tĩnh",
    "Phường Tuy Hòa": "Phú Yên",
    "Phường Thuận Thành": "Đà Nẵng", # Đông Á
    "Phường Nam Định": "Nam Định",
    "Phường Đồng Nguyên": "Bắc Ninh",
    "Phường Minh Xuân": "Tuyên Quang",
    "Phường Kinh Bắc": "Bắc Ninh",
    "Bắc Nha Trang": "Khánh Hòa",
    "Phường Mạo Khê": "Quảng Ninh",
    "Phường Tân An": "Đắk Lắk",
    "Phường Lê Thanh Nghị": "Hải Dương",
    "Phường Hoa Lư": "Ninh Bình",
    "Phường Phú Thủy": "Bình Thuận",
    "Phường Tam Kỳ": "Quảng Nam",
    "Phường Thái Bình": "Thái Bình",
    "Phường Phú Xuân": "Thừa Thiên Huế",
    "Phường Trường Vinh": "Nghệ An",
    "Thuận An": "TP.HCM",
    "Dĩ An": "TP.HCM", # Bách Khoa HCM cơ sở Dĩ An, gom về HCM cho học sinh dễ tra
    "Thủ Đức": "TP.HCM",
    "Thành phố Hồ Chí Minh": "TP.HCM",
    "Hồ Chí Minh": "TP.HCM",
}

# Ánh xạ các trường bị "Khác" cụ thể
KHAC_MAP = {
    "Học viện Chính trị Quốc gia HCM": "Hà Nội",
    "Học viện quân y hệ dân sự": "Hà Nội",
    "Học Viện Quân Y - Hệ Quân sự": "Hà Nội",
    "Đại học Quốc tế miền đông": "Bình Dương",
    "Đại học Công nghệ Giao thông Vận tải": "Hà Nội",
    "Đại học Giao thông Vận tải cơ sở 2": "TP.HCM",
    "Học viện Chính trị CAND": "Hà Nội",
    "Đại học Lao động Xã hội CS2": "TP.HCM",
    "Đại học Nông lâm Bắc Giang": "Bắc Giang",
    "Đại học Nông Lâm Bắc Giang": "Bắc Giang",
    "Đại học Lâm nghiệp CS2": "Đồng Nai",
    "Đại học Phòng cháy Chữa cháy CS2": "TP.HCM",
    "Đại học Công nghệ Miền Đông": "Đồng Nai",
    "Trường Đại học Công nghệ miền Đông": "Đồng Nai",
    "Đại học Ngoại thương CS2": "TP.HCM",
    "Đại học Nguyễn Tất Thành CS2": "TP.HCM",
    "Đại học Nội vụ CS2": "TP.HCM",
    "Học viện Phòng không - Không quân DS": "Hà Nội",
    "Học viện Phòng không CS2": "Hà Nội",
    "Học viện Phòng không CS2 DS": "Hà Nội",
    "Đại học Công nghệ GTVT - Phân hiệu Vĩnh Phúc": "Vĩnh Phúc",
    "Sĩ quan Đặc công": "Hà Nội",
    "Đại học Sư phạm Kỹ thuật Hưng Yên": "Hưng Yên",
    "Đại học Sư phạm Kỹ thuật Nam Định": "Nam Định",
    "Đại học Sư phạm Nghệ thuật Trung ương": "Hà Nội",
    "Trường Sĩ Quan Thông Tin - Hệ Dân Sự - Đại Học Thông Tin Liên Lạc": "Khánh Hòa",
    "Trường Sĩ Quan Thông Tin - Hệ Quân sự - Đại Học Thông Tin Liên Lạc": "Khánh Hòa",
    "Đại học Công nghệ và Quản lý Hữu Nghị": "Hà Nội",
    "Trường Sĩ Quan Tăng - Thiết Giáp": "Vĩnh Phúc",
    "Đại học Y Khoa Tokyo Việt Nam": "Hưng Yên",
    "Đại Học Thủy Lợi (Cơ sở 1): Khác": "Hà Nội",
    "Đại Học Thủy Lợi (Cơ sở 1)": "Hà Nội",
    "Đại Học Y Khoa Phạm Ngọc Thạch": "TP.HCM",
    "Đại học Tài Chính Kế Toán": "Quảng Ngãi",
    "Đại học Công Nghệ Đông Á": "Bắc Ninh",
    "Đại Học Sư Phạm Kỹ Thuật Vĩnh Long": "Vĩnh Long",
    "Trường Sĩ Quan Kĩ Thuật Quân Sự - Hệ Quân sự - Đại Học Trần Đại Nghĩa": "TP.HCM",
    "Trường Sĩ Quan Kĩ Thuật Quân Sự - Hệ Dân sự - Đại Học Trần Đại Nghĩa": "TP.HCM",
    "Đại Học Công Nghiệp Việt Trì": "Phú Thọ",
    "Đại Học Xây Dựng Miền Trung": "Phú Yên",
    "Đại Học Y Dược Thái Bình": "Thái Bình",
    "Trường Sĩ Quan Công Binh - Hệ Dân sự - Đại học Ngô Quyền": "Bình Dương",
    "Đại học Văn hóa Nghệ thuật Quân đội": "Hà Nội",
    "Trường ĐH Phennikaa": "Hà Nội",
    "ĐH Kinh tế KT CN": "Hà Nội",
    "ĐH Kinh tế công nghiệp Long An": "Long An",
    "ĐH Kinh tế Lạc Hồng": "Đồng Nai",
    "ĐH Lao động XH (CS phía Nam)": "TP.HCM",
    "Học viện Công nghệ BCVT (Miền Bắc)": "Hà Nội",
    "Học viện Công nghệ BCVT (Miền Nam)": "TP.HCM",
    "Học viện khoa học quân sự hệ dân sự": "Hà Nội",
    "Đại học ngoại ngữ, tin học HCM": "TP.HCM",
    "Đại học Phan Châu Trinh": "Quảng Nam",
    "Đại học Kinh tế và Quản trị kinh doanh": "Thái Nguyên",
    "Đại học Bà Rịa - Vũng Tàu": "Bà Rịa - Vũng Tàu",
}

def clean():
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for uni, prov in data.items():
        # Rule 1: Dọn dẹp Wards/Districts thành Provinces
        if prov in NOISE_MAP:
            data[uni] = NOISE_MAP[prov]
            
        # Rule 2: Gắn Map cứng cho các trường "Khác"
        if uni in KHAC_MAP:
            data[uni] = KHAC_MAP[uni]
            
        # Rule 3: Nhận diện fallback cho các trường ĐHTN
        if data[uni] == "Khác":
            uni_l = uni.lower()
            if "đhtn" in uni_l or "thái nguyên" in uni_l:
                data[uni] = "Thái Nguyên"
            elif "công nghệ thông tin gia định" in uni_l:
                data[uni] = "TP.HCM"
                
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"Data Cleansing v2 Completed. Updated {JSON_PATH}")

if __name__ == "__main__":
    clean()
