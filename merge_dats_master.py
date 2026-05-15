import pandas as pd
import os
import re

# === Đường dẫn ===
CSV_2026 = os.path.join("data", "data_tuyensinh_2026.csv")
CSV_2025 = os.path.join("data", "data_tuyensinh_2025_dats.csv")
CSV_2024 = os.path.join("data", "data_tuyensinh_2024.csv")
OUTPUT_MASTER = os.path.join("data", "data_tuyensinh_master.csv")

def normalize_school_name(name):
    if pd.isna(name): return ""
    name = str(name).upper().strip()
    # Loại bỏ các tiền tố/hậu tố thường gặp để chuẩn hóa (tương tự _normalize_school_name trong recommender.py)
    name = re.sub(r'^(TRƯỜNG\s+)?(ĐẠI HỌC|HỌC VIỆN|ĐH|HV)\s+', '', name)
    name = name.replace(' - ', '-').replace('–', '-')
    return name.strip()

def main():
    dfs = []
    
    # 1. Đọc dữ liệu
    for file_path, year in [(CSV_2026, 2026), (CSV_2025, 2025), (CSV_2024, 2024)]:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            # Ensure proper typing
            df['Năm'] = year
            dfs.append(df)
            print(f"✅ Đã tải: {file_path} ({len(df)} dòng)")
        else:
            print(f"⚠️ Không tìm thấy: {file_path}")
            
    if not dfs:
        print("❌ Không có dữ liệu để gộp.")
        return

    # 2. Gộp lại
    master_df = pd.concat(dfs, ignore_index=True)
    print(f"\n📊 Tổng số dòng trước khi lọc: {len(master_df)}")
    
    # 3. Chuẩn hóa tên trường để group
    master_df['Norm_School'] = master_df['Trường'].apply(normalize_school_name)
    
    # 4. Sắp xếp theo Năm giảm dần để ưu tiên dữ liệu mới nhất
    master_df.sort_values(by=['Norm_School', 'Năm'], ascending=[True, False], inplace=True)
    
    # 5. Drop duplicates theo Norm_School, giữ dòng đầu tiên (năm mới nhất)
    master_df.drop_duplicates(subset=['Norm_School'], keep='first', inplace=True)
    
    # Drop cột phụ
    master_df.drop(columns=['Norm_School'], inplace=True)
    
    # 6. Lưu file
    master_df.to_csv(OUTPUT_MASTER, index=False, encoding='utf-8-sig')
    
    print(f"\n✅ Hoàn thành gộp DATS Master!")
    print(f"  📊 Tổng số trường (unique): {len(master_df)}")
    print(f"  💾 Lưu tại: {OUTPUT_MASTER}")
    print(f"  📏 Kích thước: {os.path.getsize(OUTPUT_MASTER) / 1024:.0f} KB")

    # Hiển thị thống kê theo năm
    print("\nThống kê theo năm dữ liệu:")
    print(master_df['Năm'].value_counts())

if __name__ == "__main__":
    main()
