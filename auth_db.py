import os
import sqlite3
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "chat_history.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_user(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
        "avatar_url": row["avatar_url"],
        "auth_provider": row["auth_provider"],
        "password_hash": row["password_hash"],
        "created_at": row["created_at"],
        "last_login": row["last_login"],
    }


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def init_auth_db():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            email         TEXT UNIQUE NOT NULL,
            display_name  TEXT NOT NULL,
            avatar_url    TEXT DEFAULT '',
            auth_provider TEXT NOT NULL DEFAULT 'email',
            password_hash TEXT DEFAULT '',
            created_at    TEXT NOT NULL,
            last_login    TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS oauth_states (
            state TEXT PRIMARY KEY,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def store_oauth_state_db(state: str, ttl: int):
    import time
    now = time.time()
    conn = _get_conn()
    conn.execute(
        "INSERT INTO oauth_states (state, created_at) VALUES (?, ?)",
        (state, now)
    )
    # Cleanup expired
    conn.execute("DELETE FROM oauth_states WHERE created_at < ?", (now - ttl,))
    conn.commit()
    conn.close()

def consume_oauth_state_db(state: str, ttl: int) -> bool:
    import time
    now = time.time()
    conn = _get_conn()
    row = conn.execute("SELECT created_at FROM oauth_states WHERE state = ?", (state,)).fetchone()
    if row:
        conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        conn.commit()
        conn.close()
        created_at = row["created_at"]
        return (now - created_at) < ttl
    conn.close()
    return False


def create_user(email: str, display_name: str, avatar_url: str = "", auth_provider: str = "email", password_hash: str = "") -> dict:
    now = datetime.now().isoformat()
    user_id = uuid.uuid4().hex
    normalized_email = normalize_email(email)
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO users (id, email, display_name, avatar_url, auth_provider, password_hash, created_at, last_login)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, normalized_email, display_name.strip(), avatar_url or "", auth_provider, password_hash or "", now, now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return _row_to_user(row)


def get_user_by_email(email: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (normalize_email(email),)).fetchone()
    conn.close()
    return _row_to_user(row)


def get_user_by_id(user_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return _row_to_user(row)


def update_last_login(user_id: str):
    conn = _get_conn()
    conn.execute(
        "UPDATE users SET last_login = ? WHERE id = ?",
        (datetime.now().isoformat(), user_id),
    )
    conn.commit()
    conn.close()


def upsert_google_user(email: str, display_name: str, avatar_url: str = "") -> dict:
    normalized_email = normalize_email(email)
    existing = get_user_by_email(normalized_email)
    if existing:
        now = datetime.now().isoformat()
        conn = _get_conn()
        conn.execute(
            """
            UPDATE users
            SET display_name = ?, avatar_url = ?, auth_provider = ?, last_login = ?
            WHERE id = ?
            """,
            (display_name.strip(), avatar_url or "", "google", now, existing["id"]),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (existing["id"],)).fetchone()
        conn.close()
        return _row_to_user(row)
    return create_user(
        email=normalized_email,
        display_name=display_name.strip() or normalized_email,
        avatar_url=avatar_url or "",
        auth_provider="google",
        password_hash="",
    )


def update_password(user_id: str, new_password_hash: str):
    conn = _get_conn()
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (new_password_hash, user_id),
    )
    conn.commit()
    conn.close()


def delete_user_account(user_id: str):
    conn = _get_conn()
    # Cascade delete messages and searched universities
    conn.execute("DELETE FROM chat_sessions WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM searched_universities WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

