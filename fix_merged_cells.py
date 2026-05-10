import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import re
import os
import shutil

print("1. Đang sao lưu file gốc...")
original_path = 'data/data_tuyensinh.csv'
backup_path = 'data/data_tuyensinh_backup.csv'
if not os.path.exists(backup_path):
    shutil.copy2(original_path, backup_path)
    print("   Đã tạo bản backup: data_tuyensinh_backup.csv")

print("2. Đang load dữ liệu (có thể mất vài chục giây vì file lớn)...")
df = pd.read_csv(original_path, low_memory=False).fillna("")

# Tìm cột cuối cùng để nhồi dữ liệu
last_col = df.columns[-1]

print("3. Đang xử lý Hidden Column Injection...")
current_school = ""
current_major_code = ""
injected_count = 0

# Regex tìm mã ngành: chuỗi bắt đầu bằng 7 và có 7 chữ số (Mã ngành ĐH Việt Nam luôn bắt đầu bằng 7)
major_code_pattern = re.compile(r'\b7\d{6}\b')

for index, row in df.iterrows():
    school = str(row['Tên Trường']).strip()
    
    # Nếu chuyển sang trường khác, reset mã ngành tạm
    if school != current_school:
        current_school = school
        current_major_code = ""
        
    row_str = " | ".join([str(val) for val in row.values])
    
    # Tìm mã ngành trong dòng hiện tại
    found_codes = major_code_pattern.findall(row_str)
    
    if found_codes:
        # Nếu dòng có chứa mã ngành -> Cập nhật mã ngành hiện tại
        current_major_code = found_codes[0]
    else:
        # Nếu dòng KHÔNG chứa mã ngành, nhưng ta đang giữ một mã ngành trong bộ nhớ
        # Chứng tỏ đây là dòng Merged Cells (phương thức phụ của mã ngành phía trên)
        if current_major_code != "":
            # Nhồi mã ngành vào cột cuối cùng
            df.at[index, last_col] = f"[HIDDEN_CODE: {current_major_code}]"
            injected_count += 1

print(f"4. Đã bơm thành công mã ngành ẩn cho {injected_count} dòng bị khuyết!")

print("5. Đang lưu lại file data_tuyensinh.csv...")
df.to_csv(original_path, index=False, encoding='utf-8-sig')

print("HOÀN THÀNH! Hệ thống RAG giờ đây có thể quét trúng mọi dòng Merged Cells.")
