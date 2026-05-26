import hashlib
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.method_normalizer import normalize_method

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


SCHEMA_VERSION = "exam-advising-v1"
VERIFIED_COLUMNS_FOR_HASH = [
    "Trường",
    "Mã ngành",
    "Tên ngành",
    "Phương thức xét tuyển",
    "Điểm chuẩn",
    "Tổ hợp môn",
    "Ghi chú",
    "Năm",
]


def _sha256_file(path: str | os.PathLike[str]) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _compute_row_hash(row: pd.Series) -> str:
    canonical = "|".join(str(row.get(col, "")).strip() for col in VERIFIED_COLUMNS_FOR_HASH)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _backup_db(db_path: str) -> None:
    if not os.path.exists(db_path):
        return
    backup_dir = os.path.join(os.path.dirname(db_path), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"admissions_{stamp}.db")
    shutil.copy2(db_path, backup_path)
    print(f"🛡️ Đã backup database: {backup_path}")


def _prepare_verified_dataframe(csv_path: str) -> tuple[pd.DataFrame, str]:
    df_verified = pd.read_csv(csv_path).fillna("")
    df_verified.columns = df_verified.columns.str.strip()

    if "Phương thức xét tuyển" in df_verified.columns:
        df_verified["method_key"] = df_verified["Phương thức xét tuyển"].apply(normalize_method)
    else:
        df_verified["method_key"] = ""

    if "Điểm chuẩn" in df_verified.columns:
        df_verified["Điểm chuẩn_Num"] = pd.to_numeric(df_verified["Điểm chuẩn"], errors="coerce")
    else:
        df_verified["Điểm chuẩn_Num"] = pd.NA

    if "Năm" in df_verified.columns:
        df_verified["Năm_Num"] = pd.to_numeric(df_verified["Năm"], errors="coerce").astype("Int64")
    else:
        df_verified["Năm_Num"] = pd.Series([pd.NA] * len(df_verified), dtype="Int64")

    df_verified["row_hash"] = df_verified.apply(_compute_row_hash, axis=1)
    return df_verified, _sha256_file(csv_path)


def _create_cache_tables(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS db_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS admission_rule_cache (
            row_hash TEXT PRIMARY KEY,
            rule_json TEXT NOT NULL,
            parser_version TEXT NOT NULL,
            data_version TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )


def _create_verified_indexes(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_verified_method_year_cutoff '
        'ON diem_chuan_verified(method_key, "Năm_Num", "Điểm chuẩn_Num");'
    )
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_verified_row_hash ON diem_chuan_verified(row_hash);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_verified_truong ON diem_chuan_verified("Trường");')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_verified_ma_nganh ON diem_chuan_verified("Mã ngành");')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_verified_diem ON diem_chuan_verified("Điểm chuẩn_Num");')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_verified_nam ON diem_chuan_verified("Năm_Num");')


def _update_metadata(conn: sqlite3.Connection, source_hash: str) -> None:
    metadata = {
        "source_hash": source_hash,
        "migrated_at": datetime.now().isoformat(timespec="seconds"),
        "schema_version": SCHEMA_VERSION,
    }
    conn.executemany(
        "INSERT OR REPLACE INTO db_metadata(key, value) VALUES (?, ?)",
        metadata.items(),
    )

def sync_csv_to_db(db_path="data/admissions.db"):
    """
    Đồng bộ dữ liệu từ các file CSV sang SQLite.
    Hàm này có thể được gọi lại bất cứ khi nào bạn cập nhật dữ liệu CSV mới.
    Sử dụng if_exists='replace' nên KHÔNG LO BỊ LỖI TRÙNG LẶP.
    """
    # Đảm bảo thư mục data tồn tại
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    _backup_db(db_path)
    
    conn = sqlite3.connect(db_path)
    print(f"🔄 Đang kết nối tới Database: {db_path}")
    _create_cache_tables(conn)

    # 1. Bảng diem_chuan_verified
    csv_verified = "data/data_diem_chuan_verified.csv"
    if os.path.exists(csv_verified):
        print(f"📦 Đang load {csv_verified}...")
        df_verified, source_hash = _prepare_verified_dataframe(csv_verified)
            
        # Ghi đè chỉ bảng diem_chuan_verified. Cache tables dùng IF NOT EXISTS và không bị drop.
        df_verified.to_sql('diem_chuan_verified', conn, if_exists='replace', index=False)
        print("✅ Đã ghi bảng 'diem_chuan_verified'.")
        
        # Tạo Indexes lại sau to_sql replace.
        _create_verified_indexes(conn)
        _update_metadata(conn, source_hash)
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
