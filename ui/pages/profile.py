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


def render_profile_page():
    user = st.session_state.get("user")

    # Guard: yêu cầu đăng nhập
    if not user:
        st.markdown("""
        <div class="profile-login-prompt anim-fade-up">
            <div class="profile-lock-icon" style="font-size: 48px; margin-bottom: 16px; color: var(--text-secondary);">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-lock"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            </div>
            <h2>Vui lòng đăng nhập</h2>
            <p>Bạn cần đăng nhập để xem hồ sơ cá nhân và lịch sử tra cứu trường.</p>
        </div>
        """, unsafe_allow_html=True)
        col_l, col_c, col_r = st.columns([1, 1, 1])
        with col_c:
            if st.button("Đăng nhập ngay", icon=":material/login:", type="primary", use_container_width=True):
                login_dialog()
        return

    # Header
    col_back, col_title = st.columns([0.15, 0.85])
    with col_back:
        if st.button("Trang chủ", icon=":material/arrow_back:", key="profile_back_home"):
            st.session_state.page = "home"
            st.rerun()
    with col_title:
        st.markdown("## 👤 Hồ sơ cá nhân")

    # ─── CARD THÔNG TIN CÁ NHÂN ───
    display_name = user.get("display_name") or "Người dùng"
    email = user.get("email") or ""
    avatar_letter = display_name[0].upper() if display_name else "U"
    google_icon_svg = '<svg width="14" height="14" viewBox="0 0 24 24" style="vertical-align: middle; margin-right: 4px; fill: currentColor;"><path d="M12.24 10.285V14.4h6.887c-.648 2.41-2.519 4.2-5.137 4.2a5.7 5.7 0 0 1-5.7-5.7 5.7 5.7 0 0 1 5.7-5.7c2.49 0 4.548 1.83 5.378 4.2h4.296C22.68 5.61 17.88 2 12.24 2 6.585 2 2 6.585 2 12.24s4.585 10.24 10.24 10.24c5.79 0 10.428-4.14 10.428-10.24 0-.66-.075-1.35-.195-1.955H12.24z"/></svg>'
    mail_icon_svg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 4px;"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>'
    provider_icon = google_icon_svg if auth_provider == "google" else mail_icon_svg
    created_at = user.get("created_at", "")
    created_display = ""
    if created_at:
        try:
            dt = datetime.datetime.fromisoformat(created_at.replace("Z", ""))
            created_display = dt.strftime("%d/%m/%Y")
        except Exception:
            created_display = created_at[:10]

    st.markdown(f"""
    <div class="profile-header anim-fade-up">
        <div class="profile-avatar">{avatar_letter}</div>
        <div class="profile-info">
            <div class="profile-name">{display_name}</div>
            <div class="profile-email">{email}</div>
            <div class="profile-meta">
                {provider_icon} {provider_label}
                {'&nbsp;·&nbsp;<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 4px; margin-left: 2px;"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>Tham gia: ' + created_display if created_display else ''}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ─── LỊCH SỬ TRƯỜNG ĐH ĐÃ TRA CỨU ───
    universities = list_searched_universities(user["id"], limit=50)
    uni_count = len(universities)

    st.markdown(f"""
    <div class="profile-section-header anim-fade-up anim-delay-1">
        <span class="profile-section-icon" style="vertical-align: middle; margin-right: 4px;"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-school"><path d="M12 22v-4"/><path d="M14 22v-4"/><path d="M2 22h20"/><path d="M22 18H2v-4h20v4z"/><path d="m12 2-10 4v3h20V6l-10-4z"/><path d="M6 18v-4"/><path d="M10 18v-4"/><path d="M14 18v-4"/><path d="M18 18v-4"/></svg></span>
        <span class="profile-section-title">Trường ĐH đã tra cứu</span>
        <span class="profile-section-count">{uni_count} trường</span>
    </div>
    """, unsafe_allow_html=True)

    if not universities:
        st.markdown("""
        <div class="uni-empty-state anim-fade-up anim-delay-2">
            <div class="profile-empty-icon" style="font-size: 40px; margin-bottom: 12px; color: var(--text-secondary);">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-book-open"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
            </div>
            <p><strong>Chưa có trường nào.</strong></p>
            <p>Hãy bắt đầu trò chuyện và tra cứu thông tin tuyển sinh để thấy lịch sử ở đây!</p>
        </div>
        """, unsafe_allow_html=True)
        _, c_chat, _ = st.columns([1, 1, 1])
        with c_chat:
            if st.button("Bắt đầu tra cứu", icon=":material/chat:", type="primary", use_container_width=True, key="profile_start_chat"):
                st.session_state.page = "chat"
                st.rerun()
        return

    # Hiển thị danh sách trường
    for idx, uni in enumerate(universities):
        school_name = uni["school_name"]
        query_text = uni.get("query_text", "")
        searched_at = uni.get("searched_at", "")

        # Format thời gian
        time_display = ""
        if searched_at:
            try:
                dt = datetime.datetime.fromisoformat(searched_at.replace("Z", ""))
                now = datetime.datetime.now()
                delta = (now.date() - dt.date()).days
                if delta == 0:
                    time_display = f"Hôm nay, {dt.strftime('%H:%M')}"
                elif delta == 1:
                    time_display = f"Hôm qua, {dt.strftime('%H:%M')}"
                elif delta < 7:
                    weekdays = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]
                    time_display = f"{weekdays[dt.weekday()]}, {dt.strftime('%H:%M')}"
                else:
                    time_display = dt.strftime("%d/%m/%Y, %H:%M")
            except Exception:
                time_display = searched_at[:10]

        # Card UI
        query_html = f'<div class="uni-history-query">&quot;{query_text}&quot;</div>' if query_text else ''
        st.markdown(f"""
        <div class="uni-history-card anim-fade-up" style="animation-delay: {min(idx * 0.05, 0.5)}s;">
            <div class="uni-history-header">
                <span class="uni-history-icon" style="vertical-align: middle; margin-right: 4px;"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-school"><path d="M12 22v-4"/><path d="M14 22v-4"/><path d="M2 22h20"/><path d="M22 18H2v-4h20v4z"/><path d="m12 2-10 4v3h20V6l-10-4z"/><path d="M6 18v-4"/><path d="M10 18v-4"/><path d="M14 18v-4"/><path d="M18 18v-4"/></svg></span>
                <div class="uni-history-details">
                    <div class="uni-history-name">{school_name}</div>
                    {query_html}
                    <div class="uni-history-time"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-clock" style="vertical-align: middle; margin-right: 4px;"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>{time_display}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Action buttons
        col_ask, col_del = st.columns([1, 1])
        with col_ask:
            if st.button("Hỏi tiếp", icon=":material/chat_bubble:", key=f"uni_ask_{idx}", use_container_width=True, type="secondary"):
                st.session_state.page = "chat"
                st.session_state.pending_query = f"Cho tôi biết thêm về trường {school_name}"
                st.rerun()
        with col_del:
            if st.session_state.get(f"confirm_uni_del_{idx}"):
                cd1, cd2 = st.columns(2)
                if cd1.button("Xác nhận", icon=":material/warning:", key=f"cf_uni_del_{idx}", use_container_width=True):
                    delete_searched_university(user["id"], school_name)
                    st.session_state.pop(f"confirm_uni_del_{idx}", None)
                    st.rerun()
                if cd2.button("Hủy", icon=":material/undo:", key=f"cc_uni_del_{idx}", use_container_width=True):
                    st.session_state.pop(f"confirm_uni_del_{idx}", None)
                    st.rerun()
            else:
                if st.button("Xóa", icon=":material/delete:", key=f"uni_del_{idx}", use_container_width=True, type="secondary"):
                    st.session_state[f"confirm_uni_del_{idx}"] = True
                    st.rerun()

    # ─── NÚT XÓA TOÀN BỘ ───
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    if st.session_state.get("confirm_clear_all_unis"):
        st.warning(f"Bạn có chắc muốn xóa toàn bộ **{uni_count} trường** khỏi lịch sử tra cứu?")
        c1, c2 = st.columns(2)
        if c1.button("Xác nhận xóa tất cả", icon=":material/warning:", key="cf_clear_unis", use_container_width=True):
            deleted = clear_searched_universities(user["id"])
            st.session_state.pop("confirm_clear_all_unis", None)
            st.toast("✅ Đã xóa lịch sử.")
            st.rerun()
        if c2.button("Hủy", icon=":material/undo:", key="cc_clear_unis", use_container_width=True):
            st.session_state.pop("confirm_clear_all_unis", None)
            st.rerun()
    else:
        if st.button("Xóa toàn bộ lịch sử tra cứu", icon="🧹", key="clear_all_unis", use_container_width=True, type="secondary"):
            st.session_state.confirm_clear_all_unis = True
            st.rerun()

