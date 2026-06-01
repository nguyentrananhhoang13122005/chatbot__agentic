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

def _safe_js_string(value: str) -> str:
    return json.dumps(value).replace("</", "<\\/")


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
                if st.button("👤 Hồ sơ của tôi", key="profile_btn", use_container_width=True):
                    st.session_state.page = "profile"
                    st.rerun()
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
    _, c_score, _ = st.columns([1, 1, 1])
    with c_score:
        if st.button("📊 Phân tích Học bạ", use_container_width=True, type="primary"):
            st.session_state.page = "score_analysis"
            st.rerun()


# === SCORE ANALYSIS PAGE ===
_SCORE_INPUT_PLACEHOLDER = "Nhập điểm"
_EXTRA_APTITUDE_DETAIL_INPUTS = [
    "Vẽ HHMT",
    "Vẽ TTM",
    "Năng khiếu SKĐA 1",
    "Năng khiếu SKĐA 2",
    "Năng khiếu TDTT 1",
    "Năng khiếu TDTT 2",
]
_EXAM_MODE_LABEL = "📝 Xét điểm thi THPT"
_TRANSCRIPT_MODE_LABEL = "📋 Xét điểm Học bạ THPT"


def _score_widget_key(subject: str) -> str:
    return subject.replace(" ", "_").replace("/", "_")


def _clear_score_input_widgets() -> None:
    for key in list(st.session_state.keys()):
        if str(key).startswith(("sa_score_choice_", "sa_score_text_", "sa_score_not_taken_")):
            st.session_state.pop(key, None)


def _missing_input_targets(missing_inputs: list[str]) -> dict[str, bool]:
    text = " ".join(str(item).lower() for item in missing_inputs)
    return {
        "language": any(item in text for item in ["tiếng nhật", "tiếng trung", "tiếng pháp", "tiếng đức", "tiếng nga"]),
        "aptitude": any(item in text for item in ["vẽ", "năng khiếu"]),
        "certificate": any(item in text for item in ["ielts", "toefl", "toeic", "chứng chỉ"]),
        "school_record": any(item in text for item in ["đtb", "lớp 12", "học lực"]),
    }


def _scroll_to_score_input_anchor() -> None:
    components.html(
        """
        <script>
        setTimeout(function() {
            try {
                const anchor = window.parent.document.getElementById("sa-score-input-anchor");
                if (anchor) {
                    anchor.scrollIntoView({behavior: "smooth", block: "start"});
                }
            } catch (error) {}
        }, 120);
        </script>
        """,
        height=0,
        scrolling=False,
    )


def _default_score_text(subject: str, existing: dict, not_taken_subjects: set[str]) -> str:
    if subject in not_taken_subjects:
        return ""
    if subject not in existing:
        return ""
    try:
        score = float(existing[subject])
    except (TypeError, ValueError):
        return ""
    return _format_decimal_default(max(0.0, min(10.0, score)))


def _parse_decimal_score(value: str, max_value: float) -> float | None:
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        score = float(text)
    except ValueError:
        return None
    if 0.0 <= score <= max_value:
        return round(score, 2)
    return None


