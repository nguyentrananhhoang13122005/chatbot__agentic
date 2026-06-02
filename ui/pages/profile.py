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
            <div style="font-size: 48px; margin-bottom: 16px;">🔒</div>
            <h2>Vui lòng đăng nhập</h2>
            <p>Bạn cần đăng nhập để xem hồ sơ cá nhân và lịch sử tra cứu trường.</p>
        </div>
        """, unsafe_allow_html=True)
        col_l, col_c, col_r = st.columns([1, 1, 1])
        with col_c:
            if st.button("🔑 Đăng nhập ngay", type="primary", use_container_width=True):
                login_dialog()
        return

    # Header
    col_back, col_title = st.columns([0.15, 0.85])
    with col_back:
        if st.button("← Trang chủ", key="profile_back_home"):
            st.session_state.page = "home"
            st.rerun()
    with col_title:
        st.markdown("## 👤 Hồ sơ cá nhân")

    # ─── CARD THÔNG TIN CÁ NHÂN ───
    display_name = user.get("display_name") or "Người dùng"
    email = user.get("email") or ""
    avatar_letter = display_name[0].upper() if display_name else "U"
    auth_provider = user.get("auth_provider", "email")
    provider_label = "Google" if auth_provider == "google" else "Email"
    provider_icon = "🔵" if auth_provider == "google" else "📧"
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
                {'&nbsp;·&nbsp;📅 Tham gia: ' + created_display if created_display else ''}
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
        <span class="profile-section-icon">🏛️</span>
        <span class="profile-section-title">Trường ĐH đã tra cứu</span>
        <span class="profile-section-count">{uni_count} trường</span>
    </div>
    """, unsafe_allow_html=True)

    if not universities:
        st.markdown("""
        <div class="uni-empty-state anim-fade-up anim-delay-2">
            <div style="font-size: 40px; margin-bottom: 12px;">📚</div>
            <p><strong>Chưa có trường nào.</strong></p>
            <p>Hãy bắt đầu trò chuyện và tra cứu thông tin tuyển sinh để thấy lịch sử ở đây!</p>
        </div>
        """, unsafe_allow_html=True)
        _, c_chat, _ = st.columns([1, 1, 1])
        with c_chat:
            if st.button("💬 Bắt đầu tra cứu", type="primary", use_container_width=True, key="profile_start_chat"):
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
                <span class="uni-history-icon">🏛️</span>
                <div class="uni-history-details">
                    <div class="uni-history-name">{school_name}</div>
                    {query_html}
                    <div class="uni-history-time">🕐 {time_display}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Action buttons
        col_ask, col_del = st.columns([1, 1])
        with col_ask:
            if st.button("💬 Hỏi tiếp", key=f"uni_ask_{idx}", use_container_width=True, type="secondary"):
                st.session_state.page = "chat"
                st.session_state.pending_query = f"Cho tôi biết thêm về trường {school_name}"
                st.rerun()
        with col_del:
            if st.session_state.get(f"confirm_uni_del_{idx}"):
                cd1, cd2 = st.columns(2)
                if cd1.button("⚠️ Xác nhận", key=f"cf_uni_del_{idx}", use_container_width=True):
                    delete_searched_university(user["id"], school_name)
                    st.session_state.pop(f"confirm_uni_del_{idx}", None)
                    st.rerun()
                if cd2.button("↩️ Hủy", key=f"cc_uni_del_{idx}", use_container_width=True):
                    st.session_state.pop(f"confirm_uni_del_{idx}", None)
                    st.rerun()
            else:
                if st.button("🗑️ Xóa", key=f"uni_del_{idx}", use_container_width=True, type="secondary"):
                    st.session_state[f"confirm_uni_del_{idx}"] = True
                    st.rerun()

    # ─── NÚT XÓA TOÀN BỘ ───
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    if st.session_state.get("confirm_clear_all_unis"):
        st.warning(f"Bạn có chắc muốn xóa toàn bộ **{uni_count} trường** khỏi lịch sử tra cứu?")
        c1, c2 = st.columns(2)
        if c1.button("⚠️ Xác nhận xóa tất cả", key="cf_clear_unis", use_container_width=True):
            deleted = clear_searched_universities(user["id"])
            st.session_state.pop("confirm_clear_all_unis", None)
            st.toast(f"✅ Đã xóa {deleted} trường khỏi lịch sử.")
            st.rerun()
        if c2.button("↩️ Hủy", key="cc_clear_unis", use_container_width=True):
            st.session_state.pop("confirm_clear_all_unis", None)
            st.rerun()
    else:
        if st.button("🧹 Xóa toàn bộ lịch sử tra cứu", key="clear_all_unis", use_container_width=True, type="secondary"):
            st.session_state.confirm_clear_all_unis = True
            st.rerun()

