import streamlit as st
from router import classify_query, dispatch_to_agent_stream
from agents.counselor import (
    build_counselor_system_prompt,
    counselor_respond_stream_from_prompt,
    doc_file,
    parse_cv_scores,
    retrieve_main_data,
)

def _dataframe_to_history_text(dataframe) -> str:
    try:
        return dataframe.to_csv(index=False)
    except Exception:
        return str(dataframe)

def _render_structured_response(response: dict) -> str:
    prefix = response.get("prefix", "")
    dataframe = response.get("dataframe")
    stream = response.get("stream")
    suffix = response.get("suffix", "")
    history_parts = []

    if prefix:
        st.write(prefix)
        history_parts.append(prefix.strip())

    if dataframe is not None:
        st.dataframe(dataframe, use_container_width=True, hide_index=True, height=400)
        table_text = _dataframe_to_history_text(dataframe).strip()
        if table_text:
            history_parts.append(f"### Bảng dữ liệu\n\n```csv\n{table_text}\n```")

    if stream is not None:
        commentary = st.write_stream(stream)
        if isinstance(commentary, list):
            commentary = "".join(str(item) for item in commentary)
        commentary = str(commentary or "").strip()
        if commentary:
            history_parts.append(commentary)

    if suffix:
        st.write(suffix)
        history_parts.append(suffix.strip())

    return "\n\n".join(part for part in history_parts if part)

def _process_query(query: str, uploaded_cv=None):
    """Xử lý câu hỏi qua pipeline: Router Classify → Agent Dispatch."""
    has_file = uploaded_cv is not None
    chat_history = st.session_state.messages[-4:]

    # === HIỆU ỨNG CHỜ "ĐANG SUY LUẬN" (SKELETON / TYPING) ===
    thinking_ui = st.empty()
    thinking_ui.markdown("""
        <div class="skeleton-container">
            <div class="skeleton-avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
            </div>
            <div class="skeleton-msg">
                <div class="skeleton-line" style="width: 90%;"></div>
                <div class="skeleton-line" style="width: 75%;"></div>
                <div class="skeleton-line" style="width: 50%;"></div>
            </div>
            <div class="skeleton-typing">✨ AI đang suy luận chuyên sâu<span>.</span><span>.</span><span>.</span></div>
        </div>
    """, unsafe_allow_html=True)

    # === BƯỚC 1: ROUTER PHÂN LOẠI ===
    classification = classify_query(query, has_file, chat_history)
    intent = classification["intent"]

    if classification.get("error_message"):
        st.warning(classification["error_message"])

    # === BƯỚC 2: AGENT XỬ LÝ ===
    if intent == "COUNSELOR" and uploaded_cv is not None:
        raw_ocr = doc_file(uploaded_cv)
        score_table = parse_cv_scores(raw_ocr)
        main_db_context = retrieve_main_data()
        system_prompt = build_counselor_system_prompt(score_table, query, main_db_context)
        
        response_generator = counselor_respond_stream_from_prompt(system_prompt, query)
        thinking_ui.empty()
        return st.write_stream(response_generator)
    else:
        response = dispatch_to_agent_stream(classification, query, uploaded_cv, chat_history)
        thinking_ui.empty()
        
        if isinstance(response, dict) and "dataframe" in response:
            return _render_structured_response(response)
        if isinstance(response, str):
            st.write(response)
            return response
        return st.write_stream(response)
