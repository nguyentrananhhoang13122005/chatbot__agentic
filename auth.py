import os
import re
from urllib.parse import urlencode
import time
import streamlit as st

import requests
from dotenv import load_dotenv

from auth_db import get_user_by_email, init_auth_db, create_user, update_last_login, upsert_google_user, normalize_email

load_dotenv(override=True)

# ── Module-level OAuth state store ──────────────────────────────
# st.session_state is tied to the WebSocket; when the browser
# navigates away (Google OAuth redirect) the socket disconnects
# and the session may be lost.  A module-level dict survives
# across Streamlit sessions inside the same server process.
_OAUTH_TTL = 600                        # 10 minutes

@st.cache_resource
def _get_oauth_store() -> dict:
    """Shared dict that survives Streamlit reruns."""
    return {}

def _store_oauth_state(state: str):
    store = _get_oauth_store()
    store[state] = time.time()
    cutoff = time.time() - _OAUTH_TTL
    for k in [k for k, v in store.items() if v < cutoff]:
        store.pop(k, None)

def _consume_oauth_state(state: str) -> bool:
    store = _get_oauth_store()
    if state and state in store:
        ts = store.pop(state)
        return (time.time() - ts) < _OAUTH_TTL
    return False

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _sanitize_user(user: dict | None) -> dict | None:
    if not user:
        return None
    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "avatar_url": user.get("avatar_url", ""),
        "auth_provider": user.get("auth_provider", ""),
        "created_at": user.get("created_at", ""),
        "last_login": user.get("last_login", ""),
    }


def get_google_auth_url(state: str | None = None) -> str:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    if state:
        params["state"] = state
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> str:
    response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501"),
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("access_token", "")


def get_google_user_info(access_token: str) -> dict:
    response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    return {
        "email": payload.get("email", ""),
        "email_verified": payload.get("email_verified", False),
        "name": payload.get("name", ""),
        "picture": payload.get("picture", ""),
    }


def hash_password(plain: str) -> str:
    import bcrypt

    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    import bcrypt

    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def register_user(email: str, display_name: str, password: str) -> tuple[dict | None, str | None]:
    init_auth_db()
    normalized_email = normalize_email(email)
    cleaned_name = (display_name or "").strip()

    if not EMAIL_PATTERN.match(normalized_email):
        return None, "Email không hợp lệ."
    if not cleaned_name:
        return None, "Vui lòng nhập họ và tên."
    if len(password or "") < 8:
        return None, "Mật khẩu phải có ít nhất 8 ký tự."
    if get_user_by_email(normalized_email):
        return None, "Email này đã được đăng ký."

    user = create_user(
        email=normalized_email,
        display_name=cleaned_name,
        avatar_url="",
        auth_provider="email",
        password_hash=hash_password(password),
    )
    return _sanitize_user(user), None


def login_user(email: str, password: str) -> tuple[dict | None, str | None]:
    init_auth_db()
    normalized_email = normalize_email(email)
    user = get_user_by_email(normalized_email)

    if user is None:
        return None, "Email hoặc mật khẩu không đúng."
    if user.get("auth_provider") == "google" and not user.get("password_hash"):
        return None, "Tài khoản này dùng Google. Vui lòng đăng nhập bằng Google."
    if not verify_password(password or "", user.get("password_hash", "")):
        return None, "Email hoặc mật khẩu không đúng."

    update_last_login(user["id"])
    refreshed = get_user_by_email(normalized_email)
    return _sanitize_user(refreshed), None


def handle_google_callback(code: str) -> dict | None:
    if not code:
        return None
    init_auth_db()
    try:
        access_token = exchange_code_for_token(code)
        if not access_token:
            return None
        info = get_google_user_info(access_token)
        if not info.get("email_verified", False):
            return None
        email = normalize_email(info.get("email", ""))
        if not email:
            return None
        display_name = (info.get("name") or email).strip()
        user = upsert_google_user(email=email, display_name=display_name, avatar_url=info.get("picture", ""))
        return _sanitize_user(user)
    except requests.RequestException:
        return None
    except (KeyError, ValueError):
        return None


def get_current_user() -> dict | None:
    import streamlit as st

    return st.session_state.get("user")


def is_logged_in() -> bool:
    return get_current_user() is not None


def logout():
    import streamlit as st

    st.session_state.pop("user", None)
