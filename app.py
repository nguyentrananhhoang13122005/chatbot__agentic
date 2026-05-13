import streamlit as st
import sys
import io

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from router import classify_query, dispatch_to_agent

st.set_page_config(page_title="UniSearch AI", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")


def _process_query(query: str, uploaded_cv=None):
    """Xử lý câu hỏi qua pipeline: Router Classify → Agent Dispatch."""
    has_file = uploaded_cv is not None
    chat_history = st.session_state.messages[-4:]

    # === BƯỚC 1: ROUTER PHÂN LOẠI ===
    with st.status("🎛️ **Router** đang phân loại câu hỏi...", expanded=True) as status:
        classification = classify_query(query, has_file, chat_history)

        intent = classification["intent"]
        agent_name = "Recommender (Tra cứu điểm)" if intent == "RECOMMENDER" else "Counselor (Tư vấn hướng nghiệp)"
        agent_icon = "📊" if intent == "RECOMMENDER" else "🧑‍🏫"

        st.write(f"**Loại câu hỏi:** `{intent}`")
        st.write(f"**Giao cho:** {agent_icon} **{agent_name}**")
        if intent == "RECOMMENDER":
            st.write(f"**Trường:** `{classification.get('school', 'ALL')}` · **Ngành:** `{classification.get('keyword', 'ALL')}` · **Năm:** `{classification.get('year', 0) or 'Không xác định'}`")

        status.update(label=f"🎛️ Router → {agent_icon} {agent_name}", state="complete", expanded=False)

    # === BƯỚC 2: AGENT XỬ LÝ ===
    with st.spinner(f"{agent_icon} **{agent_name}** đang xử lý..."):
        response = dispatch_to_agent(classification, query, uploaded_cv)

    st.write(response)
    return response

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

    /* === HIDE STREAMLIT CHROME === */
    [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stAppDeployButton"],
    footer, #MainMenu, div[class*="StatusWidget"],
    header[data-testid="stHeader"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"]
    { display:none!important; visibility:hidden!important; }
    .block-container { padding-top:var(--sp-12)!important; max-width:100vw!important; }

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
    [data-testid="stSidebar"],
    [data-testid="stSidebar"][aria-expanded="false"],
    [data-testid="stSidebar"][aria-expanded="true"] {
        background: var(--surface)!important;
        border-right: 2px solid var(--border)!important;
        min-width: 320px!important; width: 320px!important;
        display: flex!important; visibility: visible!important;
        transform: none!important; opacity: 1!important;
        position: relative!important; z-index: 999!important;
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: var(--sp-4)!important; }
    [data-testid="stSidebar"] * {
        font-family: var(--font-sans)!important;
        color: var(--text)!important;
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
            st.session_state.page = "home"
            st.session_state.messages = []
            st.rerun()

        if st.button("💬 Trò chuyện hiện tại", use_container_width=True, type="secondary"):
            st.session_state.page = "chat"
            st.rerun()

        st.markdown('<div class="sb-section">Lịch sử gần đây</div>', unsafe_allow_html=True)
        st.button("Bách Khoa vs KHTN", use_container_width=True, type="secondary")
        st.button("Ngành Marketing", use_container_width=True, type="secondary")
        st.button("Mục đã lưu", use_container_width=True, type="secondary")

        st.markdown('<div class="sb-section">Hệ thống</div>', unsafe_allow_html=True)
        st.button("Cài đặt", use_container_width=True, type="secondary")
        st.button("Trợ giúp", use_container_width=True, type="secondary")


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
        st.session_state.messages.append({"role": "assistant", "content": response})

    # Xử lý câu hỏi nhập từ ô chat
    if prompt := st.chat_input("Nhập câu hỏi... (VD: Điểm chuẩn Bách Khoa 2024?)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)
        with st.chat_message("assistant", avatar="🤖"):
            response = _process_query(prompt, uploaded_cv)
        st.session_state.messages.append({"role": "assistant", "content": response})


# === RENDER ===
load_custom_css()
render_sidebar()
if st.session_state.page == "home":
    render_home_page()
else:
    render_chat_page()
