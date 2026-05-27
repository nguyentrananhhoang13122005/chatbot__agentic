# -*- coding: utf-8 -*-
"""Shared pytest fixtures for backend admission tests."""

from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def make_row_hash(*values: object) -> str:
    return hashlib.sha256("|".join(str(v) for v in values).encode("utf-8")).hexdigest()


@pytest.fixture
def admission_db(tmp_path):
    """Create a representative SQLite admission DB in a temporary directory."""
    db_path = tmp_path / "admissions.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE diem_chuan_verified (
            "Trường" TEXT,
            "Mã ngành" TEXT,
            "Tên ngành" TEXT,
            "Năm" TEXT,
            "Phương thức xét tuyển" TEXT,
            "Điểm chuẩn" TEXT,
            "Chỉ tiêu" TEXT,
            "Tổ hợp môn" TEXT,
            "Ghi chú" TEXT,
            method_key TEXT,
            row_hash TEXT UNIQUE,
            "Điểm chuẩn_Num" REAL,
            "Năm_Num" INTEGER
        )
        """
    )
    conn.execute("CREATE TABLE db_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute(
        """
        CREATE TABLE admission_rule_cache (
            row_hash TEXT PRIMARY KEY,
            rule_json TEXT NOT NULL,
            parser_version TEXT NOT NULL,
            data_version TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    rows = [
        ("Trường A", "7480201", "Công nghệ thông tin", "2025", "Xét điểm thi THPT", "24", "100", "A00;D01", ""),
        ("Trường B", "7220201", "Ngôn ngữ Anh", "2025", "Điểm thi", "32", "80", "A01;D01", "Thang điểm 40"),
        ("Trường C", "7340101", "Quản trị", "2025", "Điểm thi riêng", "20", "50", "A00", ""),
        ("Trường D", "7340201", "Kế toán", "2025", "Xét điểm Học bạ THPT", "22", "50", "A00", ""),
        ("Trường E", "7480101", "ĐGNL", "2025", "Xét điểm thi THPT", "800", "50", "A00", ""),
        ("Trường F", "7140202", "Sư phạm Toán", "2025", "Xét điểm thi THPT", "25", "50", "A00", "Toán ≥ 9.5"),
        ("Trường G", "7340120", "Kinh doanh quốc tế", "2025", "Xét điểm thi THPT", "24", "50", "D01", "IELTS ≥ 5.5"),
        ("Trường H", "7210403", "Thiết kế", "2025", "Xét điểm thi THPT", "24", "50", "H01", "nhân theo công thức riêng"),
        ("Trường I", "7480201", "Công nghệ thông tin", "2024", "Xét điểm thi THPT", "23", "100", "A00", ""),
        ("Trường J", "7210404", "Thiết kế đồ họa", "2025", "Xét điểm thi THPT", "20", "50", "H01", ""),
    ]
    for row in rows:
        method_key = {
            "Xét điểm thi THPT": "xet diem thi thpt",
            "Điểm thi": "diem thi",
            "Điểm thi riêng": "diem thi rieng",
            "Xét điểm Học bạ THPT": "xet diem hoc ba thpt",
        }[row[4]]
        row_hash = make_row_hash(row[0], row[1], row[2], row[4], row[5], row[7], row[8], row[3])
        conn.execute(
            """
            INSERT INTO diem_chuan_verified
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*row, method_key, row_hash, float(row[5]), int(row[3])),
        )
    conn.execute("INSERT INTO db_metadata(key, value) VALUES ('source_hash', 'fixture-v1')")
    conn.commit()
    conn.close()
    return db_path
