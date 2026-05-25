import os
import sqlite3
import pandas as pd
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def sync_csv_to_db(db_path="data/admissions.db"):
    """
    Đồng bộ dữ liệu từ các file CSV sang SQLite.
    Hàm này có thể được gọi lại bất cứ khi nào bạn cập nhật dữ liệu CSV mới.
    Sử dụng if_exists='replace' nên KHÔNG LO BỊ LỖI TRÙNG LẶP.
    """
    # Đảm bảo thư mục data tồn tại
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    print(f"🔄 Đang kết nối tới Database: {db_path}")

    # 1. Bảng diem_chuan_verified
    csv_verified = "data/data_diem_chuan_verified.csv"
    if os.path.exists(csv_verified):
        print(f"📦 Đang load {csv_verified}...")
        df_verified = pd.read_csv(csv_verified).fillna("")
        
        # Tiền xử lý kiểu dữ liệu (Convert thành float ngay khi ghi vào DB)
        if 'Điểm chuẩn' in df_verified.columns:
            df_verified['Điểm chuẩn_Num'] = pd.to_numeric(df_verified['Điểm chuẩn'], errors='coerce').fillna(0)
        
        if 'Năm' in df_verified.columns:
            df_verified['Năm_Num'] = pd.to_numeric(df_verified['Năm'], errors='coerce').fillna(0)
            
        # Ghi đè vào bảng
        df_verified.to_sql('diem_chuan_verified', conn, if_exists='replace', index=False)
        print("✅ Đã ghi bảng 'diem_chuan_verified'.")
        
        # Tạo Indexes (giúp tìm kiếm O(log N))
        cursor = conn.cursor()
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_verified_truong ON diem_chuan_verified("Trường");')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_verified_ma_nganh ON diem_chuan_verified("Mã ngành");')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_verified_diem ON diem_chuan_verified("Điểm chuẩn_Num");')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_verified_nam ON diem_chuan_verified("Năm_Num");')
        print("⚡ Đã tạo Index cho 'diem_chuan_verified'.")

    # 2. Bảng dats_master
    csv_master = "data/data_tuyensinh_master.csv"
    if os.path.exists(csv_master):
        print(f"📦 Đang load {csv_master}...")
        df_master = pd.read_csv(csv_master).fillna("")
        
        if 'Năm' in df_master.columns:
            df_master['Năm_Num'] = pd.to_numeric(df_master['Năm'], errors='coerce').fillna(0)
            
        df_master.to_sql('dats_master', conn, if_exists='replace', index=False)
        print("✅ Đã ghi bảng 'dats_master'.")
        
        cursor = conn.cursor()
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_master_truong ON dats_master("Trường");')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_master_nam ON dats_master("Năm_Num");')
        print("⚡ Đã tạo Index cho 'dats_master'.")
        
    # 3. Bảng data_tuyensinh_clean (Nếu cần tra cứu thêm)
    csv_clean = "data/data_tuyensinh_clean.csv"
    if os.path.exists(csv_clean):
        print(f"📦 Đang load {csv_clean}...")
        df_clean = pd.read_csv(csv_clean, low_memory=False).fillna("")
        df_clean.to_sql('tuyensinh_clean', conn, if_exists='replace', index=False)
        print("✅ Đã ghi bảng 'tuyensinh_clean'.")
        
        cursor = conn.cursor()
        if "Trường" in df_clean.columns:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_clean_truong ON tuyensinh_clean("Trường");')
        print("⚡ Đã tạo Index cho 'tuyensinh_clean'.")

    conn.commit()
    conn.close()
    print("🎉 Hoàn tất đồng bộ dữ liệu vào SQLite!")

if __name__ == "__main__":
    sync_csv_to_db()
