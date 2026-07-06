import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app
from auth_db import init_auth_db, _get_conn

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_auth_db()
    yield
    # Cleanup DB after tests
    conn = _get_conn()
    conn.execute("DELETE FROM users")
    conn.execute("DELETE FROM oauth_states")
    conn.commit()
    conn.close()

def test_register_success():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "testapi@example.com",
            "display_name": "Test API",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["user"]["email"] == "testapi@example.com"
    # Verify cookie is set
    assert "access_token" in response.cookies

def test_register_validation_error():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "invalid-email",
            "display_name": "Test API",
            "password": "pass"
        }
    )
    assert response.status_code == 400

def test_login_success():
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "display_name": "Login Test",
            "password": "password123"
        }
    )
    
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    assert "access_token" in response.cookies
    data = response.json()
    assert data["user"]["email"] == "login@example.com"

def test_login_failure():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrong"
        }
    )
    assert response.status_code == 400

def test_logout():
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    # Cookie should be cleared (FastAPI does this by setting it to empty and expiring it)
    assert response.cookies.get("access_token") == "" or response.headers["set-cookie"].find("Max-Age=0") != -1

def test_get_me_unauthenticated():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

def test_get_me_authenticated():
    # Register and get token
    login_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "display_name": "Me Test",
            "password": "password123"
        }
    )
    token = login_resp.cookies.get("access_token")
    
    # Set cookie for request
    client.cookies.set("access_token", token)
    response = client.get("/api/v1/auth/me")
    
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "me@example.com"
    # Ensure password_hash is not leaked
    assert "password_hash" not in data["user"]

def test_google_url():
    response = client.get("/api/v1/auth/google/url")
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "https://accounts.google.com/o/oauth2/v2/auth" in data["url"]
    assert "state=" in data["url"]

@patch("api.routers.auth.exchange_code_for_token")
@patch("api.routers.auth.get_google_user_info")
def test_google_callback_success(mock_get_info, mock_exchange):
    mock_exchange.return_value = "mock_access_token"
    mock_get_info.return_value = {
        "email": "google@example.com",
        "email_verified": True,
        "name": "Google User",
        "picture": "http://example.com/pic.jpg"
    }
    
    # Generate state
    url_resp = client.get("/api/v1/auth/google/url")
    url = url_resp.json()["url"]
    # Extract state from URL
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    state = qs["state"][0]
    
    # Callback
    response = client.post(
        "/api/v1/auth/google/callback",
        json={
            "code": "mock_code",
            "state": state
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "google@example.com"
    assert "password_hash" not in data["user"]
    assert "access_token" in response.cookies

def test_google_callback_invalid_state():
    response = client.post(
        "/api/v1/auth/google/callback",
        json={
            "code": "mock_code",
            "state": "invalid_state"
        }
    )
    assert response.status_code == 400
    assert "Invalid or expired OAuth state" in response.json()["detail"]
