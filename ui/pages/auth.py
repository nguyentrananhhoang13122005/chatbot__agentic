import streamlit as st
import json
import io
import datetime
import secrets
import html
import streamlit.components.v1 as components
from auth import get_google_auth_url, login_user, register_user, logout
from chat_db import (
    new_session_id, save_session, list_sessions, load_session_for_user,
    delete_session, toggle_bookmark, rename_session, format_session_date,
    list_searched_universities, delete_searched_university, clear_searched_universities,
)
from core.query_processor import _process_query
from utils.audio_utils import generate_audio_from_text
from streamlit_mic_recorder import speech_to_text

# Local imports after split
from ui.pages.utils import _safe_js_string, _positive_session_float, _to_float
from ui.pages.auth import login_dialog


@st.dialog("Đăng nhập hoặc đăng ký", width="small")
def login_dialog():
    from auth import _store_oauth_state
    state = secrets.token_urlsafe(32)
    st.session_state.oauth_state = state
    _store_oauth_state(state)
    google_auth_url = get_google_auth_url(state=state)
    st.markdown("**Đăng nhập nhanh**")
    st.link_button("🔵 Tiếp tục bằng Google", google_auth_url, use_container_width=True)
    st.divider()
    st.markdown("**Hoặc dùng email**")
    tab_login, tab_register = st.tabs(["Đăng nhập", "Đăng ký"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Mật khẩu", type="password", key="login_pass")
        if st.button("Đăng nhập", key="btn_login", type="primary", use_container_width=True):
            user, error = login_user(email, password)
            if error:
                st.error(error)
            else:
                st.session_state.user = user
                st.session_state.session_id = new_session_id()
                st.session_state.messages = []
                st.session_state.auth_toast = f"✅ Chào mừng {user['display_name']}!"
                st.rerun(scope="app")

    with tab_register:
        reg_name = st.text_input("Họ và tên", key="reg_name")
        reg_email = st.text_input("Email", key="reg_email")
        reg_pass = st.text_input("Mật khẩu", type="password", key="reg_pass")
        reg_pass2 = st.text_input("Xác nhận mật khẩu", type="password", key="reg_pass2")
        if st.button("Đăng ký", key="btn_register", type="primary", use_container_width=True):
            if reg_pass != reg_pass2:
                st.error("Mật khẩu xác nhận không khớp.")
            else:
                user, error = register_user(reg_email, reg_name, reg_pass)
                if error:
                    st.error(error)
                else:
                    st.session_state.user = user
                    st.session_state.session_id = new_session_id()
                    st.session_state.messages = []
                    st.session_state.auth_toast = f"✅ Chào mừng {user['display_name']}!"
                    st.rerun(scope="app")

