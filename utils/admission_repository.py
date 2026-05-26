# -*- coding: utf-8 -*-
"""SQLite access layer for admission cutoff rows."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from utils.method_normalizer import EXAM_METHOD_ALIASES, is_exam_method, normalize_method


DEFAULT_DB_PATH = Path("data/admissions.db")
DEFAULT_CSV_PATH = Path("data/data_diem_chuan_verified.csv")


@dataclass(frozen=True)
class AdmissionRow:
    truong: str
    ma_nganh: str
    ten_nganh: str
    nam_num: int
    phuong_thuc: str
    method_key: str
    diem_chuan_num: float
    to_hop_mon: str
    ghi_chu: str
    row_hash: str


_FIELD_MAP = {
    "Trường": "truong",
    "Mã ngành": "ma_nganh",
    "Tên ngành": "ten_nganh",
    "Năm_Num": "nam_num",
    "Phương thức xét tuyển": "phuong_thuc",
    "Điểm chuẩn_Num": "diem_chuan_num",
    "Tổ hợp môn": "to_hop_mon",
    "Ghi chú": "ghi_chu",
}


class AdmissionRepository:
    """Read admission rows from SQLite, with CSV fallback only for local dev."""

    def __init__(self, db_path: str | os.PathLike[str] = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.csv_path = DEFAULT_CSV_PATH
        self._use_csv_fallback = False

        if not self.db_path.exists():
            env = os.getenv("APP_ENV") or os.getenv("ENV") or os.getenv("ADMISSIONS_ENV")
            if str(env).lower() in {"prod", "production", "deploy", "deployment"}:
                raise FileNotFoundError(
                    f"SQLite database not found at {self.db_path}. Run scripts/migrate_csv_to_sqlite.py first."
                )
            warnings.warn(
                f"SQLite database not found at {self.db_path}; falling back to CSV for local development.",
                RuntimeWarning,
                stacklevel=2,
            )
            self._use_csv_fallback = True

    def iter_exam_rows(self, years: Iterable[int] | None = None) -> Iterable[AdmissionRow]:
        """Yield exam-method rows with valid cutoff scores from the repository."""
        if self._use_csv_fallback:
            yield from self._iter_exam_rows_csv(years)
            return

        where = ['method_key IN ({})'.format(",".join("?" for _ in EXAM_METHOD_ALIASES))]
        params: list[object] = list(EXAM_METHOD_ALIASES)
        where.append('"Điểm chuẩn_Num" > 0')
        where.append('"Điểm chuẩn_Num" <= 40')
        year_list = [int(y) for y in years] if years else []
        if year_list:
            where.append('"Năm_Num" IN ({})'.format(",".join("?" for _ in year_list)))
            params.extend(year_list)

        sql = f"""
            SELECT "Trường", "Mã ngành", "Tên ngành", "Năm_Num",
                   "Phương thức xét tuyển", method_key, "Điểm chuẩn_Num",
                   "Tổ hợp môn", "Ghi chú", row_hash
            FROM diem_chuan_verified
            WHERE {" AND ".join(where)}
            ORDER BY "Năm_Num" DESC, "Trường", "Tên ngành"
        """
        with self._connect() as conn:
            for row in conn.execute(sql, params):
                item = self._row_from_sqlite(row)
                if is_exam_method(item.phuong_thuc):
                    yield item

    def get_rows_by_method_and_year(
        self,
        method_key: str,
        years: Iterable[int] | None,
        max_cutoff: float = 40.0,
    ) -> list[AdmissionRow]:
        """Return rows by normalized method key and optional years."""
        key = normalize_method(method_key)
        rows = [r for r in self.iter_exam_rows(years) if r.method_key == key and r.diem_chuan_num <= max_cutoff]
        return rows

    def get_latest_exam_year(self, years: Iterable[int] | None = None) -> int | None:
        """Return the newest available exam year within an optional allow-list."""
        rows = list(self.iter_exam_rows(years))
        if not rows:
            return None
        return max(row.nam_num for row in rows)

    def get_row_version(self) -> str:
        """Return a stable version hash for invalidating parsed-rule caches."""
        if self._use_csv_fallback:
            if not self.csv_path.exists():
                return "missing-csv"
            return hashlib.sha256(self.csv_path.read_bytes()).hexdigest()

        with self._connect() as conn:
            metadata = conn.execute(
                "SELECT value FROM db_metadata WHERE key = 'source_hash'"
            ).fetchone()
            if metadata:
                return str(metadata["value"])
            values = [
                str(row["row_hash"])
                for row in conn.execute(
                    "SELECT row_hash FROM diem_chuan_verified ORDER BY row_hash"
                )
                if row["row_hash"]
            ]
        return hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()

    def load_cached_rule(self, row_hash: str, parser_version: str, data_version: str) -> str | None:
        """Return cached rule JSON when version metadata matches."""
        if self._use_csv_fallback:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT rule_json FROM admission_rule_cache
                WHERE row_hash = ? AND parser_version = ? AND data_version = ?
                """,
                (row_hash, parser_version, data_version),
            ).fetchone()
        return str(row["rule_json"]) if row else None

    def load_cached_rules(
        self,
        row_hashes: Iterable[str],
        parser_version: str,
        data_version: str,
    ) -> dict[str, str]:
        """Batch-load cached rule JSON payloads for many row hashes."""
        if self._use_csv_fallback:
            return {}
        hashes = [item for item in row_hashes if item]
        if not hashes:
            return {}

        result: dict[str, str] = {}
        with self._connect() as conn:
            for index in range(0, len(hashes), 500):
                chunk = hashes[index : index + 500]
                placeholders = ",".join("?" for _ in chunk)
                sql = f"""
                    SELECT row_hash, rule_json
                    FROM admission_rule_cache
                    WHERE parser_version = ?
                      AND data_version = ?
                      AND row_hash IN ({placeholders})
                """
                params = [parser_version, data_version, *chunk]
                for row in conn.execute(sql, params):
                    result[str(row["row_hash"])] = str(row["rule_json"])
        return result

    def save_cached_rule(self, row_hash: str, rule_json: str, parser_version: str, data_version: str) -> None:
        """Persist a parsed-rule JSON string in SQLite cache."""
        if self._use_csv_fallback:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO admission_rule_cache
                    (row_hash, rule_json, parser_version, data_version, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (row_hash, rule_json, parser_version, data_version),
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _iter_exam_rows_csv(self, years: Iterable[int] | None = None) -> Iterable[AdmissionRow]:
        if not self.csv_path.exists():
            return
        df = pd.read_csv(self.csv_path, encoding="utf-8").fillna("")
        df.columns = df.columns.str.strip()
        df["Điểm chuẩn_Num"] = pd.to_numeric(df.get("Điểm chuẩn", 0), errors="coerce").fillna(0)
        df["Năm_Num"] = pd.to_numeric(df.get("Năm", 0), errors="coerce").fillna(0).astype(int)
        df["method_key"] = df.get("Phương thức xét tuyển", "").apply(normalize_method)
        year_set = {int(y) for y in years} if years else None

        for _, row in df.iterrows():
            method = str(row.get("Phương thức xét tuyển", ""))
            cutoff = float(row.get("Điểm chuẩn_Num", 0) or 0)
            year = int(row.get("Năm_Num", 0) or 0)
            if not is_exam_method(method) or not (0 < cutoff <= 40):
                continue
            if year_set and year not in year_set:
                continue
            row_hash = str(row.get("row_hash") or _compute_row_hash_from_mapping(row))
            yield AdmissionRow(
                truong=str(row.get("Trường", "")),
                ma_nganh=str(row.get("Mã ngành", "")),
                ten_nganh=str(row.get("Tên ngành", "")),
                nam_num=year,
                phuong_thuc=method,
                method_key=str(row.get("method_key", "")),
                diem_chuan_num=cutoff,
                to_hop_mon=str(row.get("Tổ hợp môn", "")),
                ghi_chu=str(row.get("Ghi chú", "")),
                row_hash=row_hash,
            )

    @staticmethod
    def _row_from_sqlite(row: sqlite3.Row) -> AdmissionRow:
        return AdmissionRow(
            truong=str(row["Trường"] or ""),
            ma_nganh=str(row["Mã ngành"] or ""),
            ten_nganh=str(row["Tên ngành"] or ""),
            nam_num=int(row["Năm_Num"] or 0),
            phuong_thuc=str(row["Phương thức xét tuyển"] or ""),
            method_key=str(row["method_key"] or ""),
            diem_chuan_num=float(row["Điểm chuẩn_Num"] or 0),
            to_hop_mon=str(row["Tổ hợp môn"] or ""),
            ghi_chu=str(row["Ghi chú"] or ""),
            row_hash=str(row["row_hash"] or ""),
        )


def _compute_row_hash_from_mapping(row: object) -> str:
    columns = [
        "Trường",
        "Mã ngành",
        "Tên ngành",
        "Phương thức xét tuyển",
        "Điểm chuẩn",
        "Tổ hợp môn",
        "Ghi chú",
        "Năm",
    ]
    canonical = "|".join(str(row.get(col, "")).strip() for col in columns)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
