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


def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div class="sb-header">
            <div class="sb-logo">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-graduation-cap"><path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"/><path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5"/><path d="M21.5 12v6"/></svg>
            </div>
            <div class="sb-name">UniSearch</div>
            <div class="sb-tag">AI Platform</div>
        </div>
        """, unsafe_allow_html=True)

        user = st.session_state.get("user")
        if not user:
            st.markdown('<span class="guest-login-card-marker"></span>', unsafe_allow_html=True)
            if st.button("Khách\nĐĂNG NHẬP ĐỂ LƯU LỊCH SỬ", key="guest_login_card", use_container_width=True, type="secondary"):
                login_dialog()

        current_theme = st.session_state.get("theme", "light")
        toggle_icon = ":material/dark_mode:" if current_theme == "light" else ":material/light_mode:"
        toggle_label = "Chế độ tối" if current_theme == "light" else "Chế độ sáng"
        if st.button(toggle_label, icon=toggle_icon, key="theme_toggle", use_container_width=True, type="secondary"):
            new_theme = "dark" if current_theme == "light" else "light"
            st.session_state.theme = new_theme
            # Pre-set localStorage & transition class BEFORE rerun to prevent flash
            components.html(f"""
            <script>
            (function() {{
                try {{
                    var doc = window.parent.document;
                    var html = doc.documentElement;
                    html.classList.add('theme-transitioning');
                    html.setAttribute('data-theme', '{new_theme}');
                    localStorage.setItem('unisearch-theme', '{new_theme}');
                    setTimeout(function() {{
                        html.classList.remove('theme-transitioning');
                    }}, 400);
                }} catch(e) {{}}
            }})();
            </script>
            """, height=0, scrolling=False)
            st.rerun()

        # if st.button("＋ Phiên tư vấn mới", use_container_width=True, type="primary"):
        #     # Lưu phiên hiện tại trước khi tạo mới
        #     if user and st.session_state.messages:
        #         save_session(st.session_state.session_id, st.session_state.messages, user_id=user["id"])
        #     st.session_state.session_id = new_session_id()
        #     st.session_state.messages = []
        #     st.session_state.page = "chat"
        #     st.rerun()
        #
        # if st.button("💬 Trò chuyện hiện tại", use_container_width=True, type="secondary"):
        #     st.session_state.page = "chat"
        #     st.rerun()

        # ─── LỊCH SỬ GẦN ĐÂY (từ SQLite) ───
        if user:
            st.markdown('<div class="sb-section">Lịch sử gần đây</div>', unsafe_allow_html=True)

            recent_sessions = list_sessions(limit=15, user_id=user["id"])
            if not recent_sessions:
                st.caption("Chưa có lịch sử chat.")
            else:
                for sess in recent_sessions:
                    sid = sess["id"]
                    is_current = (sid == st.session_state.get("session_id"))

                    with st.container():
                        st.markdown(f'<div class="hist-row-marker {"active" if is_current else ""}"></div>', unsafe_allow_html=True)

                        # Tính toán thời gian trước khi render
                        time_str = ""
                        try:
                            dt_str = str(sess["updated_at"]).replace("Z", "")
                            dt = datetime.datetime.fromisoformat(dt_str)
                            now = datetime.datetime.now()
                            if dt.date() == now.date():
                                time_str = f"Hôm nay, {dt.strftime('%H:%M')}"
                            elif dt.date() == (now - datetime.timedelta(days=1)).date():
                                time_str = f"Hôm qua, {dt.strftime('%H:%M')}"
                            else:
                                time_str = dt.strftime("%d/%m/%Y, %H:%M")
                        except Exception:
                            time_str = ""

                        if st.session_state.get("rename_sid") == sid:
                            new_name = st.text_input("Đổi tên", value=sess['title'], key=f"rn_in_{sid}", label_visibility="collapsed")
                            c1, c2 = st.columns(2)
                            if c1.button("Lưu", key=f"sv_{sid}", use_container_width=True):
                                if new_name.strip():
                                    rename_session(sid, new_name.strip(), user_id=user["id"])
                                st.session_state.rename_sid = None
                                st.rerun()
                            if c2.button("Hủy", key=f"cc_{sid}", use_container_width=True):
                                st.session_state.rename_sid = None
                                st.rerun()
                        else:
                            col1, col2 = st.columns([8, 1.5], vertical_alignment="center")
                            with col1:
                                icon_param = ":material/push_pin:" if sess["bookmarked"] else None
                                # Giới hạn độ dài tiêu đề
                                display_title = sess['title']
                                if len(display_title) > 25: display_title = display_title[:22] + "..."

                                if st.button(display_title, icon=icon_param, key=f"load_{sid}", use_container_width=True):
                                    if user and st.session_state.messages:
                                        save_session(st.session_state.session_id, st.session_state.messages, user_id=user["id"])
                                    st.session_state.session_id = sid
                                    st.session_state.messages = load_session_for_user(sid, user["id"])
                                    st.session_state.page = "chat"
                                    st.rerun()
                            with col2:
                                with st.popover("⋮", use_container_width=True):
                                    pin_label = "Bỏ ghim" if sess["bookmarked"] else "Ghim"
                                    if st.button(pin_label, icon=":material/push_pin:", key=f"bm_{sid}", use_container_width=True):
                                        toggle_bookmark(sid, user_id=user["id"])
                                        st.rerun()
                                    if st.button("Đổi tên", icon=":material/edit:", key=f"rn_btn_{sid}", use_container_width=True):
                                        st.session_state.rename_sid = sid
                                        st.rerun()
                                    if st.session_state.get("confirm_delete_sid") == sid:
                                        st.warning("Bạn có chắc muốn xóa?")
                                        cd1, cd2 = st.columns(2)
                                        if cd1.button("Xác nhận", icon=":material/warning:", key=f"cf_del_{sid}", use_container_width=True):
                                            delete_session(sid, user_id=user["id"])
                                            st.session_state.pop("confirm_delete_sid", None)
                                            if sid == st.session_state.get("session_id"):
                                                st.session_state.session_id = new_session_id()
                                                st.session_state.messages = []
                                            st.rerun()
                                        if cd2.button("Hủy", icon=":material/undo:", key=f"cc_del_{sid}", use_container_width=True):
                                            st.session_state.pop("confirm_delete_sid", None)
                                            st.rerun()
                                    else:
                                        if st.button("Xóa", icon=":material/delete:", key=f"del_{sid}", use_container_width=True):
                                            st.session_state.confirm_delete_sid = sid
                                            st.rerun()

                        # Hiển thị thời gian NGOÀI khung border của history item
                        if time_str:
                            st.markdown(f'<div class="hist-time">{time_str}</div>', unsafe_allow_html=True)
        else:
            st.caption("💡 Đăng nhập để lưu và xem lại lịch sử chat.")

        # ─── HỆ THỐNG ───
        st.markdown('<div class="sb-section">Hệ thống</div>', unsafe_allow_html=True)
        st.caption("💡 Phiên chưa ghim sẽ tự động xóa sau 20 ngày")
        if user:
            if st.button("Xoá lịch sử của tôi", icon=":material/delete_sweep:", use_container_width=True, type="secondary"):
                for sess in list_sessions(limit=1000, user_id=user["id"]):
                    delete_session(sess["id"], user_id=user["id"])
                st.session_state.session_id = new_session_id()
                st.session_state.messages = []
                st.toast("✅ Đã xoá lịch sử chat của bạn.")
                st.rerun()

        # ─── BOTTOM USER PROFILE (sticky) ───
        if user:
            raw_display_name = user.get("display_name") or "Người dùng"
            raw_email = user.get("email") or ""
            avatar_letter = raw_display_name[0].upper() if raw_display_name else "U"
            display_name_js = _safe_js_string(raw_display_name)
            email_js = _safe_js_string(raw_email)
            avatar_letter_js = _safe_js_string(avatar_letter)

            st.markdown('<div class="sb-bottom-spacer"></div>', unsafe_allow_html=True)
            with st.popover(f"{raw_display_name}\n{raw_email}", use_container_width=True):
                if st.button("Hồ sơ của tôi", icon=":material/account_circle:", key="profile_btn", use_container_width=True):
                    st.session_state.page = "profile"
                    st.rerun()
                if st.button("Cài đặt", icon=":material/settings:", key="settings_btn", use_container_width=True):
                    st.toast("🚧 Tính năng đang phát triển.")
                if st.button("Đăng xuất", icon=":material/logout:", key="logout_popup_btn", use_container_width=True):
                    logout()
                    st.session_state.session_id = new_session_id()
                    st.session_state.messages = []
                    st.session_state.auth_toast = "👋 Đã đăng xuất."
                    st.rerun()

            # JS: Add CSS classes + data attributes to popover elements for reliable styling
            components.html(f"""
            <script>
            (function applyUserCard() {{
                try {{
                    var doc = window.parent.document;
                    // Find the popover button in the sidebar
                    var sidebar = doc.querySelector('[data-testid="stSidebar"]');
                    if (!sidebar) return setTimeout(applyUserCard, 300);

                    // Strategy: find ALL .stPopover buttons in sidebar, pick the one
                    // whose text content contains the user's display name
                    var allPopovers = sidebar.querySelectorAll('.stPopover');
                    var targetPopover = null;
                    var targetBtn = null;
                    for (var i = 0; i < allPopovers.length; i++) {{
                        var b = allPopovers[i].querySelector('button');
                        if (b && b.textContent && b.textContent.indexOf({display_name_js}) !== -1) {{
                            targetPopover = allPopovers[i];
                            targetBtn = b;
                            break;
                        }}
                    }}
                    if (!targetBtn) return setTimeout(applyUserCard, 300);

                    // Add CSS classes for reliable selector matching
                    targetBtn.classList.add('sb-user-card-btn');
                    targetPopover.classList.add('sb-user-popover');
                    // Add container class to the wrapper div for border-top
                    var wrapper = targetPopover.parentElement;
                    if (wrapper) wrapper.classList.add('sb-user-card-container');

                    // Set data attributes for CSS ::before and ::after content
                    targetBtn.setAttribute('data-avatar', {avatar_letter_js});
                    targetBtn.setAttribute('data-label', {display_name_js} + '\\n' + {email_js});

                    // Force-hide ALL inner elements (expand_more/expand_less icons, p, span)
                    function hideInnerElements(button) {{
                        var children = button.querySelectorAll('*');
                        for (var j = 0; j < children.length; j++) {{
                            children[j].style.cssText = 'display:none!important;visibility:hidden!important;width:0!important;height:0!important;overflow:hidden!important;position:absolute!important;font-size:0!important;';
                        }}
                    }}
                    hideInnerElements(targetBtn);

                    // MutationObserver: re-apply when Streamlit re-renders
                    var observer = new MutationObserver(function() {{
                        targetBtn.classList.add('sb-user-card-btn');
                        targetBtn.setAttribute('data-avatar', {avatar_letter_js});
                        targetBtn.setAttribute('data-label', {display_name_js} + '\\n' + {email_js});
                        hideInnerElements(targetBtn);
                    }});
                    observer.observe(targetBtn, {{ childList: true, subtree: true }});
                }} catch(e) {{ setTimeout(applyUserCard, 500); }}
            }})();
            </script>
            """, height=0, scrolling=False)

