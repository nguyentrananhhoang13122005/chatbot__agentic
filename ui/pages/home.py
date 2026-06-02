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


def render_home_page():
    # Hero
    st.markdown("""
    <div class="hero anim-fade-up">
        <div class="badge">
            <span class="badge-dot"></span>
            Trợ lý tuyển sinh AI
        </div>
        <h1>
            Tìm trường <span class="hl-pink">mơ ước</span><br>
            của bạn, <span class="hl-blue">ngay hôm nay</span>.
        </h1>
        <p class="desc">
            Tra cứu điểm chuẩn · So sánh trường · Phân tích học bạ<br>
            Tất cả được hỗ trợ bởi trí tuệ nhân tạo.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Stats
    st.markdown("""
    <div class="stats anim-fade-up anim-delay-1">
        <div class="stat">
            <div class="stat-n count-200"></div>
            <div class="stat-l">Trường ĐH</div>
        </div>
        <div class="stat">
            <div class="stat-n count-5k"></div>
            <div class="stat-l">Ngành học</div>
        </div>
        <div class="stat">
            <div class="stat-n">∞</div>
            <div class="stat-l">Câu hỏi</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Feature Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="r-card anim-fade-up anim-delay-2">
            <div class="r-card-num">01</div>
            <div class="r-card-icon pink">🎯</div>
            <div class="r-card-title">Định hướng ngành</div>
            <div class="r-card-desc">Phân tích ngành nghề phù hợp dựa trên thế mạnh cá nhân.</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="r-card anim-fade-up anim-delay-3">
            <div class="r-card-num">02</div>
            <div class="r-card-icon blue">📊</div>
            <div class="r-card-title">Tra cứu điểm chuẩn</div>
            <div class="r-card-desc">Dữ liệu tuyển sinh cập nhật chính xác, dự báo cơ hội.</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="r-card anim-fade-up anim-delay-4">
            <div class="r-card-num">03</div>
            <div class="r-card-icon pink">✨</div>
            <div class="r-card-title">Phân tích học bạ AI</div>
            <div class="r-card-desc">Tải học bạ lên, AI đánh giá năng lực và chỉ ra cơ hội.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, c_score, _ = st.columns([1, 1, 1])
    with c_score:
        if st.button("📊 Phân tích Học bạ", use_container_width=True, type="primary"):
            st.session_state.page = "score_analysis"
            st.rerun()

