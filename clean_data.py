# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import re

def clean_school_name(name):
    """
    Làm sạch tên trường từ dữ liệu OCR thô:
    - Bỏ số thứ tự ở đầu (VD: '33. ĐH Bách khoa' -> 'ĐH Bách khoa')
    - Bỏ năm ở cuối (VD: 'ĐH Bách khoa 2024' -> 'ĐH Bách khoa')
    - Chuẩn hóa khoảng trắng
    - Capitalize / Title case cho đẹp
    """
    if not isinstance(name, str) or pd.isna(name):
        return name
        
    name = str(name).strip()
    
    # 1. Bỏ số thứ tự đầu (VD: '1.', '247.', '127.2025 ', '249-')
    # Bắt đầu bằng 1 hoặc nhiều số, tiếp theo có thể là dấu chấm, gạch ngang, hoặc không gian
    name = re.sub(r'^\d+[\.\-\s]+(?:\d{4}\s+)?', '', name)
    
    # Xử lý trường hợp như "2025. Đề án tuyển sinh năm 2025" 
    name = re.sub(r'^\d{4}\.?\s*(?:Đề án.*|Tuyển sinh.*)?', '', name, flags=re.IGNORECASE)
    
    # Bỏ chữ "Đề án Tuyển sinh" nếu có ở đầu
    name = re.sub(r'^(?:Đề án|Tuyển sinh)[\s\w]*\s+', '', name, flags=re.IGNORECASE)
    
    # 2. Bỏ năm ở cuối (VD: '... 2024', '... 2025')
    name = re.sub(r'\s*\d{4}\s*$', '', name)
    name = re.sub(r'\s*\-\s*\d{4}\s*$', '', name)
    
    # Bỏ hậu tố lạ (VD: '-QHI', '-BVU...')
    name = re.sub(r'\-[A-Z0-9]+$', '', name)
    
    # 3. Chuẩn hóa khoảng trắng
    name = re.sub(r'\s+', ' ', name)
    name = name.strip()
    
    # 4. Viết hoa chữ cái đầu mỗi từ cho đẹp (tránh việc chữ "Hà nội" vs "Hà Nội")
    # Tự động uppercase những từ như ĐH, HV, TPHCM
    words = name.split()
    fixed_words = []
    for w in words:
        wl = w.lower()
        if wl in ['đh', 'hv', 'đhqg', 'tphcm', 'hcm', 'hn', 'vn', 'qhi']:
            fixed_words.append(w.upper())
        elif wl in ['và', 'của', 'tại', 'về']:
            fixed_words.append(wl)
        else:
            fixed_words.append(w.capitalize())
            
    name = ' '.join(fixed_words)
    return name

print("Đang đọc file gốc...")
df = pd.read_csv('data/data_tuyensinh.csv', low_memory=False)

print(f"Tổng số dòng: {len(df)}")
original_schools = df['Tên Trường'].dropna().unique().tolist()
print(f"Số lượng tên trường gốc: {len(original_schools)}")

print("Đang làm sạch dữ liệu...")
df['Tên Trường'] = df['Tên Trường'].apply(clean_school_name)

# Loại bỏ các dòng mà Tên Trường rỗng sau khi clean
df = df[df['Tên Trường'].astype(bool)]

new_schools = df['Tên Trường'].dropna().unique().tolist()
print(f"Số lượng tên trường sau khi gộp chuẩn hóa: {len(new_schools)} (giảm {(1 - len(new_schools)/len(original_schools))*100:.1f}%)")

output_path = 'data/data_tuyensinh_clean.csv'
df.to_csv(output_path, index=False, encoding='utf-8')
print(f"✅ Đã lưu file sạch vào: {output_path}")

print("\n--- SAMPLE TRƯỜNG ĐÃ LÀM SẠCH ---")
for s in sorted(new_schools)[:20]:
    print(f"  {s}")
