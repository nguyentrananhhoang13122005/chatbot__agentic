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


def render_chat_page():
    if st.button("🏠 Quay lại Trang chủ", type="secondary"):
        st.session_state.page = "home"
        st.rerun()

    st.markdown('<div class="chat-hdr"><span class="chat-dot"></span> Tuyển sinh AI</div>', unsafe_allow_html=True)

    uploaded_cv_widget = st.file_uploader("📥 Tải lên Học bạ / Hồ sơ (Ảnh hoặc PDF):", type=["jpg", "jpeg", "png", "pdf"])

    # === CACHE FILE VÀO SESSION_STATE ===
    # BUG FIX: Streamlit giữ widget qua re-render → uploaded_cv_widget.read() lần 2
    # trả về b'' (stream đã đọc hết) → overwrite cache tốt bằng bytes rỗng.
    # Giải pháp: chỉ đọc bytes khi file THỰC SỰ MỚI (fingerprint = tên + size).
    if uploaded_cv_widget is not None:
        file_fingerprint = f"{uploaded_cv_widget.name}_{uploaded_cv_widget.size}"
        if st.session_state.get('cached_cv_fingerprint') != file_fingerprint:
            # File mới hoặc chưa cache → đọc bytes và lưu
            raw_bytes = uploaded_cv_widget.read()
            if raw_bytes:  # chỉ lưu nếu đọc được dữ liệu thật
                st.session_state['cached_cv_bytes']       = raw_bytes
                st.session_state['cached_cv_name']        = uploaded_cv_widget.name
                st.session_state['cached_cv_fingerprint'] = file_fingerprint
                st.success(f"✅ Đã tải lên: **{uploaded_cv_widget.name}** — Sẵn sàng phân tích!")
        else:
            # Cùng file, đã cache → chỉ hiển thị thông báo
            st.success(f"✅ Học bạ đang hoạt động: **{uploaded_cv_widget.name}**")

    # Tái tạo file object từ cache để dùng cho OCR (fresh BytesIO mỗi lần render)
    uploaded_cv = None
    if st.session_state.get('cached_cv_bytes'):
        cv_bytes    = st.session_state['cached_cv_bytes']
        cv_name     = st.session_state.get('cached_cv_name', 'hocba.jpg')
        uploaded_cv = io.BytesIO(cv_bytes)
        uploaded_cv.name = cv_name  # Gắn tên để doc_file() nhận diện đúng định dạng (.jpg/.pdf)
        if uploaded_cv_widget is None:
            col_info, col_clear = st.columns([4, 1])
            col_info.info(f"📎 Đang dùng học bạ đã tải: **{cv_name}**")
            if col_clear.button("🗑️ Xóa file", key="clear_cv", type="secondary"):
                for k in ['cached_cv_bytes', 'cached_cv_name', 'cached_cv_fingerprint']:
                    st.session_state.pop(k, None)
                st.rerun()


    if len(st.session_state.messages) == 0 and "pending_query" not in st.session_state:
        with st.chat_message("assistant", avatar="assistant"):
            st.write("Chào bạn! 👋 Mình là trợ lý tuyển sinh AI. Bạn muốn tìm hiểu về trường nào, ngành nào, hay so sánh điểm chuẩn hôm nay?")
            st.write("")
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("Top 5 CNTT", type="secondary"):
                st.session_state.pending_query = "Top 5 trường CNTT"
                st.rerun()
            if c2.button("ĐC Ngoại thương", type="secondary"):
                st.session_state.pending_query = "Điểm chuẩn Ngoại thương"
                st.rerun()
            if c3.button("Học phí RMIT", type="secondary"):
                st.session_state.pending_query = "Học phí RMIT"
                st.rerun()
            if c4.button("HUST vs KHTN", type="secondary"):
                st.session_state.pending_query = "So sánh Bách Khoa và KHTN"
                st.rerun()

    # Hiển thị lịch sử hội thoại
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"], avatar="assistant" if msg["role"] == "assistant" else "user"):
            st.write(msg["content"])
            if msg["role"] == "assistant":
                if st.button("🔊 Nghe", key=f"tts_{i}"):
                    with st.spinner("Đang tạo giọng nói..."):
                        audio_bytes = generate_audio_from_text(msg["content"])
                        if audio_bytes:
                            st.audio(audio_bytes, format='audio/mp3', autoplay=True)

    # Xử lý câu hỏi đang chờ (từ nút gợi ý)
    if "pending_query" in st.session_state:
        pending = st.session_state.pending_query
        del st.session_state.pending_query
        st.session_state.messages.append({"role": "user", "content": pending})
        with st.chat_message("user", avatar="user"):
            st.write(pending)
        with st.chat_message("assistant", avatar="assistant"):
            response = _process_query(pending, uploaded_cv)
        if response:
            st.session_state.messages.append({"role": "assistant", "content": str(response)})
        # === AUTO-SAVE ===
        user = st.session_state.get("user")
        if user and st.session_state.messages:
            save_session(st.session_state.session_id, st.session_state.messages, user_id=user["id"])
        st.rerun()

    # === CUSTOM CHAT INPUT BAR: text_input + mic + send button in one row ===
    if "input_key_counter" not in st.session_state:
        st.session_state.input_key_counter = 0

    with st.container():
        col_input, col_mic, col_send = st.columns([12, 1, 1], vertical_alignment="bottom")
        with col_input:
            text_input = st.text_input(
                "chat_input",
                placeholder="Nhập câu hỏi... (VD: Điểm chuẩn Bách Khoa 2024?)",
                label_visibility="collapsed",
                key=f"custom_chat_input_{st.session_state.input_key_counter}"
            )
        with col_mic:
            voice_input = speech_to_text(
                language='vi-VN',
                start_prompt='🎙️',
                stop_prompt='🛑',
                use_container_width=False,
                just_once=True,
                key='STT'
            )
        with col_send:
            st.markdown('<span id="chat-bar-anchor"></span>', unsafe_allow_html=True)
            send_clicked = st.button("↑", key="send_btn", use_container_width=True)

    # Determine final query: voice > button click > Enter key
    final_query = None
    if voice_input:
        final_query = voice_input
    elif text_input and (send_clicked or st.session_state.get("_prev_input") != text_input):
        final_query = text_input
    st.session_state["_prev_input"] = text_input if text_input else ""

    # If new query detected, save it and clear input IMMEDIATELY (before processing)
    if final_query:
        st.session_state["pending_chat_query"] = final_query
        st.session_state.input_key_counter += 1  # Force text_input to reset
        st.rerun()

    # Process pending query (runs on the NEXT rerun, after input is already cleared)
    if "pending_chat_query" in st.session_state:
        query = st.session_state.pending_chat_query
        del st.session_state.pending_chat_query
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user", avatar="user"):
            st.write(query)
        with st.chat_message("assistant", avatar="assistant"):
            response = _process_query(query, uploaded_cv)
        if response:
            st.session_state.messages.append({"role": "assistant", "content": str(response)})
        # === AUTO-SAVE ===
        user = st.session_state.get("user")
        if user and st.session_state.messages:
            save_session(st.session_state.session_id, st.session_state.messages, user_id=user["id"])
        st.rerun()

