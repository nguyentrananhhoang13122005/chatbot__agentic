import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "chat_history.db"
    import chat_db

    monkeypatch.setattr(chat_db, "DB_PATH", str(db_path))
    yield str(db_path)


@pytest.fixture()
def auth_modules(isolated_db, monkeypatch):
    import chat_db
    import auth_db
    import auth

    monkeypatch.setattr(auth_db, "DB_PATH", isolated_db)
    chat_db.init_db()
    auth_db.init_auth_db()
    return auth_db, auth, chat_db


class TestAuthDb:
    def test_create_and_get_user_by_email(self, auth_modules):
        auth_db, _, _ = auth_modules

        user = auth_db.create_user(
            email="student@example.com",
            display_name="Student One",
            avatar_url="",
            auth_provider="email",
            password_hash="hashed",
        )

        loaded = auth_db.get_user_by_email("student@example.com")
        assert loaded["id"] == user["id"]
        assert loaded["email"] == "student@example.com"
        assert loaded["display_name"] == "Student One"
        assert loaded["auth_provider"] == "email"
        assert loaded["password_hash"] == "hashed"

    def test_upsert_google_user_merges_existing_email_user(self, auth_modules):
        auth_db, _, _ = auth_modules
        existing = auth_db.create_user(
            email="merge@example.com",
            display_name="Old Name",
            avatar_url="",
            auth_provider="email",
            password_hash="hashed",
        )

        merged = auth_db.upsert_google_user(
            email="merge@example.com",
            display_name="Google Name",
            avatar_url="https://example.com/avatar.png",
        )

        assert merged["id"] == existing["id"]
        assert merged["display_name"] == "Google Name"
        assert merged["avatar_url"] == "https://example.com/avatar.png"
        assert merged["auth_provider"] == "google"


class TestAuth:
    def test_register_user_rejects_duplicate_email(self, auth_modules):
        _, auth, _ = auth_modules

        first_user, first_error = auth.register_user("dupe@example.com", "Dupe", "secret123")
        second_user, second_error = auth.register_user("dupe@example.com", "Dupe 2", "secret123")

        assert first_error is None
        assert first_user is not None
        assert second_user is None
        assert second_error == "Email này đã được đăng ký."

    def test_login_user_rejects_wrong_password(self, auth_modules):
        _, auth, _ = auth_modules
        auth.register_user("login@example.com", "Login User", "correct123")

        user, error = auth.login_user("login@example.com", "wrong123")

        assert user is None
        assert error == "Email hoặc mật khẩu không đúng."

    def test_login_user_returns_user_for_correct_password(self, auth_modules):
        _, auth, _ = auth_modules
        auth.register_user("ok@example.com", "OK User", "correct123")

        user, error = auth.login_user("ok@example.com", "correct123")

        assert error is None
        assert user["email"] == "ok@example.com"
        assert user["display_name"] == "OK User"
        assert "password_hash" not in user

    def test_handle_google_callback_returns_none_when_exchange_fails(self, auth_modules, monkeypatch):
        _, auth, _ = auth_modules

        def raise_error(_code):
            raise auth.requests.RequestException("oauth failed")

        monkeypatch.setattr(auth, "exchange_code_for_token", raise_error)

        assert auth.handle_google_callback("bad-code") is None


