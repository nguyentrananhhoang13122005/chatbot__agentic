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


def _positive_session_float(key: str) -> float | None:
    try:
        value = float(st.session_state.get(key, 0) or 0)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _to_float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number

