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


class TestSaveSessionOwnerSafety:
    def test_save_session_cannot_steal_ownership(self, auth_modules):
        _, _, chat_db = auth_modules
        chat_db.save_session("steal-test", [{"role": "user", "content": "mine"}], user_id="owner-a")

        chat_db.save_session("steal-test", [{"role": "user", "content": "stolen"}], user_id="attacker")

        msgs = chat_db.load_session_for_user("steal-test", "owner-a")
        assert len(msgs) > 0
        assert msgs[0]["content"] == "mine"
        assert chat_db.load_session_for_user("steal-test", "owner-a") == msgs
        assert chat_db.load_session_for_user("steal-test", "attacker") == []

class TestOAuthStateStore:
    def test_store_and_consume_state(self, auth_modules):
        _, auth, _ = auth_modules
        auth.store_oauth_state("test-state-123")
        assert auth.consume_oauth_state("test-state-123") is True
        assert auth.consume_oauth_state("test-state-123") is False

    def test_consume_expired_state(self, auth_modules, monkeypatch):
        _, auth, _ = auth_modules
        import time
        auth.store_oauth_state("expired-state")
        current_time = time.time()
        monkeypatch.setattr("time.time", lambda: current_time + 601)
        assert auth.consume_oauth_state("expired-state") is False

class TestGoogleAPI:
    def test_exchange_code_for_token_success(self, auth_modules, monkeypatch):
        _, auth, _ = auth_modules
        class MockResponse:
            def raise_for_status(self): pass
            def json(self): return {"access_token": "mock-access-token"}
        monkeypatch.setattr(auth.requests, "post", lambda *args, **kwargs: MockResponse())
        token = auth.exchange_code_for_token("valid-code")
        assert token == "mock-access-token"

    def test_get_google_user_info_success(self, auth_modules, monkeypatch):
        _, auth, _ = auth_modules
        class MockResponse:
            def raise_for_status(self): pass
            def json(self): return {"email": "test@google.com", "email_verified": True, "name": "Test User", "picture": "pic.png"}
        monkeypatch.setattr(auth.requests, "get", lambda *args, **kwargs: MockResponse())
        info = auth.get_google_user_info("token")
        assert info["email"] == "test@google.com"
        assert info["email_verified"] is True
        assert info["name"] == "Test User"
        assert info["picture"] == "pic.png"



class TestAuthEdgeCases:
    def test_sanitize_user_none(self, auth_modules):
        _, auth, _ = auth_modules
        assert auth._sanitize_user(None) is None

    def test_verify_password_empty(self, auth_modules):
        _, auth, _ = auth_modules
        assert auth.verify_password("", "hashed") is False
        assert auth.verify_password("plain", "") is False

    def test_register_invalid_email(self, auth_modules):
        _, auth, _ = auth_modules
        user, error = auth.register_user("invalid-email", "Name", "password123")
        assert user is None
        assert error == "Email không hợp lệ."

    def test_register_empty_name(self, auth_modules):
        _, auth, _ = auth_modules
        user, error = auth.register_user("test@example.com", "   ", "password123")
        assert user is None
        assert error == "Vui lòng nhập họ và tên."

    def test_handle_google_callback_key_error(self, auth_modules, monkeypatch):
        _, auth, _ = auth_modules
        monkeypatch.setattr(auth, "exchange_code_for_token", lambda c: "token")
        monkeypatch.setattr(auth, "get_google_user_info", lambda t: {"wrong_key": "val"})
        assert auth.handle_google_callback("code") is None

    def test_handle_google_callback_no_code(self, auth_modules):
        _, auth, _ = auth_modules
        assert auth.handle_google_callback(None) is None
        assert auth.handle_google_callback("") is None

    def test_verify_password_invalid_hash(self, auth_modules):
        _, auth, _ = auth_modules
        assert auth.verify_password("plain", "invalid-hash-format") is False


class TestAuthSettings:
    def test_change_password_success(self, auth_modules):
        auth_db, auth, _ = auth_modules
        user_raw = auth_db.create_user(
            email="changepass@example.com",
            display_name="Change Pass",
            avatar_url="",
            auth_provider="email",
            password_hash=auth.hash_password("oldpassword123"),
        )

        success, error = auth.change_password(user_raw["id"], "oldpassword123", "newpassword123")
        assert success is True
        assert error is None

        # Verify login with new password works
        logged_in_user, login_err = auth.login_user("changepass@example.com", "newpassword123")
        assert login_err is None
        assert logged_in_user is not None

    def test_change_password_invalid_current(self, auth_modules):
        auth_db, auth, _ = auth_modules
        user_raw = auth_db.create_user(
            email="changepass2@example.com",
            display_name="Change Pass 2",
            avatar_url="",
            auth_provider="email",
            password_hash=auth.hash_password("oldpassword123"),
        )

        success, error = auth.change_password(user_raw["id"], "wrongpassword", "newpassword123")
        assert success is False
        assert error == "Mật khẩu hiện tại không đúng."

    def test_change_password_too_short(self, auth_modules):
        auth_db, auth, _ = auth_modules
        user_raw = auth_db.create_user(
            email="changepass3@example.com",
            display_name="Change Pass 3",
            avatar_url="",
            auth_provider="email",
            password_hash=auth.hash_password("oldpassword123"),
        )

        success, error = auth.change_password(user_raw["id"], "oldpassword123", "short")
        assert success is False
        assert error == "Mật khẩu mới phải có ít nhất 8 ký tự."

    def test_delete_user_account(self, auth_modules):
        auth_db, _, chat_db = auth_modules
        user_raw = auth_db.create_user(
            email="delete@example.com",
            display_name="Delete Me",
            avatar_url="",
            auth_provider="email",
            password_hash="hashed",
        )

        # Save a chat session and searched university
        chat_db.save_session("session1", [{"role": "user", "content": "Hi"}], user_id=user_raw["id"])
        chat_db.save_searched_university(user_raw["id"], "Đại học Bách Khoa")

        # Assert they exist
        assert len(chat_db.list_sessions(user_id=user_raw["id"])) == 1
        assert len(chat_db.list_searched_universities(user_id=user_raw["id"])) == 1

        # Delete account
        auth_db.delete_user_account(user_raw["id"])

        # Verify deleted cascade
        assert auth_db.get_user_by_id(user_raw["id"]) is None
        assert len(chat_db.list_sessions(user_id=user_raw["id"])) == 0
        assert len(chat_db.list_searched_universities(user_id=user_raw["id"])) == 0

    def test_export_and_clear_data(self, auth_modules):
        auth_db, _, chat_db = auth_modules
        user_raw = auth_db.create_user(
            email="export@example.com",
            display_name="Export Me",
            avatar_url="",
            auth_provider="email",
            password_hash="hashed",
        )

        chat_db.save_session("session2", [{"role": "user", "content": "Hello"}], user_id=user_raw["id"])
        chat_db.save_searched_university(user_raw["id"], "Đại học Công nghệ")

        # Export
        chat_csv, uni_csv = chat_db.export_user_data_csv(user_raw["id"])
        assert "Mã phiên chat" in chat_csv
        assert "Hello" in chat_csv
        assert "Tên trường ĐH" in uni_csv
        assert "Đại học Công nghệ" in uni_csv

        # Clear chat sessions
        chat_db.clear_user_chat_sessions(user_raw["id"])
        assert len(chat_db.list_sessions(user_id=user_raw["id"])) == 0

        # Clear searched universities
        chat_db.clear_searched_universities(user_raw["id"])
        assert len(chat_db.list_searched_universities(user_id=user_raw["id"])) == 0

