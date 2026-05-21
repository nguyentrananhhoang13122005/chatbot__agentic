import streamlit as st
import json
import io
import datetime
import secrets
import streamlit.components.v1 as components
from auth import get_google_auth_url, login_user, register_user, logout
from chat_db import new_session_id, save_session, list_sessions, load_session_for_user, delete_session, toggle_bookmark, rename_session, format_session_date
from core.query_processor import _process_query
from utils.audio_utils import generate_audio_from_text
from streamlit_mic_recorder import speech_to_text

def _safe_js_string(value: str) -> str:
    return json.dumps(value).replace("</", "<\\/")


@st.dialog("Đăng nhập hoặc đăng ký", width="small")
def login_dialog():
    from app import _store_oauth_state
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


# === SIDEBAR ===
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div class="sb-header">
            <div class="sb-logo">🎓</div>
            <div class="sb-name">UniSearch</div>
            <div class="sb-tag">AI Platform</div>
        </div>
        """, unsafe_allow_html=True)

        user = st.session_state.get("user")
        if not user:
            st.markdown('<span class="guest-login-card-marker"></span>', unsafe_allow_html=True)
            if st.button("Khách\nĐĂNG NHẬP ĐỂ LƯU LỊCH SỬ", key="guest_login_card", use_container_width=True, type="secondary"):
                login_dialog()

        # === THEME TOGGLE ===
        current_theme = st.session_state.get("theme", "light")
        toggle_icon = "🌙" if current_theme == "light" else "☀️"
        toggle_label = "Chế độ tối" if current_theme == "light" else "Chế độ sáng"
        if st.button(f"{toggle_icon} {toggle_label}", key="theme_toggle", use_container_width=True, type="secondary"):
            st.session_state.theme = "dark" if current_theme == "light" else "light"
            st.rerun()

        if st.button("＋ Phiên tư vấn mới", use_container_width=True, type="primary"):
            # Lưu phiên hiện tại trước khi tạo mới
            if user and st.session_state.messages:
                save_session(st.session_state.session_id, st.session_state.messages, user_id=user["id"])
            st.session_state.session_id = new_session_id()
            st.session_state.messages = []
            st.session_state.page = "chat"
            st.rerun()

        if st.button("💬 Trò chuyện hiện tại", use_container_width=True, type="secondary"):
            st.session_state.page = "chat"
            st.rerun()

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
                                pin_icon = "📌 " if sess["bookmarked"] else ""
                                # Giới hạn độ dài tiêu đề
                                display_title = sess['title']
                                if len(display_title) > 25: display_title = display_title[:22] + "..."

                                btn_label = f"{pin_icon}{display_title}"

                                if st.button(btn_label, key=f"load_{sid}", use_container_width=True):
                                    if user and st.session_state.messages:
                                        save_session(st.session_state.session_id, st.session_state.messages, user_id=user["id"])
                                    st.session_state.session_id = sid
                                    st.session_state.messages = load_session_for_user(sid, user["id"])
                                    st.session_state.page = "chat"
                                    st.rerun()
                            with col2:
                                with st.popover("⋮", use_container_width=True):
                                    pin_label = "Bỏ ghim" if sess["bookmarked"] else "Ghim"
                                    if st.button(f"📌 {pin_label}", key=f"bm_{sid}", use_container_width=True):
                                        toggle_bookmark(sid, user_id=user["id"])
                                        st.rerun()
                                    if st.button("✏️ Đổi tên", key=f"rn_btn_{sid}", use_container_width=True):
                                        st.session_state.rename_sid = sid
                                        st.rerun()
                                    if st.session_state.get("confirm_delete_sid") == sid:
                                        st.warning("Bạn có chắc muốn xóa?")
                                        cd1, cd2 = st.columns(2)
                                        if cd1.button("⚠️ Xác nhận", key=f"cf_del_{sid}", use_container_width=True):
                                            delete_session(sid, user_id=user["id"])
                                            st.session_state.pop("confirm_delete_sid", None)
                                            if sid == st.session_state.get("session_id"):
                                                st.session_state.session_id = new_session_id()
                                                st.session_state.messages = []
                                            st.rerun()
                                        if cd2.button("↩️ Hủy", key=f"cc_del_{sid}", use_container_width=True):
                                            st.session_state.pop("confirm_delete_sid", None)
                                            st.rerun()
                                    else:
                                        if st.button("🗑️ Xóa", key=f"del_{sid}", use_container_width=True):
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
            if st.button("🧹 Xoá lịch sử của tôi", use_container_width=True, type="secondary"):
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
                if st.button("⚙️ Cài đặt", key="settings_btn", use_container_width=True):
                    st.toast("🚧 Tính năng đang phát triển.")
                if st.button("🚪 Đăng xuất", key="logout_popup_btn", use_container_width=True):
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


# === HOME PAGE ===
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
    _, c_chat, c_score, _ = st.columns([0.8, 1, 1, 0.8])
    with c_chat:
        if st.button("💬 Bắt đầu trò chuyện", use_container_width=True, type="primary"):
            st.session_state.page = "chat"
            st.rerun()
    with c_score:
        if st.button("📊 Phân tích Học bạ", use_container_width=True, type="secondary"):
            st.session_state.page = "score_analysis"
            st.rerun()


# === SCORE ANALYSIS PAGE ===
def render_score_analysis_page():
    from utils.score_calculator import (
        MAIN_SUBJECTS, normalize_scores, get_top_k_combinations,
        get_strength_analysis, format_combination_display, MIN_THRESHOLD,
    )
    from agents.match_maker import find_top_k_schools, generate_analysis_stream
    from agents.counselor import doc_file, parse_scores_to_json

    # --- Init session state ---
    if "sa_step" not in st.session_state:
        st.session_state.sa_step = 1
    if "sa_scores" not in st.session_state:
        st.session_state.sa_scores = {}
    if "sa_result" not in st.session_state:
        st.session_state.sa_result = None

    # --- Header ---
    col_back, col_title = st.columns([0.15, 0.85])
    with col_back:
        if st.button("← Trang chủ", key="sa_back_home"):
            st.session_state.page = "home"
            st.session_state.sa_step = 1
            st.rerun()
    with col_title:
        st.markdown("## 📊 Phân tích Học bạ & Gợi ý Trường")

    # --- Step Wizard Bar ---
    step = st.session_state.sa_step
    steps = ["① Nhập điểm", "② Phương thức", "③ Kết quả AI"]
    step_cols = st.columns(3)
    for i, (sc, label) in enumerate(zip(step_cols, steps)):
        with sc:
            if i + 1 < step:
                st.success(f"✅ {label}")
            elif i + 1 == step:
                st.info(f"👉 {label}")
            else:
                st.markdown(f"⬜ {label}")

    st.divider()

    # ========== STEP 1: NHẬP ĐIỂM ==========
    if step == 1:
        st.markdown("### 📝 Nhập điểm từng môn")

        # --- OCR Upload ---
        with st.expander("📸 Tải ảnh Học bạ để AI tự nhận diện (tùy chọn)", expanded=False):
            uploaded_file = st.file_uploader(
                "Chọn ảnh hoặc PDF học bạ:",
                type=["jpg", "jpeg", "png", "pdf"],
                key="sa_file_upload"
            )
            if uploaded_file and st.button("🔍 AI Quét tự động", key="sa_ocr_btn", type="primary"):
                with st.spinner("⏳ Đang quét ảnh bằng AI..."):
                    raw_ocr = doc_file(uploaded_file)
                    if raw_ocr and not raw_ocr.startswith("[LOI"):
                        parsed = parse_scores_to_json(raw_ocr)
                        if parsed:
                            st.session_state.sa_scores = parsed
                            st.success(f"✅ AI đã nhận diện được {len(parsed)} môn! Kiểm tra và chỉnh sửa bên dưới.")
                            st.rerun()
                        else:
                            st.warning("⚠️ AI không trích xuất được điểm. Vui lòng nhập thủ công.")
                    else:
                        st.error("❌ Không đọc được file. Vui lòng thử lại hoặc nhập thủ công.")

        st.markdown("---")
        st.markdown("**Nhập điểm thủ công** *(thang 10)*")

        # --- Score Input Form ---
        existing = st.session_state.sa_scores
        input_scores = {}

        col_left, col_right = st.columns(2)
        for i, subj in enumerate(MAIN_SUBJECTS):
            default_val = existing.get(subj, 0.0)
            target_col = col_left if i < 5 else col_right
            with target_col:
                val = st.number_input(
                    subj,
                    min_value=0.0,
                    max_value=10.0,
                    value=float(default_val),
                    step=0.1,
                    format="%.1f",
                    key=f"sa_input_{subj}",
                )
                input_scores[subj] = val

        # --- Ngoại ngữ phụ (tùy chọn) ---
        from utils.score_calculator import EXTRA_LANGUAGES
        with st.expander("🌐 Ngoại ngữ khác (Nhật, Trung, Pháp, Đức, Nga) — *bấm để mở*"):
            st.caption("Nếu bạn học ngoại ngữ 2 hoặc thi ngoại ngữ khác ngoài Tiếng Anh, nhập điểm để mở thêm tổ hợp khối D.")
            lang_col1, lang_col2 = st.columns(2)
            for j, lang in enumerate(EXTRA_LANGUAGES):
                default_lang = existing.get(lang, 0.0)
                target_lang_col = lang_col1 if j < 3 else lang_col2
                with target_lang_col:
                    lang_val = st.number_input(
                        lang,
                        min_value=0.0,
                        max_value=10.0,
                        value=float(default_lang),
                        step=0.1,
                        format="%.1f",
                        key=f"sa_input_{lang}",
                    )
                    if lang_val > 0:
                        input_scores[lang] = lang_val

        # --- Năng khiếu (tùy chọn) ---
        from utils.score_calculator import EXTRA_APTITUDE
        with st.expander("🎨 Môn Năng khiếu (Vẽ, Âm nhạc, Thể thao...) — *bấm để mở*"):
            st.caption("Nhập điểm các môn năng khiếu để xét tuyển vào các khối V, H, M, N, T, S, R.")
            apt_col1, apt_col2 = st.columns(2)
            for j, apt in enumerate(EXTRA_APTITUDE):
                default_apt = existing.get(apt, 0.0)
                target_apt_col = apt_col1 if j % 2 == 0 else apt_col2
                with target_apt_col:
                    apt_val = st.number_input(
                        apt,
                        min_value=0.0,
                        max_value=10.0,
                        value=float(default_apt),
                        step=0.1,
                        format="%.1f",
                        key=f"sa_input_{apt}",
                    )
                    if apt_val > 0:
                        input_scores[apt] = apt_val

        st.markdown("---")

        # --- Điểm ưu tiên (MAJOR #2: Tách KV + ĐT theo Quy chế 2026) ---
        from utils.score_calculator import PRIORITY_KV, PRIORITY_UT, calculate_total_raw_bonus

        st.markdown("**Điểm ưu tiên** *(theo Quy chế 2026 — Bộ GD&ĐT)*")
        kv_col, ut_col = st.columns(2)
        with kv_col:
            kv_options = list(PRIORITY_KV.keys())
            kv_labels = [
                f"KV1 — Miền núi, hải đảo (+0.75đ)",
                f"KV2-NT — Nông thôn (+0.50đ)",
                f"KV2 — Thị xã, TP thuộc tỉnh (+0.25đ)",
                f"KV3 — TP trực thuộc TW (+0đ)",
            ]
            kv_idx = st.selectbox(
                "Khu vực ưu tiên:",
                options=range(len(kv_options)),
                format_func=lambda i: kv_labels[i],
                index=3,  # Default: KV3
                key="sa_kv",
            )
            selected_kv = kv_options[kv_idx]

        with ut_col:
            ut_options = list(PRIORITY_UT.keys())
            ut_labels = [
                f"Không thuộc diện ưu tiên (+0đ)",
                f"UT2 — Con thương binh, liệt sĩ... (+1.0đ)",
                f"UT1 — DTTS vùng KT-XH khó khăn (+2.0đ)",
            ]
            ut_idx = st.selectbox(
                "Đối tượng ưu tiên:",
                options=range(len(ut_options)),
                format_func=lambda i: ut_labels[i],
                index=0,  # Default: Không
                key="sa_ut",
            )
            selected_ut = ut_options[ut_idx]

        raw_bonus = calculate_total_raw_bonus(selected_kv, selected_ut)
        if raw_bonus > 0:
            st.info(
                f"📌 Tổng điểm ưu tiên gốc: **+{raw_bonus}đ** "
                f"(KV: +{PRIORITY_KV[selected_kv]}đ + ĐT: +{PRIORITY_UT[selected_ut]}đ). "
                f"*Lưu ý: Điểm ưu tiên sẽ giảm dần khi tổng 3 môn ≥ 22.5 theo quy chế.*"
            )

        # --- Nút tiếp tục ---
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Tiếp tục →", key="sa_next_1", type="primary", use_container_width=True):
            # Lọc chỉ giữ môn có điểm > 0
            filled = {k: v for k, v in input_scores.items() if v > 0}
            if len(filled) < 3:
                st.error("❌ Vui lòng nhập ít nhất 3 môn để tính tổ hợp khối thi.")
            else:
                st.session_state.sa_scores = filled
                st.session_state.sa_bonus_val = raw_bonus
                st.session_state.sa_kv_selected = selected_kv
                st.session_state.sa_ut_selected = selected_ut
                st.session_state.sa_step = 2
                st.rerun()

    # ========== STEP 2: CHỌN PHƯƠNG THỨC ==========
    elif step == 2:
        st.markdown("### 🎯 Chọn phương thức xét tuyển")

        scores = normalize_scores(st.session_state.sa_scores)

        # Preview tổ hợp mạnh nhất
        bonus = st.session_state.get("sa_bonus_val", 0.0)
        top3 = get_top_k_combinations(scores, k=3, bonus=bonus)
        if top3:
            st.markdown("**Top 3 tổ hợp mạnh nhất của bạn:**")
            preview_cols = st.columns(3)
            for i, combo in enumerate(top3[:3]):
                with preview_cols[i]:
                    is_below = combo.get("below_threshold", False)
                    emoji = "⚠️" if is_below else "🏆"
                    st.metric(
                        label=f"{emoji} {combo['code']}",
                        value=f"{combo['total']} điểm",
                        delta=f"{'Dưới ngưỡng 15!' if is_below else ' + '.join(combo['subjects'])}",
                        delta_color="inverse" if is_below else "off",
                    )

        st.divider()

        methods = st.multiselect(
            "Chọn phương thức xét tuyển:",
            options=[
                "Xét điểm Học bạ THPT",
                "Xét điểm thi THPT",
            ],
            default=["Xét điểm Học bạ THPT", "Xét điểm thi THPT"],
            key="sa_methods",
        )

        # Cảnh báo quy chế 2026
        st.warning(
            "⚠️ **Lưu ý Quy chế 2026:** Từ năm 2026, không xét riêng học bạ. "
            "Dữ liệu điểm chuẩn Học bạ từ 2025 trở về trước chỉ mang tính tham khảo."
        )

        top_k = st.selectbox(
            "Số trường gợi ý (Top K):",
            options=[3, 5, 10, 15],
            index=1,
            key="sa_top_k",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        col_back2, col_next2 = st.columns(2)
        with col_back2:
            if st.button("← Quay lại", key="sa_back_2", use_container_width=True):
                st.session_state.sa_step = 1
                st.rerun()
        with col_next2:
            if st.button("🚀 Phân tích ngay!", key="sa_analyze", type="primary", use_container_width=True):
                if not methods:
                    st.error("Vui lòng chọn ít nhất 1 phương thức xét tuyển.")
                else:
                    with st.spinner("⏳ Đang quét 20,000+ dòng dữ liệu điểm chuẩn..."):
                        result = find_top_k_schools(
                            student_scores=st.session_state.sa_scores,
                            methods=methods,
                            k=top_k,
                            bonus=bonus,
                        )
                        st.session_state.sa_result = result
                        st.session_state.sa_step = 3
                        st.rerun()

    # ========== STEP 3: KẾT QUẢ ==========
    elif step == 3:
        result = st.session_state.sa_result
        if not result:
            st.error("Không có kết quả. Vui lòng quay lại.")
            return

        if "error" in result:
            st.error(result["error"])
            if st.button("← Quay lại", key="sa_back_err"):
                st.session_state.sa_step = 1
                st.rerun()
            return

        # --- Warnings ---
        for w in result.get("warnings", []):
            st.warning(w)

        # --- Phân tích điểm mạnh ---
        strength = result.get("strength", {})
        scores = result.get("scores", {})

        st.markdown("### 📊 Phân tích Năng lực")
        m_cols = st.columns(4)
        with m_cols[0]:
            st.metric("Điểm TB", f"{strength.get('avg', 0)}")
        with m_cols[1]:
            st.metric("Xu hướng", strength.get("category", "—"))
        with m_cols[2]:
            strongest = strength.get("strongest", [])
            st.metric("Môn mạnh nhất", ", ".join(strongest[:2]) if strongest else "—")
        with m_cols[3]:
            st.metric("Số môn nhập", str(strength.get("total_subjects", 0)))

        # --- Top tổ hợp ---
        st.markdown("### 🏆 Top Tổ hợp Khối thi Mạnh nhất")
        top_combos = result.get("top_combinations", [])
        if top_combos:
            combo_cols = st.columns(min(len(top_combos), 5))
            for i, combo in enumerate(top_combos[:5]):
                with combo_cols[i]:
                    is_diem_liet = combo.get("has_diem_liet", False)
                    is_below = combo.get("below_threshold", False)
                    
                    if is_diem_liet:
                        border_color = "#8b0000" # Dark red for paralyzing score
                        warning_html = "<div style='color:#8b0000;font-size:0.75em;font-weight:bold;'>🚨 BỊ ĐIỂM LIỆT</div>"
                    elif is_below:
                        border_color = "#ff4b4b" # Standard red for below 15
                        warning_html = "<div style='color:#ff4b4b;font-size:0.75em;'>⚠️ Dưới ngưỡng 15</div>"
                    else:
                        border_color = "#00c853" # Green for good
                        warning_html = ""
                        
                    st.markdown(f"""
                    <div style="border: 2px solid {border_color}; border-radius: 12px; 
                                padding: 16px; text-align: center; margin-bottom: 8px;">
                        <div style="font-size: 1.4em; font-weight: 700;">{combo['code']}</div>
                        <div style="font-size: 1.8em; font-weight: 800; color: {border_color};">
                            {combo['total']}
                        </div>
                        <div style="font-size: 0.8em; opacity: 0.7;">
                            {' + '.join(combo['subjects'])}
                        </div>
                        {warning_html}
                    </div>
                    """, unsafe_allow_html=True)

        # --- Bảng Top K trường ---
        st.markdown(f"### 🎓 Top {len(result.get('matched_schools', []))} Trường Phù hợp")
        df = result.get("matched_schools")
        if df is not None and not df.empty:
            # Format display for Thang_40
            display_df = df.copy()
            if "Thang_40" in display_df.columns:
                display_df["Điểm chuẩn"] = display_df.apply(
                    lambda r: f"{r['Điểm chuẩn']:.2f} (x2)" if r.get("Thang_40") else f"{r['Điểm chuẩn']:.2f}", 
                    axis=1
                )
                display_df = display_df.drop(columns=["Thang_40"])
                
            if "Điểm min" in display_df.columns:
                display_df["Điểm của bạn"] = display_df.apply(
                    lambda r: f"{r['Điểm min']:.2f} - {r['Điểm của bạn']:.2f} (?)" if r.get("Điểm min") != r.get("Điểm của bạn") else f"{r['Điểm của bạn']:.2f}",
                    axis=1
                )
                display_df = display_df.drop(columns=["Điểm min"])
                
            # Ẩn cột Delta khỏi giao diện người dùng theo yêu cầu
            if "Delta" in display_df.columns:
                display_df = display_df.drop(columns=["Delta"])
                
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
            )
            st.caption(f"📈 Tổng cộng tìm thấy **{result.get('total_found', 0)}** trường/ngành phù hợp.")
            st.info("💡 **Lưu ý Thang 40:** Các trường có điểm chuẩn > 30 (dấu `x2`) nhân hệ số 2 môn chính. Do quy định môn nhân đôi tùy thuộc vào đề án từng trường, hệ thống hiển thị **Khoảng điểm (Thấp nhất - Cao nhất)** thay vì phỏng đoán. Bạn hãy tự đối chiếu môn nhân đôi của trường để biết chính xác điểm của mình nằm ở đâu trong khoảng này.")
        else:
            st.info("Không tìm thấy trường phù hợp. Thử mở rộng phương thức xét tuyển hoặc kiểm tra lại điểm.")

        # --- Phân tích AI ---
        st.markdown("### 🤖 Phân tích Chuyên gia AI")
        if df is not None and not df.empty:
            with st.spinner("⏳ AI đang phân tích..."):
                try:
                    stream = generate_analysis_stream(result)
                    if stream:
                        response_text = st.write_stream(stream)
                    else:
                        st.info("AI không thể phân tích lúc này. Vui lòng tham khảo bảng dữ liệu ở trên.")
                except Exception as e:
                    st.warning(f"⚠️ AI tạm thời không khả dụng: {e}")

        # --- Action buttons ---
        st.markdown("<br>", unsafe_allow_html=True)
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            if st.button("🔄 Phân tích lại", key="sa_retry", use_container_width=True):
                st.session_state.sa_step = 1
                st.session_state.sa_result = None
                st.rerun()
        with col_a2:
            if st.button("💬 Hỏi thêm AI", key="sa_to_chat", use_container_width=True, type="primary"):
                # Inject context vào chat
                if df is not None and not df.empty:
                    context_msg = f"[Kết quả phân tích học bạ]\nĐiểm: {scores}\nTop trường: {df[['Trường','Tên ngành','Điểm chuẩn','Delta','Tier']].to_string(index=False)}"
                    if "messages" not in st.session_state:
                        st.session_state.messages = []
                    st.session_state.messages.append({"role": "assistant", "content": context_msg})
                st.session_state.page = "chat"
                st.rerun()
        with col_a3:
            if st.button("🏠 Trang chủ", key="sa_home", use_container_width=True):
                st.session_state.page = "home"
                st.session_state.sa_step = 1
                st.rerun()



# === CHAT PAGE ===
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