def _format_decimal_default(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _render_subject_score_input(subject: str, existing: dict, not_taken_subjects: set[str]) -> tuple[float | None, bool, bool]:
    key = _score_widget_key(subject)
    score_col, not_taken_col = st.columns([3.4, 1], vertical_alignment="bottom")
    with not_taken_col:
        not_taken = st.checkbox(
            "Không thi",
            value=subject in not_taken_subjects,
            key=f"sa_score_not_taken_{key}",
        )
    with score_col:
        text_value = st.text_input(
            subject,
            value=_default_score_text(subject, existing, not_taken_subjects),
            placeholder=_SCORE_INPUT_PLACEHOLDER,
            disabled=not_taken,
            key=f"sa_score_text_{key}",
        )

    if not_taken:
        return None, True, True
    if not str(text_value or "").strip():
        return None, False, True
    score = _parse_decimal_score(text_value, 10.0)
    if score is None:
        st.error(f"Điểm {subject} phải là số trong khoảng 0-10.")
        return None, False, False
    return score, False, True


def _render_ielts_input() -> None:
    ielts_options = [value / 2 for value in range(0, 19)]
    current = st.session_state.get("sa_ielts", 0.0)
    try:
        current_value = float(current or 0.0)
    except (TypeError, ValueError):
        current_value = 0.0
    if current_value not in ielts_options:
        current_value = 0.0
    st.selectbox(
        "IELTS",
        ielts_options,
        index=ielts_options.index(current_value),
        format_func=lambda value: "Không có" if value == 0 else f"{value:.1f}",
        key="sa_ielts",
    )


def _positive_session_float(key: str) -> float | None:
    try:
        value = float(st.session_state.get(key, 0) or 0)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _selected_score_mode() -> str:
    label = st.session_state.get("sa_mode_radio", _EXAM_MODE_LABEL)
    return "exam" if label == _EXAM_MODE_LABEL else "transcript"


def _build_score_analysis_payload(mode: str) -> dict:
    raw_scores = dict(st.session_state.get("sa_scores", {}))
    if mode != "exam":
        return raw_scores

    from utils.score_calculator import EXTRA_APTITUDE

    aptitude_names = set(EXTRA_APTITUDE) | set(_EXTRA_APTITUDE_DETAIL_INPUTS)
    aptitude_scores = {
        subject: score
        for subject, score in raw_scores.items()
        if subject in aptitude_names or subject.startswith("Vẽ") or subject.startswith("Năng khiếu")
    }
    exam_scores = {subject: score for subject, score in raw_scores.items() if subject not in aptitude_scores}
    academic_rank = st.session_state.get("sa_rank12")
    if academic_rank == "Không chọn":
        academic_rank = None

    return {
        "exam_scores": exam_scores,
        "aptitude_scores": aptitude_scores,
        "not_taken_subjects": list(st.session_state.get("sa_not_taken_subjects", set())),
        "ielts": _positive_session_float("sa_ielts"),
        "toefl": _positive_session_float("sa_toefl"),
        "toeic": _positive_session_float("sa_toeic"),
        "gpa_12": _positive_session_float("sa_gpa12"),
        "academic_rank_12": academic_rank,
    }


def _current_score_analysis_result() -> dict | None:
    mode = st.session_state.get("sa_mode", "exam")
    if mode == "exam":
        return st.session_state.get("sa_exam_result")
    return st.session_state.get("sa_transcript_result")


def _to_float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _format_score_number(value) -> str:
    number = _to_float(value)
    if number is None:
        return str(value or "")
    return f"{number:.2f}".rstrip("0").rstrip(".")


def _format_score_range(row) -> str:
    min_score = _to_float(row.get("Điểm min"))
    max_score = _to_float(row.get("Điểm của bạn"))
    if min_score is not None and max_score is not None and abs(min_score - max_score) > 0.001:
        return f"{_format_score_number(min_score)} - {_format_score_number(max_score)}"
    return _format_score_number(row.get("Điểm của bạn"))


def _format_cutoff(row) -> str:
    cutoff = _format_score_number(row.get("Điểm chuẩn"))
    if not cutoff:
        return ""
    pieces = [cutoff]
    if "Thang_40" in row:
        scale_flag = str(row.get("Thang_40", "")).strip().lower()
        is_thang_40 = bool(row.get("Thang_40")) and scale_flag not in {"false", "0", "nan", "none"}
        pieces.append("thang 40" if is_thang_40 else "thang 30")
    year = row.get("Năm")
    year_number = _to_float(year)
    if year_number is not None:
        pieces.append(str(int(year_number)))
    elif year is not None and str(year).strip().lower() not in {"", "nan", "none"}:
        pieces.append(str(year))
    return " / ".join(pieces)


def _format_annotation(row) -> str:
    annotation = str(row.get("Chú thích") or "").strip()
    min_score = _to_float(row.get("Điểm min"))
    max_score = _to_float(row.get("Điểm của bạn"))
    scale_flag = str(row.get("Thang_40", "")).strip().lower()
    is_thang_40 = bool(row.get("Thang_40")) and scale_flag not in {"false", "0", "nan", "none"}
    if is_thang_40 and min_score is not None and max_score is not None and abs(min_score - max_score) > 0.001:
        tag = "🔶 Thang 40 chưa rõ môn nhân - xếp hạng bảo thủ"
        if tag not in annotation:
            annotation = f"{annotation} · {tag}" if annotation else tag
    return annotation


def _format_admission_gap_for_chat(row) -> str:
    gap = _to_float(row.get("Delta"))
    if gap is None:
        return "chưa đủ dữ liệu để so sánh điểm"
    if abs(gap) < 0.05:
        return "xấp xỉ điểm chuẩn"
    if gap > 0:
        return f"cao hơn điểm chuẩn {_format_score_number(abs(gap))} điểm"
    return f"thấp hơn điểm chuẩn {_format_score_number(abs(gap))} điểm"


def _format_school_context_for_chat(df) -> str:
    if df is None or df.empty:
        return "Không có dữ liệu trường/ngành phù hợp."

    lines = []
    for index, (_, row) in enumerate(df.iterrows(), start=1):
        pieces = [
            f"{index}. {row.get('Trường', 'Không rõ')} - {row.get('Tên ngành', 'Không rõ')}",
            f"Điểm chuẩn: {_format_cutoff(row)}",
            f"Điểm của học sinh: {_format_score_range(row)}",
            f"Chênh lệch điểm: {_format_admission_gap_for_chat(row)}",
            f"Nhóm: {row.get('Tier', 'Không rõ')}",
        ]
        year = row.get("Năm")
        if year is not None and str(year).strip().lower() not in {"", "nan", "none"}:
            pieces.append(f"Năm: {year}")
        lines.append(" | ".join(pieces))
    return "\n".join(lines)


def _prepare_school_display(df):
    import pandas as pd
    display_df = df.copy()
    
    # 1. Gộp Tên ngành và Mã ngành
    if "Mã ngành" in display_df.columns and "Tên ngành" in display_df.columns:
        display_df["Ngành (Mã)"] = display_df.apply(
            lambda r: f"{r['Tên ngành']} ({r['Mã ngành']})" if pd.notna(r['Mã ngành']) and str(r['Mã ngành']).strip() else r['Tên ngành'], 
            axis=1
        )
    else:
        display_df["Ngành (Mã)"] = display_df.get("Tên ngành", display_df.get("Mã ngành", ""))

    # 2. Gộp Điểm chuẩn và Năm/Thang điểm
    def format_new_cutoff(row):
        cutoff = _format_score_number(row.get("Điểm chuẩn"))
        if not cutoff: return ""
        details = []
        if "Thang_40" in row:
             scale_flag = str(row.get("Thang_40", "")).strip().lower()
             is_thang_40 = bool(row.get("Thang_40")) and scale_flag not in {"false", "0", "nan", "none"}
             if is_thang_40: details.append("Thang 40")
        year = row.get("Năm")
        if year is not None and str(year).strip().lower() not in {"", "nan", "none"}:
            try:
                details.append(str(int(float(year))))
            except:
                details.append(str(year))
        
        if details:
            return f"{cutoff} ({', '.join(details)})"
        return cutoff

    if "Điểm chuẩn" in display_df.columns:
        display_df["Điểm chuẩn năm trước"] = display_df.apply(format_new_cutoff, axis=1)

    # 3. Gộp Điểm của bạn và Tổ hợp môn
    def format_new_user_score(row):
        score_str = _format_score_range(row)
        combo = row.get("Tổ hợp khớp", "")
        if combo and str(combo).strip():
            return f"{score_str} ({combo})"
        return score_str

    if "Điểm của bạn" in display_df.columns:
        display_df["Điểm của bạn (Tổ hợp)"] = display_df.apply(format_new_user_score, axis=1)

    # 4. Đổi tên cột Tier
    if "Tier" in display_df.columns:
        display_df["Đánh giá"] = display_df["Tier"]

    # 5. Chọn lọc và sắp xếp các cột tinh gọn nhất
    ordered = [
        "Trường",
        "Ngành (Mã)",
        "Phương thức xét tuyển",
        "Điểm chuẩn năm trước",
        "Điểm của bạn (Tổ hợp)",
        "Đánh giá"
    ]
    
    final_cols = [col for col in ordered if col in display_df.columns]
    return display_df[final_cols]


@st.dialog("Nhập thêm thông tin để xét thêm ngành", width="small")
def _score_missing_inputs_dialog(missing_inputs: list[str]):
    missing_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in missing_inputs[:8])
    if len(missing_inputs) > 8:
        missing_html += f"<li>Còn {len(missing_inputs) - 8} mục khác.</li>"
    st.markdown(
        f"""
        <div class="sa-missing-panel">
            <p>Một số ngành/tổ hợp đang bị tạm loại vì thiếu dữ liệu:</p>
            <ul>{missing_html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_more, col_keep = st.columns(2)
    with col_more:
        if st.button("Nhập thêm ↑", key="sa_missing_more", type="primary", use_container_width=True):
            st.session_state.sa_step = 1
            st.session_state.sa_focus_missing_inputs = missing_inputs[:8]
            st.session_state.sa_scroll_to_score_inputs = True
            st.rerun(scope="app")
    with col_keep:
        if st.button("Giữ kết quả hiện tại", key="sa_missing_keep", use_container_width=True):
            st.session_state.sa_exam_missing_dismissed = True
            st.rerun(scope="app")


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
    if "sa_not_taken_subjects" not in st.session_state:
        st.session_state.sa_not_taken_subjects = set()
    if "sa_mode" not in st.session_state:
        st.session_state.sa_mode = "exam"
    if "sa_exam_result" not in st.session_state:
        st.session_state.sa_exam_result = None
    if "sa_transcript_result" not in st.session_state:
        st.session_state.sa_transcript_result = None
    if "sa_exam_missing_inputs" not in st.session_state:
        st.session_state.sa_exam_missing_inputs = []
    if "sa_exam_missing_dismissed" not in st.session_state:
        st.session_state.sa_exam_missing_dismissed = False
    if "sa_focus_missing_inputs" not in st.session_state:
        st.session_state.sa_focus_missing_inputs = []
    if "sa_scroll_to_score_inputs" not in st.session_state:
        st.session_state.sa_scroll_to_score_inputs = False
    if "sa_result" not in st.session_state:
        st.session_state.sa_result = None

    # --- Header ---
    col_back, col_title = st.columns([0.15, 0.85])
    with col_back:
        if st.button("← Trang chủ", key="sa_back_home"):
            st.session_state.page = "home"
            st.session_state.sa_step = 1
            st.session_state.sa_max_step = 1
            st.rerun()
    with col_title:
        st.markdown("## 📊 Phân tích điểm xét tuyển & Gợi ý Trường")

    # --- Step Wizard Bar ---
    step = st.session_state.sa_step
    if "sa_max_step" not in st.session_state:
        st.session_state.sa_max_step = step
    st.session_state.sa_max_step = max(st.session_state.sa_max_step, step)

    steps = ["① Nhập điểm", "② Phương thức", "③ Kết quả AI"]
    step_cols = st.columns(3)
    for i, (sc, label) in enumerate(zip(step_cols, steps)):
        with sc:
            is_unlocked = (i + 1 <= st.session_state.sa_max_step) or (i + 1 == 3 and st.session_state.get("sa_result") is not None)
            
            if i + 1 < step:
                if st.button(f"✅ {label}", key=f"step_btn_{i}", use_container_width=True, help="Nhấn để quay lại"):
                    st.session_state.sa_step = i + 1
                    st.rerun()
            elif i + 1 == step:
                st.button(f"👉 {label}", key=f"step_btn_{i}", type="primary", use_container_width=True)
            else:
                if is_unlocked:
                    if st.button(f"⬜ {label}", key=f"step_btn_{i}", use_container_width=True, help="Nhấn để đi tới"):
                        st.session_state.sa_step = i + 1
                        st.rerun()
                else:
                    st.button(f"⬜ {label}", key=f"step_btn_{i}", disabled=True, use_container_width=True)

    st.divider()

    # ========== STEP 1: NHẬP ĐIỂM ==========
    if step == 1:
        st.markdown("### 📝 Nhập điểm từng môn")

        input_mode = st.radio(
            "Chọn phương thức nhập điểm:",
            ["Nhập điểm thi / Trung bình môn", "Nhập chi tiết Học bạ (6 học kỳ)"],
            horizontal=True,
            key="sa_input_mode_radio"
        )



        st.markdown("---")
        st.markdown('<span id="sa-score-input-anchor"></span>', unsafe_allow_html=True)
        st.markdown("**Nhập điểm thủ công** *(thang 10)*")
        focus_missing_inputs = st.session_state.get("sa_focus_missing_inputs", [])
        missing_targets = _missing_input_targets(focus_missing_inputs)
        if focus_missing_inputs:
            st.info("Bạn đang bổ sung dữ liệu còn thiếu: " + ", ".join(focus_missing_inputs[:6]))
        if st.session_state.get("sa_scroll_to_score_inputs"):
            st.session_state.sa_scroll_to_score_inputs = False
            _scroll_to_score_input_anchor()

        # --- Score Input Form ---
        existing = st.session_state.sa_scores
        existing_not_taken = set(st.session_state.get("sa_not_taken_subjects", set()))
        input_scores = {}
        not_taken_subjects = set()
        invalid_score_inputs = []



        if input_mode == "Nhập điểm thi / Trung bình môn":
            st.markdown("**Nhập điểm thủ công** *(thang 10)*")
            col_left, col_right = st.columns(2)
            for i, subj in enumerate(MAIN_SUBJECTS):
                target_col = col_left if i < 5 else col_right
                with target_col:
                    score, not_taken, valid = _render_subject_score_input(subj, existing, existing_not_taken)
                    if not valid:
                        invalid_score_inputs.append(subj)
                    elif not_taken:
                        not_taken_subjects.add(subj)
                    elif score is not None:
                        input_scores[subj] = score

            # --- Ngoại ngữ phụ (tùy chọn) ---
            from utils.score_calculator import EXTRA_LANGUAGES
            with st.expander(
                "🌐 Ngoại ngữ khác (Nhật, Trung, Pháp, Đức, Nga) — *bấm để mở*",
                expanded=missing_targets["language"],
            ):
                st.caption("Nếu bạn học ngoại ngữ 2 hoặc thi ngoại ngữ khác ngoài Tiếng Anh, nhập điểm để mở thêm tổ hợp khối D.")
                lang_col1, lang_col2 = st.columns(2)
                for j, lang in enumerate(EXTRA_LANGUAGES):
                    target_lang_col = lang_col1 if j < 3 else lang_col2
                    with target_lang_col:
                        score, not_taken, valid = _render_subject_score_input(lang, existing, existing_not_taken)
                        if not valid:
                            invalid_score_inputs.append(lang)
                        elif not_taken:
                            not_taken_subjects.add(lang)
                        elif score is not None:
                            input_scores[lang] = score

            # --- Năng khiếu (tùy chọn) ---
            from utils.score_calculator import EXTRA_APTITUDE
            with st.expander(
                "🎨 Môn Năng khiếu (Vẽ, Âm nhạc, Thể thao...) — *bấm để mở*",
                expanded=missing_targets["aptitude"],
            ):
                st.caption("Nhập điểm các môn năng khiếu để xét tuyển vào các khối V, H, M, N, T, S, R.")
                apt_col1, apt_col2 = st.columns(2)
                aptitude_inputs = list(EXTRA_APTITUDE) + _EXTRA_APTITUDE_DETAIL_INPUTS
                for j, apt in enumerate(aptitude_inputs):
                    target_apt_col = apt_col1 if j % 2 == 0 else apt_col2
                    with target_apt_col:
                        score, not_taken, valid = _render_subject_score_input(apt, existing, existing_not_taken)
                        if not valid:
                            invalid_score_inputs.append(apt)
                        elif not_taken:
                            not_taken_subjects.add(apt)
                        elif score is not None:
                            input_scores[apt] = score
        else:
            import pandas as pd
            import numpy as np

            st.markdown("**Nhập điểm Học bạ chi tiết** *(từ 0 đến 10)*")
            if "sa_transcript_df" not in st.session_state:
                cols = ["HK1 Lớp 10", "HK2 Lớp 10", "HK1 Lớp 11", "HK2 Lớp 11", "HK1 Lớp 12", "HK2 Lớp 12"]
                subjects_to_show = MAIN_SUBJECTS + ["Tin học", "Công nghệ"]
                df_init = pd.DataFrame(0.0, index=subjects_to_show, columns=cols)
                df_init = df_init.reset_index(names=["Môn"])
                st.session_state.sa_transcript_df = df_init
            elif "Môn" not in st.session_state.sa_transcript_df.columns:
                # Migrate existing session state to new schema
                st.session_state.sa_transcript_df = st.session_state.sa_transcript_df.reset_index(names=["Môn"])
            
            formula = st.selectbox(
                "Cách tính điểm trung bình xét tuyển:",
                [
                    "Trung bình 5 học kỳ (Bỏ HK2 Lớp 12)", 
                    "Trung bình 6 học kỳ (Cả 3 năm)",
                    "Trung bình cả năm Lớp 12 (HK1 & HK2 L12)"
                ],
                key="sa_transcript_formula"
            )

            import streamlit.components.v1 as components
            import os

            df_current = st.session_state.sa_transcript_df
            initial_data = {}
            for _, row in df_current.iterrows():
                subj = row["Môn"]
                initial_data[subj] = {col: float(row[col]) for col in df_current.columns if col != "Môn"}

            _component_func = components.declare_component(
                "transcript_editor",
                path=os.path.join(os.path.dirname(__file__), "transcript_editor")
            )

            component_value = _component_func(
                subjects=df_current["Môn"].tolist(), 
                initial_data=initial_data, 
                key="custom_transcript"
            )

            if component_value is not None:
                for subj, scores in component_value.items():
                    idx = df_current.index[df_current["Môn"] == subj].tolist()
                    if idx:
                        for sem, score in scores.items():
                            if sem in df_current.columns:
                                df_current.loc[idx[0], sem] = float(score)
                st.session_state.sa_transcript_df = df_current
                edited_df = df_current
            else:
                edited_df = df_current
            
            st.markdown("---")
            st.markdown("**Kết quả tính Điểm Trung Bình:**")
            
            if formula == "Trung bình 5 học kỳ (Bỏ HK2 Lớp 12)":
                cols_to_calc = ["HK1 Lớp 10", "HK2 Lớp 10", "HK1 Lớp 11", "HK2 Lớp 11", "HK1 Lớp 12"]
            elif formula == "Trung bình 6 học kỳ (Cả 3 năm)":
                cols_to_calc = ["HK1 Lớp 10", "HK2 Lớp 10", "HK1 Lớp 11", "HK2 Lớp 11", "HK1 Lớp 12", "HK2 Lớp 12"]
            else:
                cols_to_calc = ["HK1 Lớp 12", "HK2 Lớp 12"]

            df_calc = edited_df.set_index("Môn")[cols_to_calc].replace(0.0, np.nan)
            avg_series = df_calc.mean(axis=1).round(2)
            calculated_scores = avg_series.dropna().to_dict()
            
            if calculated_scores:
                items = list(calculated_scores.items())
                for i in range(0, len(items), 5):
                    chunk = items[i:i+5]
                    cols_preview = st.columns(5)
                    for j, (subj, score) in enumerate(chunk):
                        with cols_preview[j]:
                            st.metric(subj, f"{score:.2f}")
            else:
                st.info("Nhập điểm vào bảng để xem kết quả tính toán.")
            
            input_scores = calculated_scores
            invalid_score_inputs = []
            not_taken_subjects = set()

        with st.expander("📜 Chứng chỉ ngoại ngữ (nếu có)", expanded=missing_targets["certificate"]):
            st.caption("Nhập nếu ngành yêu cầu chứng chỉ IELTS/TOEFL/TOEIC.")
            cert_col1, cert_col2, cert_col3 = st.columns(3)
            with cert_col1:
                _render_ielts_input()
            with cert_col2:
                st.number_input("TOEFL iBT", 0, 120, 0, key="sa_toefl")
            with cert_col3:
                st.number_input("TOEIC", 0, 990, 0, key="sa_toeic")

        with st.expander("📋 Thông tin THPT bổ sung (nếu ngành yêu cầu)", expanded=missing_targets["school_record"]):
            st.caption("Một số ngành yêu cầu ĐTB lớp 12 hoặc học lực.")
            gpa_col1, gpa_col2 = st.columns(2)
            with gpa_col1:
                st.number_input("ĐTB lớp 12 tổng", 0.0, 10.0, 0.0, 0.1, key="sa_gpa12")
            with gpa_col2:
                st.selectbox("Học lực lớp 12", ["Không chọn", "Giỏi", "Khá", "Trung bình"], key="sa_rank12")

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
            filled = dict(input_scores)
            if invalid_score_inputs:
                st.error("❌ Vui lòng kiểm tra lại điểm nhập cho: " + ", ".join(invalid_score_inputs[:6]))
            elif len(filled) < 3:
                st.error("❌ Vui lòng nhập ít nhất 3 môn để tính tổ hợp khối thi.")
            else:
                st.session_state.sa_scores = filled
                st.session_state.sa_not_taken_subjects = not_taken_subjects
                st.session_state.sa_bonus_val = raw_bonus
                st.session_state.sa_kv_selected = selected_kv
                st.session_state.sa_ut_selected = selected_ut
                st.session_state.sa_focus_missing_inputs = []
                st.session_state.sa_mode = "transcript" if input_mode == "Nhập chi tiết Học bạ (6 học kỳ)" else "exam"
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

        mode_index = 0 if st.session_state.get("sa_mode", "exam") == "exam" else 1
        mode_label = st.radio(
            "Chọn phương thức xét tuyển:",
            [_EXAM_MODE_LABEL, _TRANSCRIPT_MODE_LABEL],
            index=mode_index,
            key="sa_mode_radio",
            horizontal=True,
        )
        st.session_state.sa_mode = _selected_score_mode()

        if mode_label == _TRANSCRIPT_MODE_LABEL:
            st.warning(
                "⚠️ **Lưu ý Quy chế 2026:** Từ năm 2026, không xét riêng học bạ. "
                "Dữ liệu điểm chuẩn Học bạ từ 2025 trở về trước chỉ mang tính tham khảo."
            )

        top_k = st.selectbox(
            "Số trường gợi ý (Top K):",
            options=[3, 5, 10, 15, 20],
            index=1,
            key="sa_top_k",
        )

        with st.expander("🛠️ Bộ lọc nâng cao (Tùy chọn)", expanded=False):
            st.markdown("Thu hẹp kết quả tìm kiếm theo sở thích của bạn.")
            prov_options = ["Tất cả", "Hà Nội", "TP.HCM", "Đà Nẵng", "Cần Thơ", "Khác"]
            filter_province = st.selectbox("📍 Chọn Tỉnh/Thành phố:", prov_options, key="sa_filter_province")
            filter_major = st.text_input("🎓 Ngành mong muốn (VD: Máy tính, Kinh tế...):", key="sa_filter_major", placeholder="Gõ từ khóa ngành...")

        st.markdown("<br>", unsafe_allow_html=True)
        col_back2, col_next2 = st.columns(2)
        with col_back2:
            if st.button("← Quay lại", key="sa_back_2", use_container_width=True):
                st.session_state.sa_step = 1
                st.rerun()
        with col_next2:
            if st.button("🚀 Phân tích ngay!", key="sa_analyze", type="primary", use_container_width=True):
                mode = _selected_score_mode()
                methods = ["Xét điểm thi THPT"] if mode == "exam" else ["Xét điểm Học bạ THPT"]
                payload = _build_score_analysis_payload(mode)
                
                prov_val = None if filter_province == "Tất cả" else filter_province
                major_val = filter_major.strip() if filter_major.strip() else None
                
                with st.spinner("⏳ Đang quét dữ liệu điểm chuẩn..."):
                    result = find_top_k_schools(
                        student_scores=payload,
                        methods=methods,
                        k=top_k,
                        bonus=bonus,
                        province=prov_val,
                        major=major_val,
                    )
                    result.setdefault("user_filters", {})
                    result["user_filters"].update({
                        "province": prov_val,
                        "major": major_val,
                        "top_k": top_k,
                        "mode": mode,
                    })
                    st.session_state.sa_mode = mode
                    if mode == "exam":
                        st.session_state.sa_exam_result = result
                        st.session_state.sa_exam_missing_inputs = result.get("missing_inputs", [])
                        st.session_state.sa_exam_missing_dismissed = False
                    else:
                        st.session_state.sa_transcript_result = result
                    st.session_state.sa_result = result
                    st.session_state.sa_step = 3
                    st.session_state.pop("sa_ai_analysis_text", None)
                    st.rerun()

    # ========== STEP 3: KẾT QUẢ ==========
    elif step == 3:
        result = _current_score_analysis_result() or st.session_state.sa_result
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

        missing_inputs = result.get("missing_inputs", [])
        if (
            st.session_state.get("sa_mode") == "exam"
            and missing_inputs
            and not st.session_state.get("sa_exam_missing_dismissed", False)
        ):
            _score_missing_inputs_dialog(missing_inputs)

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
                        status_class = "danger"
                        warning_html = '<div class="sa-combo-card-alert">🚨 BỊ ĐIỂM LIỆT</div>'
                    elif is_below:
                        status_class = "warning"
                        warning_html = '<div class="sa-combo-card-alert">⚠️ Dưới ngưỡng 15</div>'
                    else:
                        status_class = "success"
                        warning_html = ""
                    combo_code = html.escape(str(combo["code"]))
                    combo_total = html.escape(str(combo["total"]))
                    combo_subjects = html.escape(" + ".join(combo["subjects"]))

                    st.markdown(f"""
                    <div class="sa-combo-card sa-combo-card-{status_class}">
                        <div class="sa-combo-card-code">{combo_code}</div>
                        <div class="sa-combo-card-score">{combo_total}</div>
                        <div class="sa-combo-card-subjects">{combo_subjects}</div>
                        {warning_html}
                    </div>
                    """, unsafe_allow_html=True)

        # --- Bảng Top K trường ---
        st.markdown(f"### 🎓 Top {len(result.get('matched_schools', []))} Trường Phù hợp")
        df = result.get("matched_schools")
        if df is not None and not df.empty:
            display_df = _prepare_school_display(df)
            # --- CUSTOM RESPONSIVE TABLE ---
            html_rows = []
            for _, row in display_df.iterrows():
                truong = html.escape(str(row.get("Trường", "")))
                nganh = html.escape(str(row.get("Ngành (Mã)", "")))
                ptxt = html.escape(str(row.get("Phương thức xét tuyển", "")))
                diem_chuan = html.escape(str(row.get("Điểm chuẩn năm trước", "")))
                diem_ban = html.escape(str(row.get("Điểm của bạn (Tổ hợp)", "")))
                tier = str(row.get("Đánh giá", ""))
                
                # Determine tier color
                tier_upper = tier.upper()
                if "AN TOÀN" in tier_upper:
                    badge_class = "ts247-badge-safe"
                elif "VỪA SỨC" in tier_upper:
                    badge_class = "ts247-badge-warning"
                else:
                    badge_class = "ts247-badge-danger"
                
                tier_html = f'<span class="ts247-badge {badge_class}">{html.escape(tier)}</span>'
                
                html_rows.append(f"""<div class="ts247-tr">
    <div class="ts247-td">
        <span class="ts247-td-content">{truong}</span>
    </div>
    <div class="ts247-td">
        <span class="ts247-td-label">Ngành:</span>
        <span class="ts247-td-content">{nganh}</span>
    </div>
    <div class="ts247-td">
        <span class="ts247-td-label">PTXT:</span>
        <span class="ts247-td-content">{ptxt}</span>
    </div>
    <div class="ts247-td">
        <span class="ts247-td-label">Điểm chuẩn:</span>
        <span class="ts247-td-content">{diem_chuan}</span>
    </div>
    <div class="ts247-td">
        <span class="ts247-td-label">Điểm của bạn:</span>
        <span class="ts247-td-content">{diem_ban}</span>
    </div>
    <div class="ts247-td">
        <span class="ts247-td-label">Đánh giá:</span>
        <span class="ts247-td-content">{tier_html}</span>
    </div>
</div>""")
            
            table_html = f"""<div class="ts247-container">
    <div class="ts247-table">
        <div class="ts247-thead">
            <div class="ts247-tr">
                <div class="ts247-th">Trường</div>
                <div class="ts247-th">Ngành (Mã)</div>
                <div class="ts247-th">Phương thức xét tuyển</div>
                <div class="ts247-th">Điểm chuẩn năm trước</div>
                <div class="ts247-th">Điểm của bạn (Tổ hợp)</div>
                <div class="ts247-th">Đánh giá</div>
            </div>
        </div>
        <div class="ts247-tbody">
            {"".join(html_rows)}
        </div>
    </div>
</div>"""
            st.markdown(table_html, unsafe_allow_html=True)
            st.caption(f"📈 Tổng cộng tìm thấy **{result.get('total_found', 0)}** trường/ngành phù hợp.")
            st.caption("📐 = Nhân hệ số · 📊 = Thang điểm · ⚠️ = Điều kiện · 📜 = Chứng chỉ · 📋 = Học bạ")
        else:
            st.info("Không tìm thấy trường phù hợp. Thử mở rộng phương thức xét tuyển hoặc kiểm tra lại điểm.")

        # --- Phân tích AI ---
        st.markdown("### 🤖 Phân tích Chuyên gia AI")
        if df is not None and not df.empty:
            if "sa_ai_analysis_text" in st.session_state and st.session_state.sa_ai_analysis_text:
                st.markdown(st.session_state.sa_ai_analysis_text)
            else:
                if st.button("✨ Nhận Phân tích từ Chuyên gia AI", key="sa_btn_ai_analysis"):
                    with st.spinner("⏳ AI đang phân tích..."):
                        try:
                            stream = generate_analysis_stream(result)
                            if stream:
                                response_text = st.write_stream(stream)
                                st.session_state.sa_ai_analysis_text = response_text
                            else:
                                st.info("AI không thể phân tích lúc này. Vui lòng tham khảo bảng dữ liệu ở trên.")
                        except Exception as e:
                            st.warning(f"⚠️ AI tạm thời không khả dụng: {e}")

        # --- Action buttons ---
        st.markdown("<br>", unsafe_allow_html=True)
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            if st.button("🔄 Phân tích lại", key="sa_retry", use_container_width=True):
                st.session_state.sa_step = 1
                st.session_state.sa_max_step = 1
                if st.session_state.get("sa_mode") == "exam":
                    st.session_state.sa_exam_result = None
                    st.session_state.sa_exam_missing_inputs = []
                    st.session_state.sa_exam_missing_dismissed = False
                else:
                    st.session_state.sa_transcript_result = None
                st.session_state.sa_result = None
                st.session_state.pop("sa_ai_analysis_text", None)
                st.rerun()
        with col_a2:
            if st.button("🏠 Trang chủ", key="sa_home", use_container_width=True):
                st.session_state.page = "home"
                st.session_state.sa_step = 1
                st.session_state.sa_max_step = 1
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


# === PROFILE PAGE ===
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
