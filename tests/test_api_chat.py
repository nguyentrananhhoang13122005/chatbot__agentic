import pytest
from fastapi.testclient import TestClient
from main import app
from auth_db import init_auth_db, _get_conn

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "auth_test.db")
    monkeypatch.setenv("AUTH_DB_PATH", test_db)
    init_auth_db()
    yield
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM users")
        conn.commit()
        conn.close()
    except Exception:
        pass

def test_chat_sessions_unauthenticated():
    # Unauthenticated should return 200 with empty list
    response = client.get("/api/v1/chat/sessions")
    assert response.status_code == 200
    assert response.json() == []

def test_chat_sessions_lifecycle_authenticated():
    # 1. Register a user
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "chatsession@example.com",
            "display_name": "Chat User",
            "password": "password123"
        }
    )
    assert reg.status_code == 200
    cookies = reg.cookies

    # 2. Initially empty
    res = client.get("/api/v1/chat/sessions", cookies=cookies)
    assert res.status_code == 200
    assert res.json() == []

    # 3. Create a session
    create_res = client.post(
        "/api/v1/chat/sessions",
        json={
            "id": "test-session-123",
            "title": "Tư vấn điểm chuẩn Bách Khoa",
            "messages": [
                {"role": "user", "content": "Điểm chuẩn CNTT Bách Khoa?"},
                {"role": "assistant", "content": "Điểm chuẩn CNTT là 28.5 điểm."}
            ]
        },
        cookies=cookies
    )
    assert create_res.status_code == 200
    assert create_res.json()["id"] == "test-session-123"

    # 4. List sessions
    list_res = client.get("/api/v1/chat/sessions", cookies=cookies)
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["id"] == "test-session-123"
    assert items[0]["title"] == "Tư vấn điểm chuẩn Bách Khoa"

    # 5. Get session details
    detail_res = client.get("/api/v1/chat/sessions/test-session-123", cookies=cookies)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == "test-session-123"
    assert len(detail["messages"]) == 2

    # 6. Update session title
    put_res = client.put(
        "/api/v1/chat/sessions/test-session-123/title",
        json={"title": "Điểm chuẩn HUST 2025"},
        cookies=cookies
    )
    assert put_res.status_code == 200

    # 7. Delete session
    del_res = client.delete("/api/v1/chat/sessions/test-session-123", cookies=cookies)
    assert del_res.status_code == 200

    # 8. Verify deleted
    after_del = client.get("/api/v1/chat/sessions", cookies=cookies)
    assert after_del.status_code == 200
    assert len(after_del.json()) == 0
