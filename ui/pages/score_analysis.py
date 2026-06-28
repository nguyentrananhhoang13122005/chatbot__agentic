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

def list_provinces() -> list[str]:
    import json
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "university_provinces.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return sorted(list(set(data.values())))
    except Exception as e:
        print(f"Error loading provinces: {e}")
        return []


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
_TRANSCRIPT_MODE_LABEL = "📖 Xét điểm Học bạ THPT"

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
        tag = "⚠️ Thang 40 chưa rõ môn nhân - xếp hạng bảo thủ"
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
        if st.button("Nhập thêm", icon=":material/expand_less:", key="sa_missing_more", type="primary", use_container_width=True):
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
        if st.button("Trang chủ", icon=":material/arrow_back:", key="sa_back_home"):
            st.session_state.page = "home"
            st.session_state.sa_step = 1
            st.session_state.sa_max_step = 1
            st.rerun()
    with col_title:
        st.markdown(
            '<h2 style="display: flex; align-items: center; gap: 8px; margin: 0; font-size: 1.75rem; font-weight: 700;">'
            '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-bar-chart-3" style="vertical-align: middle;"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>'
            'Phân tích điểm xét tuyển & Gợi ý Trường'
            '</h2>',
            unsafe_allow_html=True
        )

    # --- Step Wizard Bar ---
    step = st.session_state.sa_step
    if "sa_max_step" not in st.session_state:
        st.session_state.sa_max_step = step
    st.session_state.sa_max_step = max(st.session_state.sa_max_step, step)

    step_labels = ["1. Nhập điểm", "2. Phương thức", "3. Kết quả AI"]
    step_icons = [":material/edit:", ":material/tune:", ":material/auto_awesome:"]
    step_cols = st.columns(3)
    for i, (sc, label) in enumerate(zip(step_cols, step_labels)):
        with sc:
            is_unlocked = (i + 1 <= st.session_state.sa_max_step) or (i + 1 == 3 and st.session_state.get("sa_result") is not None)
            
            if i + 1 < step:
                if st.button(label, icon=":material/check_circle:", key=f"step_btn_{i}", use_container_width=True, help="Nhấn để quay lại"):
                    st.session_state.sa_step = i + 1
                    st.rerun()
            elif i + 1 == step:
                st.button(label, icon=step_icons[i], key=f"step_btn_{i}", type="primary", use_container_width=True)
            else:
                if is_unlocked:
                    if st.button(label, icon=":material/radio_button_unchecked:", key=f"step_btn_{i}", use_container_width=True, help="Nhấn để đi tới"):
                        st.session_state.sa_step = i + 1
                        st.rerun()
                else:
                    st.button(label, icon=":material/lock:", key=f"step_btn_{i}", disabled=True, use_container_width=True)

    st.divider()

    # ========== STEP 1: NHẬP ĐIỂM ==========
    if step == 1:
        st.markdown(
            '<h3 style="display: flex; align-items: center; gap: 8px; margin-top: 1.5rem; margin-bottom: 0.8rem; font-size: 1.35rem; font-weight: 600;">'
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-pencil" style="vertical-align: middle;"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>'
            'Nhập điểm từng môn'
            '</h3>',
            unsafe_allow_html=True
        )

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
                "Ngoại ngữ khác (Nhật, Trung, Pháp, Đức, Nga)",
                icon="🌐",
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
                "Môn Năng khiếu (Vẽ, Âm nhạc, Thể thao...)",
                icon="🎨",
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
                path=os.path.join(os.path.dirname(os.path.dirname(__file__)), "transcript_editor")
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

        with st.expander("Chứng chỉ ngoại ngữ (nếu có)", icon="🎫", expanded=missing_targets["certificate"]):
            st.caption("Nhập nếu ngành yêu cầu chứng chỉ IELTS/TOEFL/TOEIC.")
            cert_col1, cert_col2, cert_col3 = st.columns(3)
            with cert_col1:
                _render_ielts_input()
            with cert_col2:
                st.number_input("TOEFL iBT", 0, 120, 0, key="sa_toefl")
            with cert_col3:
                st.number_input("TOEIC", 0, 990, 0, key="sa_toeic")

        with st.expander("Thông tin THPT bổ sung (nếu ngành yêu cầu)", icon="📝", expanded=missing_targets["school_record"]):
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
                f"Tổng điểm ưu tiên gốc: **+{raw_bonus}đ** "
                f"(KV: +{PRIORITY_KV[selected_kv]}đ + ĐT: +{PRIORITY_UT[selected_ut]}đ). "
                f"*Lưu ý: Điểm ưu tiên sẽ giảm dần khi tổng 3 môn ≥ 22.5 theo quy chế.*",
                icon="📌"
            )

        # --- Nút tiếp tục ---
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Tiếp tục", icon=":material/arrow_forward:", key="sa_next_1", type="primary", use_container_width=True):
            filled = dict(input_scores)
            if invalid_score_inputs:
                st.error("Vui lòng kiểm tra lại điểm nhập cho: " + ", ".join(invalid_score_inputs[:6]))
            elif len(filled) < 3:
                st.error("Vui lòng nhập ít nhất 3 môn để tính tổ hợp khối thi.")
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
        st.markdown(
            '<h3 style="display: flex; align-items: center; gap: 8px; margin-top: 1.5rem; margin-bottom: 0.8rem; font-size: 1.35rem; font-weight: 600;">'
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-sliders-horizontal" style="vertical-align: middle;"><line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/></svg>'
            'Chọn phương thức xét tuyển'
            '</h3>',
            unsafe_allow_html=True
        )

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
                "**Lưu ý Quy chế 2026:** Từ năm 2026, không xét riêng học bạ. "
                "Học bạ chỉ là tiêu chí phụ hoặc kết hợp. Hãy cân nhắc khi chọn!"
            )

        top_k = st.selectbox(
            "Số trường gợi ý (Top K):",
            options=[3, 5, 10, 15, 20],
            index=1,
            key="sa_top_k",
        )

        with st.expander("Bộ lọc nâng cao (Tùy chọn)", icon="⚙️", expanded=False):
            st.markdown("Thu hẹp kết quả tìm kiếm theo sở thích của bạn.")
            prov_options = ["Tất cả"] + list_provinces()
            filter_province = st.selectbox("Chọn Tỉnh/Thành phố:", prov_options, key="sa_filter_province")
            filter_major = st.text_input("Ngành mong muốn (VD: Máy tính, Kinh tế...):", key="sa_filter_major", placeholder="Gõ từ khóa ngành...")

        st.markdown("<br>", unsafe_allow_html=True)
        col_back2, col_next2 = st.columns(2)
        with col_back2:
            if st.button("Quay lại", icon=":material/arrow_back:", key="sa_back_2", use_container_width=True):
                st.session_state.sa_step = 1
                st.rerun()
        with col_next2:
            if st.button("Phân tích ngay!", icon=":material/rocket_launch:", key="sa_analyze", type="primary", use_container_width=True):
                mode = _selected_score_mode()
                methods = ["Xét điểm thi THPT"] if mode == "exam" else ["Xét điểm Học bạ THPT"]
                payload = _build_score_analysis_payload(mode)
                
                prov_val = None if filter_province == "Tất cả" else filter_province
                major_val = filter_major.strip() if filter_major.strip() else None
                
                with st.spinner("Đang quét dữ liệu điểm chuẩn..."):
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
            if st.button("Quay lại", icon=":material/arrow_back:", key="sa_back_err"):
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

        st.markdown(
            '<h3 style="display: flex; align-items: center; gap: 8px; margin-top: 1.5rem; margin-bottom: 0.8rem; font-size: 1.35rem; font-weight: 600;">'
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trending-up" style="vertical-align: middle;"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>'
            'Phân tích Năng lực'
            '</h3>',
            unsafe_allow_html=True
        )
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
        st.markdown(
            '<h3 style="display: flex; align-items: center; gap: 8px; margin-top: 1.5rem; margin-bottom: 0.8rem; font-size: 1.35rem; font-weight: 600;">'
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trophy" style="vertical-align: middle;"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.45 1-1 1H4v2h16v-2h-5c-.55 0-1-.45-1-1v-2.34"/><path d="M12 2a6 6 0 0 1 6 6v3.58a6 6 0 0 1-5.99 6H12a6 6 0 0 1-6-6V8a6 6 0 0 1 6-6Z"/></svg>'
            'Top Tổ hợp Khối thi Mạnh nhất'
            '</h3>',
            unsafe_allow_html=True
        )
        top_combos = result.get("top_combinations", [])
        if top_combos:
            combo_cols = st.columns(min(len(top_combos), 5))
            for i, combo in enumerate(top_combos[:5]):
                with combo_cols[i]:
                    is_diem_liet = combo.get("has_diem_liet", False)
                    is_below = combo.get("below_threshold", False)
                    
                    if is_diem_liet:
                        status_class = "danger"
                        warning_html = '<div class="sa-combo-card-alert"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 4px;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>BỊ ĐIỂM LIỆT</div>'
                    elif is_below:
                        status_class = "warning"
                        warning_html = '<div class="sa-combo-card-alert"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 4px;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>Dưới ngưỡng 15</div>'
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
        st.markdown(
            f'<h3 style="display: flex; align-items: center; gap: 8px; margin-top: 1.5rem; margin-bottom: 0.8rem; font-size: 1.35rem; font-weight: 600;">'
            f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-graduation-cap" style="vertical-align: middle;"><path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"/><path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5"/><path d="M21.5 12v6"/></svg>'
            f'Top {len(result.get("matched_schools", []))} Trường Phù hợp'
            f'</h3>',
            unsafe_allow_html=True
        )
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
            st.caption("📏 = Nhân hệ số · 📊 = Thang điểm · ⚠️ = Điều kiện · 🎫 = Chứng chỉ · 📖 = Học bạ")
        else:
            st.info("Không tìm thấy trường phù hợp. Thử mở rộng phương thức xét tuyển hoặc kiểm tra lại điểm.")

        # --- Phân tích AI ---
        st.markdown(
            '<h3 style="display: flex; align-items: center; gap: 8px; margin-top: 1.5rem; margin-bottom: 0.8rem; font-size: 1.35rem; font-weight: 600;">'
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-sparkles" style="vertical-align: middle;"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="m5 3 1 2.5L8.5 6 6 7 5 9.5 4 7 1.5 6 4 5.5z"/><path d="m19 17 1 2.5 2.5.5-2.5 1-1 2.5-1-2.5-2.5-1 2.5-1z"/></svg>'
            'Phân tích Chuyên gia AI'
            '</h3>',
            unsafe_allow_html=True
        )
        if df is not None and not df.empty:
            cached_analysis = st.session_state.get("sa_ai_analysis_text")
            if cached_analysis:
                st.markdown(cached_analysis)
                if st.button("Phân tích lại", icon=":material/refresh:", key="sa_ai_retry", type="secondary"):
                    st.session_state.pop("sa_ai_analysis_text", None)
                    st.rerun()
            else:
                if st.button("Nhận Phân tích từ Chuyên gia AI", icon=":material/auto_awesome:", key="sa_btn_ai_analysis"):
                    with st.spinner("AI đang phân tích..."):
                        try:
                            stream = generate_analysis_stream(result)
                            if stream:
                                response_text = st.write_stream(stream)
                                st.session_state.sa_ai_analysis_text = response_text
                            else:
                                st.info("AI không thể phân tích lúc này. Vui lòng tham khảo bảng dữ liệu ở trên.")
                        except Exception as e:
                            st.warning(f"AI tạm thời không khả dụng: {e}")

        # --- Action buttons ---
        st.markdown("<br>", unsafe_allow_html=True)
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            if st.button("Phân tích lại", icon=":material/refresh:", key="sa_retry", use_container_width=True):
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

