import streamlit as st
import streamlit.components.v1 as components
import sys
import time

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from llm_client import validate_api_key
from chat_db import init_db, new_session_id, cleanup_old_sessions
from auth_db import init_auth_db
from auth import handle_google_callback, _consume_oauth_state

st.set_page_config(page_title="UniSearch AI", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# === KHỞI TẠO DB & DỌN DẸP TỰ ĐỘNG ===
init_db()
init_auth_db()
cleanup_old_sessions(days=20)

if "code" in st.query_params:
    received_state = st.query_params.get("state", "")
    # Module-level store survives session reset; fall back to session_state
    state_ok = _consume_oauth_state(received_state)
    if not state_ok:
        expected_state = st.session_state.pop("oauth_state", "")
        state_ok = bool(received_state and received_state == expected_state)
    else:
        st.session_state.pop("oauth_state", None)
    if not state_ok:
        st.session_state.auth_toast = "⚠️ Phiên đăng nhập không hợp lệ. Vui lòng thử lại."
    else:
        user = handle_google_callback(st.query_params["code"])
        if user:
            st.session_state.user = user
            st.session_state.session_id = new_session_id()
            st.session_state.messages = []
            st.session_state.auth_toast = f"✅ Chào mừng {user['display_name']}!"
        else:
            st.session_state.auth_toast = "Không thể đăng nhập bằng Google. Vui lòng thử lại."
    st.query_params.clear()
    st.rerun()


@st.cache_data(ttl=600, show_spinner=False)
def _cached_validate_api_key_v2():
    return validate_api_key()


if "page" not in st.session_state:
    st.session_state.page = "home"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = new_session_id()
if "theme" not in st.session_state:
    st.session_state.theme = "light"
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.get("auth_toast"):
    st.toast(st.session_state.pop("auth_toast"))


from ui.styles import load_custom_css
from ui.components import render_sidebar, render_home_page, render_chat_page, render_score_analysis_page, render_profile_page, login_dialog
load_custom_css()
api_key_valid, api_key_error = _cached_validate_api_key_v2()
if not api_key_valid:
    st.warning(api_key_error)
render_sidebar()
if st.session_state.page == "home":
    render_home_page()
elif st.session_state.page == "score_analysis":
    render_score_analysis_page()
elif st.session_state.page == "profile":
    render_profile_page()
else:
    render_chat_page()
if not st.session_state.get("user"):
    st.markdown('<div class="login-btn-container"></div>', unsafe_allow_html=True)
    if st.button("Đăng nhập", key="top_login_btn"):
        login_dialog()

# === THEME: Inject JS via components.html (st.markdown strips <script> tags) ===
_current_theme = st.session_state.get("theme", "light")
components.html(f"""
<script>
    (function() {{
        var theme = '{_current_theme}';
        function applyTheme() {{
            try {{
                var doc = window.parent.document;
                doc.documentElement.setAttribute('data-theme', theme);
                localStorage.setItem('unisearch-theme', theme);
            }} catch(e) {{}}
        }}
        applyTheme();
        setTimeout(applyTheme, 100);
        setTimeout(applyTheme, 500);
    }})();
</script>
""", height=0, scrolling=False)

