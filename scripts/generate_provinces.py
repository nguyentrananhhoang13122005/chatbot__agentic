# -*- coding: utf-8 -*-
import os
import json
import time
import requests
import pandas as pd

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "data_diem_chuan_verified.csv")
JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "university_provinces.json")

# Rule 1: Tự điển Hardcoded cho các trường top (Nhanh, không sai lệch)
HARDCODED_MAP = {
    "Đại học Tôn Đức Thắng": "TP.HCM",
    "Học viện Ngân hàng": "Hà Nội",
    "Đại học Ngoại thương": "Hà Nội",
    "Đại học Kinh tế Quốc dân": "Hà Nội",
    "Đại học Công đoàn": "Hà Nội",
    "Đại học Thủy lợi": "Hà Nội",
    "Đại học Thương mại": "Hà Nội",
    "Học viện Báo chí và Tuyên truyền": "Hà Nội",
    "Học viện Tài chính": "Hà Nội",
    "Đại học Xây dựng Hà Nội": "Hà Nội", # just to be safe
    "Đại học Mở TP.HCM": "TP.HCM",
    "Đại học Kinh tế TP.HCM": "TP.HCM",
    "Đại học Luật TP.HCM": "TP.HCM",
    "Đại học Y Dược TP.HCM": "TP.HCM",
    "Đại học Giao thông vận tải TP.HCM": "TP.HCM",
    "Học viện Công nghệ Bưu chính Viễn thông": "Hà Nội",
    "Đại học FPT": "Đa cơ sở",
}

# Rule 2: Nhận diện từ khóa trong tên
KEYWORD_MAP = {
    "Hà Nội": "Hà Nội",
    "Hà Nội": "Hà Nội", # intentional duplicate to handle casing if needed later
    "HN": "Hà Nội",
    "TP.HCM": "TP.HCM",
    "Thành phố Hồ Chí Minh": "TP.HCM",
    "Sài Gòn": "TP.HCM",
    "Đà Nẵng": "Đà Nẵng",
    "Cần Thơ": "Cần Thơ",
    "Huế": "Thừa Thiên Huế",
    "Hải Phòng": "Hải Phòng",
    "Vinh": "Nghệ An",
    "Thái Nguyên": "Thái Nguyên",
    "Nha Trang": "Khánh Hòa",
    "Quy Nhơn": "Bình Định",
    "Đà Lạt": "Lâm Đồng",
    "Tây Nguyên": "Đắk Lắk",
    "Đồng Tháp": "Đồng Tháp",
    "Kiên Giang": "Kiên Giang",
    "An Giang": "An Giang",
    "Trà Vinh": "Trà Vinh",
    "Hồng Đức": "Thanh Hóa",
    "Vinh": "Nghệ An",
    "Đồng Nai": "Đồng Nai",
    "Bình Dương": "Bình Dương",
}

def get_province_offline(uni_name):
    # Ưu tiên 1: Hardcoded
    if uni_name in HARDCODED_MAP:
        return HARDCODED_MAP[uni_name]
    
    # Ưu tiên 2: Keyword
    for kw, prov in KEYWORD_MAP.items():
        if kw.lower() in uni_name.lower():
            return prov
            
    return None

def fetch_province_api(uni_name):
    """Fallback calling OpenStreetMap API"""
    try:
        headers = {"User-Agent": "UniSearchAI/1.0 (tungl)"}
        url = f"https://nominatim.openstreetmap.org/search?q={uni_name}&format=json&addressdetails=1&countrycodes=vn&limit=1"
        res = requests.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            if len(data) > 0:
                address = data[0].get("address", {})
                # Cố gắng lấy Tỉnh/Thành
                prov = address.get("city") or address.get("state") or address.get("province")
                if prov:
                    if "Hà Nội" in prov: return "Hà Nội"
                    if "Hồ Chí Minh" in prov or "Ho Chi Minh" in prov: return "TP.HCM"
                    return prov.replace("Thành phố ", "").replace("Tỉnh ", "")
    except Exception as e:
        print(f"API Error for {uni_name}: {e}")
    
    return "Khác"

def main():
    print("Reading database...")
    df = pd.read_csv(CSV_PATH)
    unique_unis = df["Trường"].dropna().unique()
    
    result = {}
    print(f"Found {len(unique_unis)} unique universities. Generating Master Data...")
    
    for i, uni in enumerate(unique_unis):
        # 1. Thử Offline trước (Tốc độ ánh sáng)
        prov = get_province_offline(uni)
        
        if prov:
            result[uni] = prov
        else:
            # 2. Nếu không ra, gọi API 
            # print removed to avoid unicode encode error on windows console
            api_prov = fetch_province_api(uni)
            result[uni] = api_prov
            time.sleep(1) # Tôn trọng giới hạn rate limit của OSM API
            
    # Ghi file JSON
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully generated Master Data at {JSON_PATH}")

if __name__ == "__main__":
    main()
