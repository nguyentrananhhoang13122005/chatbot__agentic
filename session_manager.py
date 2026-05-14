import sqlite3
import os
import uuid
from datetime import datetime

DB_PATH = os.path.join("data", "chat_history.db")

def get_db_connection():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Create sessions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_bookmarked BOOLEAN DEFAULT 0
        )
    ''')
    # Create messages table
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()
    
    # Auto-cleanup old sessions
    cleanup_old_sessions(20)

def create_session(title="Phiên chat mới"):
    session_id = str(uuid.uuid4())
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO sessions (session_id, title, created_at, updated_at, is_bookmarked) VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0)",
        (session_id, title)
    )
    conn.commit()
    conn.close()
    return session_id

def get_recent_sessions(limit=10):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_bookmarked_sessions():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM sessions WHERE is_bookmarked = 1 ORDER BY updated_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_messages(session_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]} for row in rows]

def add_message(session_id, role, content):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
        (session_id, role, content)
    )
    # Update session's updated_at timestamp
    c.execute("UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def update_session_title(session_id, title):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?", (title, session_id))
    conn.commit()
    conn.close()

def toggle_bookmark(session_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT is_bookmarked FROM sessions WHERE session_id = ?", (session_id,))
    row = c.fetchone()
    if row:
        new_status = 0 if row["is_bookmarked"] else 1
        c.execute("UPDATE sessions SET is_bookmarked = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?", (new_status, session_id))
        conn.commit()
    conn.close()

def is_bookmarked(session_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT is_bookmarked FROM sessions WHERE session_id = ?", (session_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return bool(row["is_bookmarked"])
    return False

def delete_session(session_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def delete_all_sessions():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM messages")
    c.execute("DELETE FROM sessions")
    conn.commit()
    conn.close()

def cleanup_old_sessions(days=20):
    conn = get_db_connection()
    c = conn.cursor()
    # Delete non-bookmarked sessions older than X days
    c.execute(f"DELETE FROM messages WHERE session_id IN (SELECT session_id FROM sessions WHERE updated_at <= datetime('now', '-{days} days') AND is_bookmarked = 0)")
    c.execute(f"DELETE FROM sessions WHERE updated_at <= datetime('now', '-{days} days') AND is_bookmarked = 0")
    conn.commit()
    conn.close()
