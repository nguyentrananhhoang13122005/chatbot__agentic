# -*- coding: utf-8 -*-
import json
import os

JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "university_provinces.json")

def clean():
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for uni, prov in data.items():
        uni_lower = uni.lower()
        
        # Fix specific errors from OpenStreetMap
        if prov == "Thủ Đức" or prov == "Thành phố Hồ Chí Minh" or prov == "Hồ Chí Minh":
            data[uni] = "TP.HCM"
        elif prov == "Nghệ An" and "trà vinh" in uni_lower:
            data[uni] = "Trà Vinh"
        elif "nghệ an" in uni_lower:
            data[uni] = "Nghệ An"
            
        # Fix unmapped "Khác" using extended keywords
        if data[uni] == "Khác":
            if "tphcm" in uni_lower or "tp.hcm" in uni_lower or "hồ chí minh" in uni_lower:
                data[uni] = "TP.HCM"
            elif "đhtn" in uni_lower or "thái nguyên" in uni_lower:
                data[uni] = "Thái Nguyên"
            elif "hà nội" in uni_lower or "hn" in uni_lower.split():
                data[uni] = "Hà Nội"
            elif "đà nẵng" in uni_lower:
                data[uni] = "Đà Nẵng"
            elif "cần thơ" in uni_lower:
                data[uni] = "Cần Thơ"
            elif "huế" in uni_lower:
                data[uni] = "Thừa Thiên Huế"
            elif "thanh hóa" in uni_lower:
                data[uni] = "Thanh Hóa"
                
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"Data Cleansing Completed. Updated {JSON_PATH}")

if __name__ == "__main__":
    clean()
