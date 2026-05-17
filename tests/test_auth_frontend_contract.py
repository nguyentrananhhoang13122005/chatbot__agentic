import ast
import os


APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _source():
    with open(APP_PATH, "r", encoding="utf-8") as file:
        return file.read()


def _tree():
    return ast.parse(_source())


def _imported_names():
    names = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.name)
    return names


def test_app_imports_auth_backend_contract():
    imported = _imported_names()

    assert "init_auth_db" in imported
    assert "handle_google_callback" in imported
    assert "get_google_auth_url" in imported
    assert "login_user" in imported
    assert "register_user" in imported
    assert "logout" in imported
    assert "load_session_for_user" in imported


def test_app_keeps_voice_chat_contract_from_main():
    imported = _imported_names()
    source = _source()

    assert "speech_to_text" in imported
    assert "generate_audio_from_text" in imported
    assert "custom-chat-bar" in source
    assert "pending_chat_query" in source
    assert "st.session_state.input_key_counter" in source


def test_app_defines_login_dialog_and_auth_session_state():
    source = _source()
    functions = {node.name for node in ast.walk(_tree()) if isinstance(node, ast.FunctionDef)}

    assert "login_dialog" in functions
    assert '"user" not in st.session_state' in source
    assert "handle_google_callback" in source


def test_guest_card_is_clickable_login_trigger():
    source = _source()

    assert "guest-login-card-marker" in source
    assert 'st.button("Khách\\nĐĂNG NHẬP ĐỂ LƯU LỊCH SỬ", key="guest_login_card"' in source
    assert "if st.button(\"Khách\\nĐĂNG NHẬP ĐỂ LƯU LỊCH SỬ\"" in source
    assert "opacity: 0.80" not in source


def test_app_scopes_chat_history_to_logged_in_user():
    source = _source()

    assert "list_sessions(limit=15, user_id=user[\"id\"])" in source
    assert "load_session_for_user(sid, user[\"id\"])" in source
    assert "save_session(st.session_state.session_id, st.session_state.messages, user_id=user[\"id\"])" in source
    assert "rename_session(sid, new_name.strip(), user_id=user[\"id\"])" in source
    assert "toggle_bookmark(sid, user_id=user[\"id\"])" in source
    assert "delete_session(sid, user_id=user[\"id\"])" in source


def test_app_resets_anonymous_chat_after_successful_login():
    lines = _source().splitlines()
    login_success_lines = [
        index for index, line in enumerate(lines)
        if "st.session_state.user = user" in line
    ]

    assert len(login_success_lines) >= 3
    for index in login_success_lines:
        nearby = "\n".join(lines[index:index + 6])
        assert "st.session_state.session_id = new_session_id()" in nearby
        assert "st.session_state.messages = []" in nearby


def test_user_card_js_strings_escape_script_closing_tags():
    source = _source()

    assert "def _safe_js_string(value: str) -> str:" in source
    assert 'json.dumps(value).replace("</", "<\\\\/")' in source
    assert "display_name_js = _safe_js_string(raw_display_name)" in source
    assert "email_js = _safe_js_string(raw_email)" in source
    assert "avatar_letter_js = _safe_js_string(avatar_letter)" in source