class TestChatDbUserScoping:
    def test_list_sessions_filters_by_user_id(self, auth_modules):
        _, _, chat_db = auth_modules
        chat_db.save_session("s1", [{"role": "user", "content": "A"}], user_id="user-a")
        chat_db.save_session("s2", [{"role": "user", "content": "B"}], user_id="user-b")

        sessions = chat_db.list_sessions(user_id="user-a")

        assert [session["id"] for session in sessions] == ["s1"]

    def test_load_session_for_user_blocks_other_users(self, auth_modules):
        _, _, chat_db = auth_modules
        messages = [{"role": "user", "content": "private"}]
        chat_db.save_session("private-session", messages, user_id="owner")

        assert chat_db.load_session_for_user("private-session", "owner") == messages
        assert chat_db.load_session_for_user("private-session", "intruder") == []

    def test_anonymous_list_sessions_returns_empty(self, auth_modules):
        _, _, chat_db = auth_modules
        chat_db.save_session("legacy", [{"role": "user", "content": "legacy"}], user_id=None)

        assert chat_db.list_sessions(user_id=None) == []

    def test_delete_session_requires_matching_user_id(self, auth_modules):
        _, _, chat_db = auth_modules
        messages = [{"role": "user", "content": "private"}]
        chat_db.save_session("owned-session", messages, user_id="owner")

        assert chat_db.delete_session("owned-session", user_id="intruder") is False
        assert chat_db.load_session_for_user("owned-session", "owner") == messages
        assert chat_db.delete_session("owned-session", user_id="owner") is True
        assert chat_db.load_session_for_user("owned-session", "owner") == []

    def test_rename_session_requires_matching_user_id(self, auth_modules):
        _, _, chat_db = auth_modules
        chat_db.save_session("rename-session", [{"role": "user", "content": "Original"}], user_id="owner")

        assert chat_db.rename_session("rename-session", "Hacked", user_id="intruder") is False
        assert chat_db.list_sessions(user_id="owner")[0]["title"] == "Original"
        assert chat_db.rename_session("rename-session", "Renamed", user_id="owner") is True
        assert chat_db.list_sessions(user_id="owner")[0]["title"] == "Renamed"

    def test_toggle_bookmark_requires_matching_user_id(self, auth_modules):
        _, _, chat_db = auth_modules
        chat_db.save_session("bookmark-session", [{"role": "user", "content": "Pin me"}], user_id="owner")

        assert chat_db.toggle_bookmark("bookmark-session", user_id="intruder") is False
        assert chat_db.list_sessions(user_id="owner")[0]["bookmarked"] is False
        assert chat_db.toggle_bookmark("bookmark-session", user_id="owner") is True
        assert chat_db.list_sessions(user_id="owner")[0]["bookmarked"] is True


class TestOAuthState:
    def test_get_google_auth_url_includes_state_param(self, auth_modules):
        _, auth, _ = auth_modules
        url = auth.get_google_auth_url(state="abc123")
        assert "state=abc123" in url

    def test_get_google_auth_url_without_state_has_no_state_param(self, auth_modules):
        _, auth, _ = auth_modules
        url = auth.get_google_auth_url()
        assert "state=" not in url


class TestGoogleEmailVerified:
    def test_handle_google_callback_rejects_unverified_email(self, auth_modules, monkeypatch):
        _, auth, _ = auth_modules

        monkeypatch.setattr(auth, "exchange_code_for_token", lambda _code: "fake-token")
        monkeypatch.setattr(auth, "get_google_user_info", lambda _token: {
            "email": "unverified@example.com",
            "email_verified": False,
            "name": "Unverified",
            "picture": "",
        })

        assert auth.handle_google_callback("good-code") is None

    def test_handle_google_callback_accepts_verified_email(self, auth_modules, monkeypatch):
        _, auth, _ = auth_modules

        monkeypatch.setattr(auth, "exchange_code_for_token", lambda _code: "fake-token")
        monkeypatch.setattr(auth, "get_google_user_info", lambda _token: {
            "email": "verified@example.com",
            "email_verified": True,
            "name": "Verified User",
            "picture": "https://example.com/pic.png",
        })

        user = auth.handle_google_callback("good-code")
        assert user is not None
        assert user["email"] == "verified@example.com"


class TestLoginErrorMessages:
    def test_login_wrong_email_returns_generic_error(self, auth_modules):
        _, auth, _ = auth_modules
        _, error = auth.login_user("nonexistent@example.com", "any-password")
        assert error == "Email hoặc mật khẩu không đúng."

    def test_login_wrong_password_returns_generic_error(self, auth_modules):
        _, auth, _ = auth_modules
        auth.register_user("generic@example.com", "User", "correct1234")
        _, error = auth.login_user("generic@example.com", "wrong123")
        assert error == "Email hoặc mật khẩu không đúng."

    def test_login_google_account_still_returns_specific_error(self, auth_modules):
        auth_db, auth, _ = auth_modules
        auth_db.create_user(
            email="guser@example.com",
            display_name="Google User",
            auth_provider="google",
            password_hash="",
        )
        _, error = auth.login_user("guser@example.com", "any")
        assert "Google" in error


class TestPasswordMinLength:
    def test_register_rejects_7_char_password(self, auth_modules):
        _, auth, _ = auth_modules
        _, error = auth.register_user("short@example.com", "User", "1234567")
        assert error is not None
        assert "8" in error

    def test_register_accepts_8_char_password(self, auth_modules):
        _, auth, _ = auth_modules
        user, error = auth.register_user("ok8@example.com", "User", "12345678")
        assert error is None
        assert user is not None
