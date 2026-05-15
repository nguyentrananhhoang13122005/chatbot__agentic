import streamlit as st
import sys
import io

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from llm_client import validate_api_key
from router import classify_query, dispatch_to_agent_stream
from chat_db import (
    init_db, new_session_id, save_session, list_sessions,
    load_session, delete_session, toggle_bookmark,
    cleanup_old_sessions, clear_all_sessions, format_session_date, rename_session
)

st.set_page_config(page_title="UniSearch AI", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# === KHỞI TẠO DB & DỌN DẸP TỰ ĐỘNG ===
init_db()
cleanup_old_sessions(days=20)


@st.cache_data(ttl=600, show_spinner=False)
def _cached_validate_api_key_v2():
    return validate_api_key()


def _process_query(query: str, uploaded_cv=None):
    """Xử lý câu hỏi qua pipeline: Router Classify → Agent Dispatch."""
    has_file = uploaded_cv is not None
    chat_history = st.session_state.messages[-4:]

    # === BƯỚC 1: ROUTER PHÂN LOẠI ===
    with st.status("🎛️ **Router** đang phân loại câu hỏi...", expanded=True) as status:
        classification = classify_query(query, has_file, chat_history)

        intent = classification["intent"]
        if intent == "GENERAL":
            agent_name = "General AI (Trả lời chung)"
            agent_icon = "🤖"
        elif intent == "COUNSELOR":
            agent_name = "Counselor (Tư vấn hướng nghiệp)"
            agent_icon = "🧑‍🏫"
        else:
            agent_name = "Recommender (Tra cứu điểm)"
            agent_icon = "📊"

        st.write(f"**Loại câu hỏi:** `{intent}`")
        st.write(f"**Giao cho:** {agent_icon} **{agent_name}**")
        if classification.get("error_message"):
            st.warning(classification["error_message"])
        if intent == "RECOMMENDER":
            st.write(f"**Trường:** `{classification.get('school', 'ALL')}` · **Ngành:** `{classification.get('keyword', 'ALL')}` · **Năm:** `{classification.get('year', 0) or 'Không xác định'}`")

        status.update(label=f"🎛️ Router → {agent_icon} {agent_name}", state="complete", expanded=False)

    # === BƯỚC 2: AGENT XỬ LÝ ===
    response_generator = dispatch_to_agent_stream(classification, query, uploaded_cv, chat_history)
    return st.write_stream(response_generator)

# ============================================================
# RISO DESIGN SYSTEM — Tokens from DESIGN.md
# Style: Playful two-color risograph-inspired system with paper-like warmth, vivid pink actions, and bold blue structure. clean, high-contrast.
# Typography: Space Grotesk (h1, body) / Overpass Mono (label-caps)
# Colors: primary=#F237A1 secondary=#2C40A7 success=#16A34A warning=#D97706 danger=#DC2626 surface=#FFFFFF text=#111827 neutral=#FFFFFF
# Rounded: sm=4px, md=8px
# Spacing: 4/8/12/16/24/32
# ============================================================
def load_custom_css():
    css = """
    :root {
        /* Colors from DESIGN.md */
        --primary: #F237A1;
        --secondary: #2C40A7;
        --success: #16A34A;
        --warning: #D97706;
        --danger: #DC2626;
        --surface: #FFFFFF;
        --text: #111827;
        --neutral: #FFFFFF;
        
        /* Extended paper-warmth & shades for Riso feel */
        --paper: #FDFBF7;
        --border: #111827;
        
        /* Typography from DESIGN.md */
        --font-sans: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        --font-mono: 'Overpass Mono', 'Cascadia Code', 'Consolas', 'Courier New', monospace;
        
        /* Rounded & Spacing from DESIGN.md */
        --radius-sm: 4px;
        --radius-md: 8px;
        --sp-4: 4px;
        --sp-8: 8px;
        --sp-12: 12px;
        --sp-16: 16px;
        --sp-24: 24px;
        --sp-32: 32px;
        
        /* Shadows for Risograph print effect */
        --riso-shadow: 4px 4px 0px var(--border);
        --riso-shadow-hover: 6px 6px 0px var(--primary);
    }

    /* STREAMLIT NATIVE CONTROLS PRESERVED & CUSTOMIZED */
    .block-container { padding-top:var(--sp-12)!important; max-width:100vw!important; }

    /* Fix Material Icons Globally (prevents raw text like keyboard_double_arrow_right) */
    span.material-symbols-rounded, 
    span[data-testid="stIconMaterial"],
    .material-icons {
        font-family: "Material Symbols Rounded", "Material Icons", sans-serif !important;
    }

    /* Custom Sidebar Toggle Icons: Replace with ☰ and ✕ but keep buttons clickable */
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stSidebarCollapseButton"] button,
    button[data-testid="collapsedControl"],
    button[data-testid="stSidebarCollapsedControl"],
    button[data-testid="stSidebarCollapseButton"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        z-index: 9999 !important;
        font-size: 0 !important;
        color: transparent !important;
    }
    
    /* Hide ONLY the inner contents (svg/span) so the button itself stays clickable */
    [data-testid="collapsedControl"] button > *,
    [data-testid="stSidebarCollapsedControl"] button > *,
    [data-testid="stSidebarCollapseButton"] button > *,
    button[data-testid="collapsedControl"] > *,
    button[data-testid="stSidebarCollapsedControl"] > *,
    button[data-testid="stSidebarCollapseButton"] > * {
        display: none !important;
    }
    
    /* Hamburger (☰) when collapsed */
    [data-testid="collapsedControl"] button::after,
    [data-testid="stSidebarCollapsedControl"] button::after,
    button[data-testid="collapsedControl"]::after,
    button[data-testid="stSidebarCollapsedControl"]::after {
        content: '☰' !important;
        font-size: 24px !important;
        color: var(--text) !important;
        font-family: var(--font-sans) !important;
        padding: 4px;
        visibility: visible !important;
    }
    
    /* Close (✕) when expanded */
    [data-testid="stSidebarCollapseButton"] button::after,
    button[data-testid="stSidebarCollapseButton"]::after {
        content: '✕' !important;
        font-size: 20px !important;
        color: var(--text) !important;
        font-family: var(--font-sans) !important;
        padding: 4px;
        visibility: visible !important;
    }

    /* === GLOBAL === */
    .stApp {
        background: linear-gradient(-45deg, var(--paper), rgba(242, 55, 161, 0.08), var(--surface), rgba(44, 64, 167, 0.08))!important;
        background-size: 400% 400%!important;
        animation: gradientBG 20s ease infinite!important;
    }
    .main, section[data-testid="stMain"] {
        background: transparent!important;
    }
    .stApp, .main, section[data-testid="stMain"], html, body {
        font-family: var(--font-sans)!important;
        color: var(--text)!important;
    }
    html,body,p,span,div,li,a,input,textarea,button,label {
        font-family: var(--font-sans)!important;
    }

    /* === SIDEBAR (bold blue structure) === */
    [data-testid="stSidebar"] {
        background: var(--surface)!important;
        border-right: 2px solid var(--border)!important;
    }
    [data-testid="stSidebar"][aria-expanded="true"] {
        min-width: 320px!important; width: 320px!important;
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: var(--sp-4)!important; }
    [data-testid="stSidebar"] > div *:not(.material-symbols-rounded) {
        font-family: var(--font-sans)!important;
    }
    [data-testid="stSidebar"] > div * {
        color: var(--text);
    }

    /* === HISTORY ITEM STYLE (Minimal & Flat) === */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker) {
        border-radius: 8px;
        transition: all 0.2s ease;
        padding: 2px 0;
        margin-bottom: 2px;
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker):hover {
        background: rgba(0,0,0,0.04);
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker.active) {
        background: rgba(44, 64, 167, 0.08);
        border-left: 3px solid var(--primary);
        border-radius: 0 8px 8px 0;
    }

    /* External timestamp below history item */
    .hist-time {
        font-family: var(--font-mono);
        font-size: 11px;
        color: #888;
        font-weight: 500;
        padding: 2px 8px 6px;
        line-height: 1;
        letter-spacing: 0.3px;
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker.active) + div .hist-time {
        color: var(--secondary);
        font-weight: 600;
    }
    
    /* Title Button (Left Aligned, Flat) */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker) div[data-testid="column"]:first-child div.stButton > button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: var(--text) !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 4px 8px !important;
        min-height: 32px !important;
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker) div[data-testid="column"]:first-child div.stButton > button p {
        font-weight: 500 !important;
        font-size: 14px !important;
        white-space: pre-wrap !important;
        line-height: 1.4 !important;
        margin: 0 !important;
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker.active) div[data-testid="column"]:first-child div.stButton > button p {
        font-weight: 700 !important;
        color: var(--secondary) !important;
    }
    
    /* Popover button (3 dots) — override Streamlit's emotion-cache white bg & overflow:hidden */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker) div[data-testid="column"]:last-child button,
    [data-testid="stSidebar"] div:has(.hist-row-marker) .stPopover button {
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: transparent !important;
        font-size: 0 !important;
        padding: 0 !important;
        min-height: 32px !important;
        width: 32px !important;
        opacity: 0.6;
        transition: all 0.2s ease;
        position: relative !important;
        overflow: visible !important;
    }
    
    /* Hide ALL child elements inside the popover button */
    [data-testid="stSidebar"] div:has(.hist-row-marker) .stPopover button * {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
    }
    
    /* Inject 3 dots via ::after pseudo-element */
    [data-testid="stSidebar"] div:has(.hist-row-marker) .stPopover button::after {
        content: "⋮";
        color: #666 !important;
        font-size: 22px !important;
        font-weight: bold !important;
        line-height: 32px !important;
        text-align: center !important;
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        visibility: visible !important;
        pointer-events: none !important;
    }
    
    /* Hover effects */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker) div[data-testid="column"]:last-child button:hover,
    [data-testid="stSidebar"] div:has(.hist-row-marker) .stPopover button:hover {
        opacity: 1;
        background: rgba(0,0,0,0.05) !important;
        border-radius: 6px;
    }
    [data-testid="stSidebar"] div:has(.hist-row-marker) .stPopover button:hover::after {
        color: var(--primary) !important;
    }
    
    /* Popover Menu Items */
    div[data-testid="stPopoverBody"] div.stButton > button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: var(--text) !important;
        text-align: left !important;
        justify-content: flex-start !important;
        font-size: 14px !important;
        padding: 8px 12px !important;
        width: 100% !important;
        border-radius: 4px !important;
    }
    div[data-testid="stPopoverBody"] div.stButton > button:hover {
        background: rgba(0,0,0,0.05) !important;
    }

    /* === BUTTONS (vivid pink actions) === */
    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="stBaseButton-primary"] {
        background: var(--primary)!important; color:var(--surface)!important;
        border:2px solid var(--border)!important; border-radius:var(--radius-md)!important;
        font-family:var(--font-sans)!important; font-weight:700!important;
        font-size:16px!important; padding:var(--sp-12) var(--sp-24)!important;
        box-shadow: var(--riso-shadow)!important;
        transition: all .2s ease-in-out!important;
        text-transform: uppercase;
    }
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[data-testid="stBaseButton-primary"]:hover {
        transform: translate(-2px, -2px)!important;
        box-shadow: 6px 6px 0px var(--secondary)!important;
    }
    
    div.stButton > button[kind="secondary"],
    div.stButton > button[data-testid="stBaseButton-secondary"] {
        background:var(--surface)!important; color:var(--text)!important;
        border:2px solid var(--border)!important; border-radius:var(--radius-md)!important;
        font-family:var(--font-sans)!important; font-weight:600!important;
        font-size:14px!important; padding:var(--sp-8) var(--sp-16)!important;
        box-shadow: 2px 2px 0px var(--border)!important;
        transition:all .2s ease!important;
    }
    div.stButton > button[kind="secondary"]:hover,
    div.stButton > button[data-testid="stBaseButton-secondary"]:hover {
        background:var(--secondary)!important; color:var(--surface)!important;
        box-shadow: 4px 4px 0px var(--primary)!important;
        transform: translate(-2px, -2px)!important;
    }
    
    /* Compact buttons in sidebar columns (bookmark, delete) */
    [data-testid="stSidebar"] div[data-testid="column"] div.stButton > button {
        padding: 4px!important; 
        font-size: 14px!important;
        min-height: 32px!important;
    }

    /* === SIDEBAR COMPONENTS === */
    .sb-header {
        text-align:center; padding:var(--sp-12) var(--sp-16) var(--sp-12);
        border-bottom:2px solid var(--border);
        margin:0 calc(var(--sp-16) * -1) var(--sp-12); 
        background: var(--surface);
    }
    .sb-header:hover .sb-logo {
        animation: float 2s ease-in-out infinite;
    }
    .sb-logo {
        font-size:36px; margin-bottom:var(--sp-4);
        filter: drop-shadow(2px 2px 0px var(--primary));
        display: inline-block;
    }
    .sb-name {
        font-family:var(--font-sans); font-size:24px; font-weight:800;
        color:var(--secondary); letter-spacing:-1px; text-transform: uppercase;
        margin-bottom: 2px;
    }
    .sb-tag {
        font-family:var(--font-mono);
        font-size:12px; color:var(--surface); 
        letter-spacing:1px; text-transform:uppercase; margin-top:var(--sp-4);
        background: var(--primary); display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm);
        border: 1px solid var(--border);
    }
    .sb-user {
        background:var(--surface); border-radius:var(--radius-md);
        padding:var(--sp-8); margin:0 0 var(--sp-12);
        border: 2px solid var(--border);
        box-shadow: 3px 3px 0px var(--secondary);
        display:flex; align-items:center; gap:var(--sp-12);
        transition: transform 0.2s, box-shadow 0.2s;
        cursor: pointer;
    }
    .sb-user:hover {
        transform: translate(-2px, -2px);
        box-shadow: 5px 5px 0px var(--primary);
    }
    .sb-user:hover .sb-avatar {
        animation: wiggle 0.5s ease;
    }
    .sb-avatar {
        width:40px; height:40px; border-radius:var(--radius-sm);
        background: var(--primary); border: 2px solid var(--border);
        display:flex; align-items:center; justify-content:center;
        font-size:20px; flex-shrink:0; color: var(--surface);
    }
    .sb-uname { font-weight:700; font-size:16px; color:var(--text); }
    .sb-urole { font-family: var(--font-mono); font-size:12px; color:var(--secondary); margin-top:2px; font-weight:600;}
    .sb-section {
        font-family: var(--font-mono);
        font-size:14px; font-weight:700; color:var(--text);
        text-transform:uppercase; letter-spacing:1px;
        margin:var(--sp-16) 0 var(--sp-8) 0;
        border-bottom: 2px solid var(--border);
        padding-bottom: var(--sp-4);
        display: inline-block;
    }
    .sb-divider { display:none; }

    /* === HERO === */
    .hero {
        text-align:center; padding:var(--sp-32) var(--sp-24);
        position:relative; margin-top: var(--sp-24);
    }
    .badge {
        font-family: var(--font-mono);
        display:inline-flex; align-items:center; gap:var(--sp-8);
        font-size:14px; font-weight:700; color:var(--surface);
        background:var(--secondary); border:2px solid var(--border);
        padding:var(--sp-8) var(--sp-16); border-radius:var(--radius-sm); 
        margin-bottom:var(--sp-32); text-transform: uppercase;
        box-shadow: 2px 2px 0px var(--primary);
    }
    .badge-dot {
        width:10px; height:10px; border-radius:50%;
        background:var(--primary); border: 1.5px solid var(--border);
    }
    .hero h1 {
        font-family:var(--font-sans); font-size:48px; font-weight:900;
        line-height:1.1; margin:0; color:var(--text); text-transform: uppercase;
        letter-spacing: -1px;
        animation: float-subtle 4s ease-in-out infinite;
    }
    .hero .hl-pink { color:var(--primary); text-shadow: 2px 2px 0px var(--border); display: inline-block; transition: transform 0.3s;}
    .hero .hl-pink:hover { transform: scale(1.05) rotate(-2deg); }
    .hero .hl-blue { color:var(--secondary); text-shadow: 2px 2px 0px var(--border); display: inline-block; transition: transform 0.3s;}
    .hero .hl-blue:hover { transform: scale(1.05) rotate(2deg); }
    .hero .desc {
        font-size:18px; color:var(--text); font-weight: 500;
        margin-top:var(--sp-24); line-height:1.5;
        max-width:600px; margin-left:auto; margin-right:auto;
        border: 2px solid var(--border); padding: var(--sp-16);
        background: var(--surface); box-shadow: var(--riso-shadow);
        border-radius: var(--radius-md);
        transition: all 0.3s;
    }
    .hero .desc:hover {
        box-shadow: var(--riso-shadow-hover);
        transform: translateY(-2px);
    }

    /* === STATS === */
    .stats {
        display:flex; justify-content:center; gap:var(--sp-24);
        margin:var(--sp-32) auto; max-width:700px;
    }
    .stat {
        flex:1; text-align:center; padding:var(--sp-24) var(--sp-12);
        background:var(--surface); border-radius:var(--radius-md);
        border:2px solid var(--border);
        box-shadow: 4px 4px 0px var(--secondary);
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .stat:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 8px 12px 0px var(--primary);
    }
    .stat-n {
        font-family:var(--font-sans); font-size:40px; font-weight:800;
        color:var(--text); text-shadow: 2px 2px 0px var(--primary);
    }
    .stat-l {
        font-family: var(--font-mono);
        font-size:14px; color:var(--text); font-weight: 700;
        text-transform:uppercase; margin-top:var(--sp-8);
    }

    /* === CARDS === */
    .cards-row { display:flex; gap:var(--sp-24); margin-top:var(--sp-32); padding-bottom: var(--sp-32); }
    .r-card {
        flex:1; background:var(--surface); border:2px solid var(--border);
        border-radius:var(--radius-md); padding:var(--sp-24); position:relative;
        box-shadow: var(--riso-shadow);
        transition:all .2s ease;
    }
    .r-card:hover {
        transform:translate(-4px, -4px);
        box-shadow: 8px 8px 0px var(--primary);
    }
    .r-card:hover .r-card-icon {
        transform: scale(1.15) rotate(10deg);
        box-shadow: 4px 4px 0px var(--text);
    }
    .r-card-num {
        font-family: var(--font-mono);
        font-size:24px; font-weight:700; color:var(--surface);
        background: var(--border); padding: 4px 8px; border-radius: var(--radius-sm);
        position:absolute; top:var(--sp-16); right:var(--sp-16); line-height:1;
    }
    .r-card-icon {
        width:56px; height:56px; border-radius:var(--radius-sm);
        display:inline-flex; align-items:center; justify-content:center;
        font-size:28px; margin-bottom:var(--sp-16);
        border: 2px solid var(--border);
        box-shadow: 2px 2px 0px var(--text);
        transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.4s;
    }
    .r-card-icon.pink { background:var(--primary); }
    .r-card-icon.blue { background:var(--secondary); }
    .r-card-title {
        font-size:20px; font-weight:800; color:var(--text); text-transform: uppercase;
        margin-bottom:var(--sp-12);
    }
    .r-card-desc {
        font-size:16px; color:var(--text); line-height:1.5; font-weight: 500;
    }
    .r-card.accent {
        background: var(--primary);
    }
    .r-card.accent .r-card-title, .r-card.accent .r-card-desc { color:var(--surface); }
    .r-card.accent .r-card-num { background: var(--surface); color: var(--primary); }
    .r-card.accent:hover { box-shadow: 8px 8px 0px var(--secondary); }

    /* === CHAT === */
    .chat-hdr {
        font-family: var(--font-mono); text-transform: uppercase;
        font-size:24px; font-weight:800; color:var(--surface);
        background: var(--secondary); border: 2px solid var(--border);
        display:flex; align-items:center; gap:var(--sp-12);
        padding:var(--sp-16); border-radius: var(--radius-md);
        margin-bottom:var(--sp-24); box-shadow: 4px 4px 0px var(--primary);
    }
    .chat-dot {
        width:12px; height:12px; border-radius:50%;
        background:var(--success); border: 2px solid var(--border); display:inline-block;
        animation: pulse-ring 2s infinite;
    }
    [data-testid="stChatMessage"] {
        font-family:var(--font-sans)!important; border-radius:var(--radius-md)!important;
        border:2px solid var(--border)!important;
        background:var(--surface)!important;
        margin-bottom:var(--sp-16)!important;
        box-shadow: 3px 3px 0px var(--text)!important;
        padding: var(--sp-16)!important;
        transition: transform 0.2s, box-shadow 0.2s!important;
    }
    [data-testid="stChatMessage"]:hover {
        transform: translateY(-2px)!important;
        box-shadow: 5px 5px 0px var(--secondary)!important;
    }
    [data-testid="stChatMessage"]:nth-child(even) {
        background: var(--paper)!important;
        box-shadow: 3px 3px 0px var(--secondary)!important;
    }
    [data-testid="stChatInput"] textarea {
        font-family:var(--font-sans)!important; background:var(--surface)!important;
        border:2px solid var(--border)!important;
        color:var(--text)!important; border-radius:var(--radius-md)!important;
        font-size:16px!important; font-weight: 500!important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color:var(--primary)!important;
        box-shadow: 4px 4px 0px var(--primary)!important;
    }
    /* === FILE UPLOADER (compatible across Streamlit versions) === */
    [data-testid="stFileUploader"] section {
        border:2px dashed var(--secondary)!important;
        border-radius:var(--radius-md)!important; background:var(--surface)!important;
        padding: var(--sp-16) var(--sp-24)!important;
        min-height: 80px!important;
        display: flex!important;
        align-items: center!important;
        justify-content: center!important;
        gap: var(--sp-12)!important;
    }
    [data-testid="stFileUploader"] section > input { display: none; }
    [data-testid="stFileUploader"] section button {
        background: var(--surface)!important;
        border: 2px solid var(--border)!important;
        border-radius: var(--radius-sm)!important;
        padding: var(--sp-8) var(--sp-16)!important;
        font-weight: 600!important;
        cursor: pointer!important;
        white-space: nowrap!important;
    }
    [data-testid="stFileUploader"] section button:hover {
        background: var(--secondary)!important;
        color: var(--surface)!important;
    }
    [data-testid="stFileUploader"] label {
        font-family: var(--font-sans)!important;
        font-weight: 600!important;
        color: var(--text)!important;
    }
    [data-testid="stFileUploader"] small {
        font-family: var(--font-mono)!important;
        color: var(--text)!important;
        opacity: 0.6;
    }
    hr { border-color:var(--border)!important; border-width: 2px!important; }
    [data-testid="stMarkdownContainer"] p { color:var(--text); font-size:16px; font-weight: 500;}

    /* === ANIMATIONS === */
    @property --num-200 {
        syntax: '<integer>';
        initial-value: 0;
        inherits: false;
    }
    @property --num-5k {
        syntax: '<integer>';
        initial-value: 0;
        inherits: false;
    }
    @keyframes count-200 {
        from { --num-200: 0; }
        to { --num-200: 200; }
    }
    @keyframes count-5k {
        from { --num-5k: 0; }
        to { --num-5k: 5000; }
    }
    .count-200 {
        animation: count-200 2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        counter-reset: num var(--num-200);
    }
    .count-200::after {
        content: counter(num) "+";
    }
    .count-5k {
        animation: count-5k 2.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        counter-reset: num5k var(--num-5k);
    }
    .count-5k::after {
        content: counter(num5k) "+";
    }

    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    @keyframes wiggle {
        0% { transform: rotate(0deg); }
        25% { transform: rotate(-15deg) scale(1.1); }
        50% { transform: rotate(15deg) scale(1.1); }
        75% { transform: rotate(-5deg) scale(1.1); }
        100% { transform: rotate(0deg) scale(1); }
    }
    @keyframes float-subtle {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-4px); }
    }
    @keyframes fadeSlideUp {
        0% { opacity: 0; transform: translateY(20px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-8px); }
    }
    @keyframes pulse-ring {
        0% { box-shadow: 0 0 0 0 rgba(242, 55, 161, 0.4); border-color: var(--primary); }
        70% { box-shadow: 0 0 0 6px rgba(242, 55, 161, 0); border-color: var(--border); }
        100% { box-shadow: 0 0 0 0 rgba(242, 55, 161, 0); border-color: var(--border); }
    }
    .anim-fade-up { opacity: 0; animation: fadeSlideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
    .anim-delay-1 { animation-delay: 0.1s; }
    .anim-delay-2 { animation-delay: 0.2s; }
    .anim-delay-3 { animation-delay: 0.3s; }
    .anim-delay-4 { animation-delay: 0.4s; }
    .badge { animation: float 3s ease-in-out infinite; }
    .badge-dot { animation: pulse-ring 2s infinite; }

    """
    # Embed Google Fonts via @import inside <style> (works reliably in body, unlike <link>)
    # Also add robust fallback stack for networks that block Google Fonts
    font_import = """
    @import url('https://fonts.googleapis.com/css2?family=Overpass+Mono:wght@400;600;700&family=Space+Grotesk:wght@300;400;500;600;700;800;900&display=swap');
    """
    st.markdown(f"<style>{font_import}\n{css}</style>", unsafe_allow_html=True)


# === SESSION STATE ===
if "page" not in st.session_state:
    st.session_state.page = "home"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = new_session_id()


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

        st.markdown("""
        <div class="sb-user">
            <div class="sb-avatar">👦</div>
            <div>
                <div class="sb-uname">Học sinh lớp 12</div>
                <div class="sb-urole">PHIÊN TRA CỨU</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("＋ Phiên tư vấn mới", use_container_width=True, type="primary"):
            # Lưu phiên hiện tại trước khi tạo mới
            if st.session_state.messages:
                save_session(st.session_state.session_id, st.session_state.messages)
            st.session_state.session_id = new_session_id()
            st.session_state.messages = []
            st.session_state.page = "chat"
            st.rerun()

        if st.button("💬 Trò chuyện hiện tại", use_container_width=True, type="secondary"):
            st.session_state.page = "chat"
            st.rerun()

        # ─── LỊCH SỬ GẦN ĐÂY (từ SQLite) ───
        st.markdown('<div class="sb-section">Lịch sử gần đây</div>', unsafe_allow_html=True)

        recent_sessions = list_sessions(limit=15)
        if not recent_sessions:
            st.caption("Chưa có lịch sử chat.")
        else:
            for sess in recent_sessions:
                sid = sess["id"]
                is_current = (sid == st.session_state.get("session_id"))
                
                with st.container():
                    st.markdown(f'<div class="hist-row-marker {"active" if is_current else ""}"></div>', unsafe_allow_html=True)
                    
                    # Tính toán thời gian trước khi render
                    import datetime
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
                                rename_session(sid, new_name.strip())
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
                                if st.session_state.messages:
                                    save_session(st.session_state.session_id, st.session_state.messages)
                                st.session_state.session_id = sid
                                st.session_state.messages = load_session(sid)
                                st.session_state.page = "chat"
                                st.rerun()
                        with col2:
                            with st.popover("⋮", use_container_width=True):
                                pin_label = "Bỏ ghim" if sess["bookmarked"] else "Ghim"
                                if st.button(f"📌 {pin_label}", key=f"bm_{sid}", use_container_width=True):
                                    toggle_bookmark(sid)
                                    st.rerun()
                                if st.button("✏️ Đổi tên", key=f"rn_btn_{sid}", use_container_width=True):
                                    st.session_state.rename_sid = sid
                                    st.rerun()
                                if st.session_state.get("confirm_delete_sid") == sid:
                                    st.warning("Bạn có chắc muốn xóa?")
                                    cd1, cd2 = st.columns(2)
                                    if cd1.button("⚠️ Xác nhận", key=f"cf_del_{sid}", use_container_width=True):
                                        delete_session(sid)
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

        # ─── HỆ THỐNG ───
        st.markdown('<div class="sb-section">Hệ thống</div>', unsafe_allow_html=True)
        st.caption("💡 Phiên chưa ghim sẽ tự động xóa sau 20 ngày")
        if st.button("🧹 Xoá toàn bộ lịch sử", use_container_width=True, type="secondary"):
            clear_all_sessions()
            st.session_state.session_id = new_session_id()
            st.session_state.messages = []
            st.toast("✅ Đã xoá toàn bộ lịch sử chat.")
            st.rerun()


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
    _, cc, _ = st.columns([1.2, 1, 1.2])
    with cc:
        if st.button("Bắt đầu trò chuyện", use_container_width=True, type="primary"):
            st.session_state.page = "chat"
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
        with st.chat_message("assistant", avatar="🤖"):
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
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
            st.write(msg["content"])

    # Xử lý câu hỏi đang chờ (từ nút gợi ý)
    if "pending_query" in st.session_state:
        pending = st.session_state.pending_query
        del st.session_state.pending_query
        st.session_state.messages.append({"role": "user", "content": pending})
        with st.chat_message("user", avatar="👤"):
            st.write(pending)
        with st.chat_message("assistant", avatar="🤖"):
            response = _process_query(pending, uploaded_cv)
        if response:
            st.session_state.messages.append({"role": "assistant", "content": str(response)})
        # === AUTO-SAVE ===
        if st.session_state.messages:
            save_session(st.session_state.session_id, st.session_state.messages)

    # Xử lý câu hỏi nhập từ ô chat
    if prompt := st.chat_input("Nhập câu hỏi... (VD: Điểm chuẩn Bách Khoa 2024?)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)
        with st.chat_message("assistant", avatar="🤖"):
            response = _process_query(prompt, uploaded_cv)
        if response:
            st.session_state.messages.append({"role": "assistant", "content": str(response)})
        # === AUTO-SAVE ===
        if st.session_state.messages:
            save_session(st.session_state.session_id, st.session_state.messages)


# === RENDER ===
load_custom_css()
api_key_valid, api_key_error = _cached_validate_api_key_v2()
if not api_key_valid:
    st.warning(api_key_error)
render_sidebar()
if st.session_state.page == "home":
    render_home_page()
else:
    render_chat_page()
