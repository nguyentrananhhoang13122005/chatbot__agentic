import sys
import os
import shutil
import re
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("1. Đang sao lưu file gốc...")
    original_path = 'data/data_tuyensinh.csv'
    backup_path = 'data/data_tuyensinh_backup.csv'
    
    if not os.path.exists(original_path):
        print(f"Lỗi: Không tìm thấy file {original_path}")
        return

    if not os.path.exists(backup_path):
        shutil.copy2(original_path, backup_path)
        print("   Đã tạo bản backup: data_tuyensinh_backup.csv")

    print("2. Đang load dữ liệu...")
    df = pd.read_csv(original_path, low_memory=False).fillna("")

    if df.empty:
        print("File CSV trống.")
        return

    last_col = df.columns[-1]
    school_col_idx = df.columns.get_loc('Tên Trường') if 'Tên Trường' in df.columns else -1
    
    if school_col_idx == -1:
         print("Lỗi: Không tìm thấy cột 'Tên Trường'")
         return

    print("3. Đang xử lý Hidden Column Injection...")
    current_school = ""
    current_major_code = ""
    injected_count = 0
    
    major_code_pattern = re.compile(r'\b7\d{6}\b')
    
    last_col_values = df[last_col].tolist()
    school_values = df['Tên Trường'].tolist()
    records = df.values.tolist()
    
    for i, row in enumerate(records):
        school = str(school_values[i]).strip()
        
        if school != current_school:
            current_school = school
            current_major_code = ""
            
        row_str = " | ".join(map(str, row))
        found_codes = major_code_pattern.findall(row_str)
        
        if found_codes:
            current_major_code = found_codes[0]
        elif current_major_code:
            last_col_values[i] = f"[HIDDEN_CODE: {current_major_code}]"
            injected_count += 1
            
    df[last_col] = last_col_values
    
    print(f"4. Đã bơm thành công mã ngành ẩn cho {injected_count} dòng bị khuyết!")
    
    print("5. Đang lưu lại file data_tuyensinh.csv...")
    df.to_csv(original_path, index=False, encoding='utf-8-sig')
    
    print("HOÀN THÀNH! Hệ thống RAG giờ đây có thể quét trúng mọi dòng Merged Cells.")

if __name__ == "__main__":
    main()
