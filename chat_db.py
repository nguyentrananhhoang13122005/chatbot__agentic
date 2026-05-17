"""
chat_db.py — Lưu trữ lịch sử chat bằng SQLite.
Chức năng:
  - Tạo / cập nhật phiên chat
  - Liệt kê phiên gần đây (có tiêu đề tự sinh từ câu hỏi đầu tiên)
  - Tải lại nội dung phiên
  - Xoá phiên (thủ công hoặc tự động sau 20 ngày)
  - Đánh dấu / bỏ đánh dấu "Đã lưu" (bookmark)
"""

import os
import json
import sqlite3
import uuid
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "chat_history.db")

# ============================================================
# INTERNAL HELPERS
# ============================================================

def _get_conn() -> sqlite3.Connection:
    """Trả về connection tới SQLite DB. Tự tạo file + thư mục nếu chưa có."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Khởi tạo bảng nếu chưa tồn tại. Tự migration nếu cần."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL DEFAULT 'Phiên mới',
            messages    TEXT NOT NULL DEFAULT '[]',
            bookmarked  INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
    """)
    # Migration: thêm cột bookmarked nếu DB cũ chưa có
    try:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN bookmarked INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Cột đã tồn tại → bỏ qua
    try:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN user_id TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


# ============================================================
# PUBLIC API
# ============================================================

def new_session_id() -> str:
    """Sinh UUID mới cho phiên chat."""
    return uuid.uuid4().hex[:12]


def _generate_title(messages: list) -> str:
    """Tạo tiêu đề ngắn gọn từ câu hỏi đầu tiên của user."""
    for msg in messages:
        if msg.get("role") == "user":
            text = msg["content"].strip()
            # Cắt tối đa 40 ký tự, thêm "..." nếu dài
            if len(text) > 40:
                return text[:37] + "..."
            return text
    return "Phiên mới"


def save_session(session_id: str, messages: list, title: str | None = None, user_id: str | None = None):
    """Lưu hoặc cập nhật phiên chat vào DB."""
    if not messages:
        return

    now = datetime.now().isoformat()
    auto_title = title or _generate_title(messages)
    messages_json = json.dumps(messages, ensure_ascii=False)

    conn = _get_conn()
    # UPSERT: nếu session đã tồn tại → cập nhật, nếu chưa → tạo mới
    conn.execute("""
        INSERT INTO chat_sessions (id, title, messages, user_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title      = excluded.title,
            messages   = excluded.messages,
            user_id    = excluded.user_id,
            updated_at = excluded.updated_at
    """, (session_id, auto_title, messages_json, user_id, now, now))
    conn.commit()
    conn.close()


def list_sessions(limit: int = 20, user_id: str | None = None) -> list[dict]:
    """Liệt kê các phiên gần đây, sắp xếp theo updated_at giảm dần."""
    if user_id is None:
        return []

    conn = _get_conn()
    rows = conn.execute("""
        SELECT id, title, bookmarked, created_at, updated_at
        FROM chat_sessions
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()

    result = []
    for r in rows:
        result.append({
            "id": r["id"],
            "title": r["title"],
            "bookmarked": bool(r["bookmarked"]),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })
    return result


def load_session(session_id: str) -> list:
    """Tải messages của một phiên. Trả về [] nếu không tìm thấy."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT messages FROM chat_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    conn.close()

    if row:
        return json.loads(row["messages"])
    return []


def load_session_for_user(session_id: str, user_id: str) -> list:
    conn = _get_conn()
    row = conn.execute(
        "SELECT messages FROM chat_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    conn.close()

    if row:
        return json.loads(row["messages"])
    return []


def delete_session(session_id: str, user_id: str | None = None) -> bool:
    """Xoá một phiên chat."""
    conn = _get_conn()
    if user_id is None:
        cursor = conn.execute("DELETE FROM chat_sessions WHERE id = ? AND user_id IS NULL", (session_id,))
    else:
        cursor = conn.execute("DELETE FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def rename_session(session_id: str, new_title: str, user_id: str | None = None) -> bool:
    """Đổi tên một phiên chat."""
    conn = _get_conn()
    if user_id is None:
        cursor = conn.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ? AND user_id IS NULL",
            (new_title, datetime.now().isoformat(), session_id)
        )
    else:
        cursor = conn.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (new_title, datetime.now().isoformat(), session_id, user_id)
        )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def toggle_bookmark(session_id: str, user_id: str | None = None) -> bool:
    """Đảo trạng thái bookmark. Trả về trạng thái mới."""
    conn = _get_conn()
    if user_id is None:
        row = conn.execute(
            "SELECT bookmarked FROM chat_sessions WHERE id = ? AND user_id IS NULL", (session_id,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT bookmarked FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id)
        ).fetchone()

    if row is None:
        conn.close()
        return False

    new_val = 0 if row["bookmarked"] else 1
    if user_id is None:
        conn.execute(
            "UPDATE chat_sessions SET bookmarked = ? WHERE id = ? AND user_id IS NULL",
            (new_val, session_id),
        )
    else:
        conn.execute(
            "UPDATE chat_sessions SET bookmarked = ? WHERE id = ? AND user_id = ?",
            (new_val, session_id, user_id),
        )
    conn.commit()
    conn.close()
    return bool(new_val)


def cleanup_old_sessions(days: int = 20) -> int:
    """Xoá các phiên KHÔNG được bookmark và cũ hơn `days` ngày.
    Trả về số phiên đã xoá."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    conn = _get_conn()
    cursor = conn.execute(
        "DELETE FROM chat_sessions WHERE bookmarked = 0 AND updated_at < ?",
        (cutoff,),
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted > 0:
        print(f"🧹 [ChatDB] Đã xoá {deleted} phiên chat cũ hơn {days} ngày.")
    return deleted


def clear_all_sessions():
    """Xoá TOÀN BỘ lịch sử chat (kể cả bookmark)."""
    conn = _get_conn()
    conn.execute("DELETE FROM chat_sessions")
    conn.commit()
    conn.close()


def format_session_date(iso_str: str) -> str:
    """Format ngày tháng thân thiện: 'Hôm nay', 'Hôm qua', hoặc 'dd/mm'."""
    try:
        dt = datetime.fromisoformat(iso_str)
        now = datetime.now()
        delta = (now.date() - dt.date()).days

        if delta == 0:
            return f"Hôm nay, {dt.strftime('%H:%M')}"
        elif delta == 1:
            return f"Hôm qua, {dt.strftime('%H:%M')}"
        elif delta < 7:
            weekdays = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]
            return f"{weekdays[dt.weekday()]}, {dt.strftime('%H:%M')}"
        else:
            return dt.strftime("%d/%m/%Y")
    except Exception:
        return iso_str[:10]
