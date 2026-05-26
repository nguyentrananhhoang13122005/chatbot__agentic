import streamlit as st

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

    /* === DARK MODE VARIABLE OVERRIDES === */
    html[data-theme="dark"] {
        --surface: #1A1A2E;
        --paper: #16162A;
        --text: #F0F0F5;
        --border: #3A3A5C;
        --neutral: #1A1A2E;
        
        --riso-shadow: 4px 4px 0px rgba(242, 55, 161, 0.3);
        --riso-shadow-hover: 6px 6px 0px var(--primary);
    }

    /* STREAMLIT NATIVE CONTROLS PRESERVED & CUSTOMIZED */
    .block-container { padding-top:4rem!important; padding-bottom:8rem!important; max-width:100vw!important; }
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

    /* === SIDEBAR FLEX LAYOUT (sticky bottom user) === */
    [data-testid="stSidebar"] > div:first-child {
        display: flex !important;
        flex-direction: column !important;
        min-height: 100vh !important;
    }
    [data-testid="stSidebar"] > div:first-child > div[data-testid="stVerticalBlock"] {
        display: flex !important;
        flex-direction: column !important;
        flex-grow: 1 !important;
    }

    /* Bottom spacer pushes user section to bottom */
    .sb-bottom-spacer { display: none; }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.sb-bottom-spacer) {
        flex-grow: 1 !important;
        min-height: var(--sp-24) !important;
    }

    /* === BOTTOM USER PROFILE CARD === */
    /* Container border-top separator (class added via JS) */
    .sb-user-card-container {
        border-top: 2px solid var(--border) !important;
        padding-top: var(--sp-8) !important;
        margin-top: var(--sp-8) !important;
    }

    /* Popover trigger → user card appearance (class added via JS) */
    button.sb-user-card-btn {
        background: var(--surface) !important;
        border: 2px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        box-shadow: 3px 3px 0px var(--secondary) !important;
        display: flex !important;
        align-items: center !important;
        gap: var(--sp-12) !important;
        padding: var(--sp-8) var(--sp-12) !important;
        min-height: 56px !important;
        text-align: left !important;
        justify-content: flex-start !important;
        cursor: pointer !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        position: relative !important;
        overflow: hidden !important;
        width: 100% !important;
        font-size: 0 !important;
        color: transparent !important;
    }

    /* Hover effect — Riso style */
    button.sb-user-card-btn:hover {
        transform: translate(-2px, -2px) !important;
        box-shadow: 5px 5px 0px var(--primary) !important;
    }

    /* Hide ALL inner elements (expand_more/expand_less icons, p, span) */
    button.sb-user-card-btn * {
        display: none !important;
        visibility: hidden !important;
        font-size: 0 !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
        position: absolute !important;
    }

    /* Avatar via ::before */
    button.sb-user-card-btn::before {
        content: attr(data-avatar);
        width: 40px;
        height: 40px;
        min-width: 40px;
        border-radius: var(--radius-sm);
        background: var(--primary);
        border: 2px solid var(--border);
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 18px !important;
        font-weight: 800 !important;
        color: var(--surface) !important;
        visibility: visible !important;
        flex-shrink: 0;
    }

    /* Name + email via ::after */
    button.sb-user-card-btn::after {
        content: attr(data-label);
        font-size: 14px !important;
        font-weight: 600 !important;
        color: var(--text) !important;
        font-family: var(--font-sans) !important;
        visibility: visible !important;
        white-space: pre-line !important;
        line-height: 1.4 !important;
        text-align: left !important;
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* === USER PROFILE POPUP MENU === */
    .sb-user-popover div[data-testid="stPopoverBody"] {
        border: 2px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        box-shadow: 4px 4px 0px var(--secondary) !important;
        padding: var(--sp-8) !important;
        background: var(--surface) !important;
        animation: popupFadeSlideUp 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
        min-width: 200px !important;
    }

    /* Popup menu buttons */
    .sb-user-popover div[data-testid="stPopoverBody"] div.stButton > button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: var(--text) !important;
        text-align: left !important;
        justify-content: flex-start !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        padding: var(--sp-8) var(--sp-12) !important;
        width: 100% !important;
        border-radius: var(--radius-sm) !important;
        transition: background 0.15s ease, color 0.15s ease !important;
        cursor: pointer !important;
    }

    /* Menu item hover */
    .sb-user-popover div[data-testid="stPopoverBody"] div.stButton > button:hover {
        background: rgba(242, 55, 161, 0.08) !important;
        color: var(--primary) !important;
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
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker) .stPopover button {
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
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker) .stPopover button * {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
    }
    
    /* Inject 3 dots via ::after pseudo-element */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker) .stPopover button::after {
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
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker) .stPopover button:hover {
        opacity: 1;
        background: rgba(0,0,0,0.05) !important;
        border-radius: 6px;
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker) .stPopover button:hover::after {
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

    .login-btn-container {
        display: none;
    }
    div[data-testid="stVerticalBlock"] > div:has(.login-btn-container) + div div.stButton > button,
    .login-btn-container .stButton > button {
        position: fixed !important;
        top: 14px !important;
        right: 80px !important;
        z-index: 9998 !important;
        background: var(--surface) !important;
        border: 2px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        font-family: var(--font-sans) !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        padding: 8px 20px !important;
        color: var(--text) !important;
        box-shadow: 2px 2px 0px var(--border) !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
        width: auto !important;
    }
    div[data-testid="stVerticalBlock"] > div:has(.login-btn-container) + div div.stButton > button:hover,
    .login-btn-container .stButton > button:hover {
        background: var(--primary) !important;
        color: var(--surface) !important;
        transform: translate(-2px, -2px) !important;
        box-shadow: 4px 4px 0px var(--secondary) !important;
    }
    div[data-testid="stDialog"] [data-testid="stDialogContent"] {
        font-family: var(--font-sans) !important;
    }
    div[data-testid="stDialog"] .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    div[data-testid="stDialog"] .stTabs [data-baseweb="tab"] {
        font-family: var(--font-mono) !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    div[data-testid="stDialog"] .stLinkButton a {
        background: var(--surface) !important;
        border: 2px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text) !important;
        font-weight: 700 !important;
        box-shadow: 2px 2px 0px var(--border) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stDialog"] .stLinkButton a:hover {
        transform: translate(-2px, -2px) !important;
        box-shadow: 4px 4px 0px var(--secondary) !important;
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
    .guest-login-card-marker {
        display: none;
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.guest-login-card-marker) + div div.stButton > button {
        background: var(--surface) !important;
        border: 2px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        box-shadow: 3px 3px 0px var(--secondary) !important;
        color: var(--text) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: var(--sp-12) !important;
        min-height: 60px !important;
        padding: var(--sp-8) !important;
        margin: 0 0 6px !important;
        text-align: left !important;
        opacity: 1 !important;
        transition: transform 0.2s, box-shadow 0.2s !important;
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.guest-login-card-marker) + div div.stButton > button:hover {
        background: var(--surface) !important;
        color: var(--text) !important;
        transform: translate(-2px, -2px) !important;
        box-shadow: 5px 5px 0px var(--primary) !important;
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.guest-login-card-marker) + div div.stButton > button::before {
        content: "👤";
        width: 40px;
        height: 45px;
        border-radius: var(--radius-sm);
        background: var(--primary);
        border: 2px solid var(--border);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        flex-shrink: 0;
        color: var(--surface);
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.guest-login-card-marker) + div div.stButton > button p {
        white-space: pre-line !important;
        text-align: left !important;
        line-height: 1.35 !important;
        margin: 0 !important;
        color: #777 !important;
        font-family: var(--font-mono) !important;
        font-size: 12px !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.guest-login-card-marker) + div div.stButton > button p::first-line {
        color: var(--text) !important;
        font-family: var(--font-sans) !important;
        font-size: 16px !important;
        font-weight: 700 !important;
    }
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
        position:relative; margin-top: 0;
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

    .stChatInput {
        border-radius: var(--radius-md)!important;
        border: 2px solid var(--border)!important;
        box-shadow: var(--riso-shadow)!important;
    }

    /* === CUSTOM CHAT INPUT BAR (replaces st.chat_input for mic integration) === */
    .custom-chat-bar {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        z-index: 99 !important;
        background: var(--surface, #fff) !important;
        border-top: 2px solid var(--border, #e0e0e0) !important;
        padding: 12px 16px !important;
    }
    .custom-chat-bar .stTextInput > div > div {
        border-radius: var(--radius-md, 12px) !important;
        border: 2px solid var(--border, #ccc) !important;
    }
    .custom-chat-bar .stTextInput > div > div:focus-within {
        border-color: var(--primary, #1a237e) !important;
        box-shadow: 4px 4px 0px var(--primary, #1a237e) !important;
    }
    .custom-chat-bar .stTextInput input {
        font-family: var(--font-sans) !important;
        font-size: 16px !important;
        font-weight: 500 !important;
        color: var(--text) !important;
        background: var(--surface, #fff) !important;
    }
    /* Hide labels in the custom chat bar */
    .custom-chat-bar .stTextInput label,
    .custom-chat-bar .stButton label {
        display: none !important;
    }
    /* Send button styling */
    .custom-chat-bar .stButton button {
        border-radius: var(--radius-md, 12px) !important;
        background: var(--primary, #1a237e) !important;
        color: white !important;
        border: 2px solid var(--text, #1a1a2e) !important;
        font-weight: 700 !important;
        padding: 8px 16px !important;
        height: 42px !important;
        box-shadow: 3px 3px 0px var(--text, #1a1a2e) !important;
        transition: transform 0.1s, box-shadow 0.1s !important;
    }
    .custom-chat-bar .stButton button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 4px 4px 0px var(--text, #1a1a2e) !important;
    }
    .custom-chat-bar .stButton button:active {
        transform: translateY(1px) !important;
        box-shadow: 1px 1px 0px var(--text, #1a1a2e) !important;
    }
    /* Mic recorder inside column — no hack needed */
    .custom-chat-bar iframe[title="streamlit_mic_recorder.streamlit_mic_recorder"] {
        border: none !important;
        border-radius: 50% !important;
        width: 42px !important;
        height: 42px !important;
    }
    /* Add bottom padding to main content to prevent chat bar overlap */
    [data-testid="stBottomBlockContainer"] {
        padding-bottom: 80px !important;
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
    @keyframes popupFadeSlideUp {
        0% { opacity: 0; transform: translateY(8px) scale(0.96); }
        100% { opacity: 1; transform: translateY(0) scale(1); }
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

    /* === RESPONSIVE TABLES === */
    [data-testid="stMarkdownContainer"] table {
        display: block !important;
        overflow-x: auto !important;
        white-space: nowrap !important;
        width: 100% !important;
        border-collapse: collapse;
    }
    [data-testid="stMarkdownContainer"] th,
    [data-testid="stMarkdownContainer"] td {
        padding: 8px 16px;
        border: 1px solid var(--border);
    }

    /* === FIX CHAT INPUT TO BOTTOM === */
    section[data-testid="stBottom"] {
        position: fixed !important;
        bottom: 0 !important;
        z-index: 9999 !important;
        background: var(--surface) !important;
        border-top: 2px solid var(--border) !important;
        padding-bottom: max(16px, env(safe-area-inset-bottom)) !important;
        box-shadow: 0 -4px 10px rgba(0,0,0,0.05) !important;
    }

    /* === SMOOTH SIDEBAR MOBILE === */
    [data-testid="stSidebar"] {
        transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.05), width 0.4s ease !important;
        will-change: transform, width;
    }

    /* === SKELETON LOADING / TYPING EFFECT === */
    .skeleton-container {
        display: flex;
        gap: var(--sp-16);
        padding: var(--sp-16);
        background: var(--surface);
        border: 2px solid var(--border);
        border-radius: var(--radius-md);
        margin-bottom: var(--sp-32);
        box-shadow: 3px 3px 0px var(--text);
        position: relative;
    }
    .skeleton-avatar {
        width: 36px;
        height: 36px;
        border-radius: var(--radius-sm);
        background: rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        border: 2px solid var(--border);
        animation: pulse-bg 1.5s infinite;
    }
    .skeleton-msg {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: var(--sp-8);
        justify-content: center;
        margin-top: var(--sp-4);
    }
    .skeleton-line {
        height: 10px;
        background: rgba(0,0,0,0.08);
        border-radius: var(--radius-sm);
        animation: pulse-bg 1.5s infinite;
    }
    .skeleton-typing {
        position: absolute;
        bottom: -24px;
        left: 12px;
        font-size: 12px;
        font-family: var(--font-mono);
        color: var(--secondary);
        font-weight: 700;
        white-space: nowrap;
    }
    .skeleton-typing span {
        animation: blink 1.4s infinite both;
        font-size: 14px;
    }
    .skeleton-typing span:nth-child(2) { animation-delay: 0.2s; }
    .skeleton-typing span:nth-child(3) { animation-delay: 0.4s; }
    
    @keyframes blink {
        0% { opacity: 0.2; }
        20% { opacity: 1; }
        100% { opacity: 0.2; }
    }
    @keyframes pulse-bg {
        0% { opacity: 0.6; }
        50% { opacity: 0.2; }
        100% { opacity: 0.6; }
    }

    /* ============================================================
       DARK MODE — Component Overrides
       ============================================================ */

    /* --- Global Background --- */
    html[data-theme="dark"] .stApp {
        background: linear-gradient(-45deg, var(--paper), rgba(242, 55, 161, 0.06), #1E1E36, rgba(44, 64, 167, 0.06))!important;
    }
    html[data-theme="dark"] .stApp,
    html[data-theme="dark"] .main,
    html[data-theme="dark"] section[data-testid="stMain"],
    html[data-theme="dark"] html,
    html[data-theme="dark"] body {
        color: var(--text)!important;
    }

    /* --- Sidebar --- */
    html[data-theme="dark"] [data-testid="stSidebar"] {
        background: #1E1E36!important;
        border-right: 2px solid var(--border)!important;
    }
    html[data-theme="dark"] [data-testid="stSidebar"] > div * {
        color: var(--text);
    }
    html[data-theme="dark"] .sb-header {
        background: #1E1E36;
        border-bottom: 2px solid var(--border);
    }
    html[data-theme="dark"] .sb-tag {
        color: var(--surface);
    }
    html[data-theme="dark"] .sb-section {
        color: var(--text);
        border-bottom-color: var(--border);
    }

    /* --- Bottom User Profile (Dark Mode) --- */
    html[data-theme="dark"] .sb-user-card-container {
        border-top-color: var(--border);
    }

    html[data-theme="dark"] button.sb-user-card-btn {
        background: var(--surface) !important;
        border-color: var(--border) !important;
        box-shadow: 3px 3px 0px rgba(44, 64, 167, 0.5) !important;
    }
    html[data-theme="dark"] button.sb-user-card-btn:hover {
        box-shadow: 5px 5px 0px var(--primary) !important;
    }
    html[data-theme="dark"] button.sb-user-card-btn::before {
        border-color: var(--border);
    }
    html[data-theme="dark"] button.sb-user-card-btn::after {
        color: var(--text) !important;
    }

    /* Popup menu dark mode */
    html[data-theme="dark"] .sb-user-popover div[data-testid="stPopoverBody"] {
        background: var(--surface) !important;
        border-color: var(--border) !important;
        box-shadow: 4px 4px 0px rgba(44, 64, 167, 0.4) !important;
    }
    html[data-theme="dark"] .sb-user-popover div[data-testid="stPopoverBody"] div.stButton > button {
        color: var(--text) !important;
    }
    html[data-theme="dark"] .sb-user-popover div[data-testid="stPopoverBody"] div.stButton > button:hover {
        background: rgba(242, 55, 161, 0.12) !important;
        color: var(--primary) !important;
    }

    /* --- History Items --- */
    html[data-theme="dark"] [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker):hover {
        background: rgba(255,255,255,0.05);
    }
    html[data-theme="dark"] [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker.active) {
        background: rgba(44, 64, 167, 0.15);
    }
    html[data-theme="dark"] [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker) div[data-testid="column"]:first-child div.stButton > button {
        color: var(--text) !important;
    }
    html[data-theme="dark"] .hist-time { color: #888; }
    html[data-theme="dark"] [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker) .stPopover button::after {
        color: #aaa !important;
    }
    html[data-theme="dark"] [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker) .stPopover button:hover {
        background: rgba(255,255,255,0.08) !important;
    }
    html[data-theme="dark"] [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:has(.hist-row-marker) .stPopover button:hover::after {
        color: var(--primary) !important;
    }

    /* --- Popover Menu --- */
    html[data-theme="dark"] div[data-testid="stPopoverBody"] {
        background: var(--surface) !important;
        border-color: var(--border) !important;
    }
    html[data-theme="dark"] div[data-testid="stPopoverBody"] div.stButton > button {
        color: var(--text) !important;
    }
    html[data-theme="dark"] div[data-testid="stPopoverBody"] div.stButton > button:hover {
        background: rgba(255,255,255,0.08) !important;
    }

    /* --- Buttons --- */
    html[data-theme="dark"] div.stButton > button[kind="secondary"],
    html[data-theme="dark"] div.stButton > button[data-testid="stBaseButton-secondary"] {
        background: var(--surface)!important;
        color: var(--text)!important;
        border-color: var(--border)!important;
        box-shadow: 2px 2px 0px rgba(242, 55, 161, 0.3)!important;
    }
    html[data-theme="dark"] div.stButton > button[kind="secondary"]:hover,
    html[data-theme="dark"] div.stButton > button[data-testid="stBaseButton-secondary"]:hover {
        background: var(--secondary)!important;
        color: #FFFFFF!important;
        box-shadow: 4px 4px 0px var(--primary)!important;
    }
    html[data-theme="dark"] div.stButton > button[kind="primary"],
    html[data-theme="dark"] div.stButton > button[data-testid="stBaseButton-primary"] {
        border-color: var(--border)!important;
        box-shadow: var(--riso-shadow)!important;
    }
    html[data-theme="dark"] div[data-testid="stVerticalBlock"] > div:has(.login-btn-container) + div div.stButton > button,
    html[data-theme="dark"] .login-btn-container .stButton > button {
        background: var(--surface) !important;
        color: var(--text) !important;
        border-color: var(--border) !important;
        box-shadow: 2px 2px 0px rgba(242, 55, 161, 0.3) !important;
    }
    html[data-theme="dark"] div[data-testid="stVerticalBlock"] > div:has(.login-btn-container) + div div.stButton > button:hover,
    html[data-theme="dark"] .login-btn-container .stButton > button:hover {
        background: var(--primary) !important;
        color: #FFFFFF !important;
        box-shadow: 4px 4px 0px var(--secondary) !important;
    }
    html[data-theme="dark"] div[data-testid="stDialog"] [data-testid="stDialogContent"],
    html[data-theme="dark"] div[data-testid="stDialog"] .stLinkButton a {
        background: var(--surface) !important;
        color: var(--text) !important;
        border-color: var(--border) !important;
    }

    /* --- Hero --- */
    html[data-theme="dark"] .hero .desc {
        background: var(--surface);
        border-color: var(--border);
        box-shadow: var(--riso-shadow);
        color: var(--text);
    }
    html[data-theme="dark"] .hero h1 { color: var(--text); }
    html[data-theme="dark"] .hero .hl-pink { text-shadow: 2px 2px 0px rgba(242, 55, 161, 0.3); }
    html[data-theme="dark"] .hero .hl-blue { text-shadow: 2px 2px 0px rgba(44, 64, 167, 0.3); }

    /* --- Stats --- */
    html[data-theme="dark"] .stat {
        background: var(--surface);
        border-color: var(--border);
        box-shadow: 4px 4px 0px rgba(44, 64, 167, 0.4);
    }
    html[data-theme="dark"] .stat:hover {
        box-shadow: 8px 12px 0px var(--primary);
    }
    html[data-theme="dark"] .stat-n { color: var(--text); text-shadow: 2px 2px 0px rgba(242, 55, 161, 0.3); }
    html[data-theme="dark"] .stat-l { color: var(--text); }

    /* --- Cards --- */
    html[data-theme="dark"] .r-card {
        background: var(--surface);
        border-color: var(--border);
        box-shadow: var(--riso-shadow);
    }
    html[data-theme="dark"] .r-card:hover {
        box-shadow: 8px 8px 0px var(--primary);
    }
    html[data-theme="dark"] .r-card-title { color: var(--text); }
    html[data-theme="dark"] .r-card-desc { color: var(--text); }
    html[data-theme="dark"] .r-card-num { background: var(--border); color: var(--text); }
    html[data-theme="dark"] .r-card-icon { border-color: var(--border); box-shadow: 2px 2px 0px rgba(242, 55, 161, 0.3); }
    html[data-theme="dark"] .r-card.accent .r-card-num { background: var(--surface); color: var(--primary); }

    /* --- Chat --- */
    html[data-theme="dark"] .chat-hdr {
        border-color: var(--border);
        box-shadow: 4px 4px 0px rgba(242, 55, 161, 0.4);
    }
    html[data-theme="dark"] [data-testid="stChatMessage"] {
        background: var(--surface)!important;
        border-color: var(--border)!important;
        box-shadow: 3px 3px 0px rgba(242, 55, 161, 0.2)!important;
    }
    html[data-theme="dark"] [data-testid="stChatMessage"]:hover {
        box-shadow: 5px 5px 0px rgba(44, 64, 167, 0.4)!important;
    }
    html[data-theme="dark"] [data-testid="stChatMessage"]:nth-child(even) {
        background: var(--paper)!important;
        box-shadow: 3px 3px 0px rgba(44, 64, 167, 0.3)!important;
    }
    html[data-theme="dark"] [data-testid="stChatInput"] textarea {
        background: var(--surface)!important;
        border-color: var(--border)!important;
        color: var(--text)!important;
    }
    html[data-theme="dark"] [data-testid="stChatInput"] textarea::placeholder {
        color: #888!important;
        opacity: 1!important;
    }
    html[data-theme="dark"] [data-testid="stChatInput"] textarea:focus {
        border-color: var(--primary)!important;
        box-shadow: 4px 4px 0px rgba(242, 55, 161, 0.3)!important;
    }
    html[data-theme="dark"] [data-testid="stChatInput"],
    html[data-theme="dark"] [data-testid="stChatInput"] * {
        background-color: var(--surface)!important;
        border-color: var(--border)!important;
    }
    html[data-theme="dark"] [data-testid="stChatInput"] button {
        color: var(--text)!important;
    }
    html[data-theme="dark"] [data-testid="stChatInput"] button svg {
        fill: var(--text)!important;
        stroke: var(--text)!important;
    }

    /* --- File Uploader --- */
    html[data-theme="dark"] [data-testid="stFileUploader"] section {
        border-color: var(--secondary)!important;
        background: var(--surface)!important;
    }
    html[data-theme="dark"] [data-testid="stFileUploader"] section * {
        color: var(--text)!important;
    }
    html[data-theme="dark"] [data-testid="stFileUploader"] section button {
        background: var(--surface)!important;
        border-color: var(--border)!important;
        color: var(--text)!important;
    }
    html[data-theme="dark"] [data-testid="stFileUploader"] section button:hover {
        background: var(--secondary)!important;
        color: #FFFFFF!important;
    }
    html[data-theme="dark"] [data-testid="stFileUploader"] label { color: var(--text)!important; }
    html[data-theme="dark"] [data-testid="stFileUploader"] small { color: var(--text)!important; }
    html[data-theme="dark"] [data-testid="stFileUploader"] span { color: var(--text)!important; }

    /* --- AI Thinking --- */
    html[data-theme="dark"] .ai-thinking { color: var(--primary); }

    /* --- Markdown & Text --- */
    html[data-theme="dark"] [data-testid="stMarkdownContainer"] p { color: var(--text); }
    html[data-theme="dark"] hr { border-color: var(--border)!important; }
    html[data-theme="dark"] [data-testid="stCaptionContainer"] { color: #999!important; }

    /* --- Streamlit Native Widgets Override --- */
    html[data-theme="dark"] [data-testid="stTextInput"] input,
    html[data-theme="dark"] [data-testid="stSelectbox"] > div,
    html[data-theme="dark"] [data-testid="stMultiSelect"] > div {
        background: var(--surface)!important;
        color: var(--text)!important;
        border-color: var(--border)!important;
    }
    html[data-theme="dark"] .stAlert {
        background: var(--surface)!important;
        border-color: var(--border)!important;
        color: var(--text)!important;
    }
    html[data-theme="dark"] [data-testid="stToast"] {
        background: var(--surface)!important;
        color: var(--text)!important;
        border-color: var(--border)!important;
    }

    /* --- Sidebar Toggle Icons in Dark Mode --- */
    html[data-theme="dark"] [data-testid="collapsedControl"] button::after,
    html[data-theme="dark"] [data-testid="stSidebarCollapsedControl"] button::after,
    html[data-theme="dark"] button[data-testid="collapsedControl"]::after,
    html[data-theme="dark"] button[data-testid="stSidebarCollapsedControl"]::after {
        color: var(--text) !important;
    }
    html[data-theme="dark"] [data-testid="stSidebarCollapseButton"] button::after,
    html[data-theme="dark"] button[data-testid="stSidebarCollapseButton"]::after {
        color: var(--text) !important;
    }

    /* --- Theme Toggle Button --- */
    .theme-toggle-row {
        display: flex;
        justify-content: flex-end;
        padding: 4px 0 8px;
    }
    .theme-toggle-btn {
        font-family: var(--font-sans);
        font-size: 13px;
        font-weight: 600;
        color: var(--text);
        background: var(--surface);
        border: 2px solid var(--border);
        border-radius: var(--radius-md);
        padding: 6px 14px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        box-shadow: 2px 2px 0px var(--border);
        transition: all 0.2s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .theme-toggle-btn:hover {
        transform: translate(-2px, -2px);
        box-shadow: 4px 4px 0px var(--primary);
    }
    .theme-toggle-icon {
        font-size: 16px;
        transition: transform 0.3s ease;
    }
    .theme-toggle-btn:hover .theme-toggle-icon {
        transform: rotate(20deg) scale(1.1);
    }

    /* --- Scrollbar Dark Mode --- */
    html[data-theme="dark"] ::-webkit-scrollbar { width: 8px; }
    html[data-theme="dark"] ::-webkit-scrollbar-track { background: var(--paper); }
    html[data-theme="dark"] ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
    html[data-theme="dark"] ::-webkit-scrollbar-thumb:hover { background: var(--primary); }

    /* --- Dataframe Dark Mode --- */
    html[data-theme="dark"] [data-testid="stDataFrame"],
    html[data-theme="dark"] [data-testid="stTable"] {
        background: var(--surface)!important;
        color: var(--text)!important;
    }

    /* --- Score Analysis Phase 5 --- */
    .sa-missing-panel {
        border: 2px solid var(--secondary);
        border-radius: var(--radius-md);
        padding: var(--sp-16);
        background: rgba(44, 64, 167, 0.06);
        color: var(--text);
        margin-bottom: var(--sp-12);
    }
    .sa-missing-panel p,
    .sa-missing-panel li {
        color: var(--text)!important;
    }
    html[data-theme="dark"] .sa-missing-panel {
        background: rgba(44, 64, 167, 0.22);
        border-color: var(--secondary);
    }
    .sa-combo-card {
        border: 2px solid var(--sa-combo-color);
        border-radius: var(--radius-md);
        padding: var(--sp-16);
        text-align: center;
        margin-bottom: var(--sp-8);
        background: transparent;
    }
    .sa-combo-card-success { --sa-combo-color: var(--success); }
    .sa-combo-card-warning { --sa-combo-color: var(--warning); }
    .sa-combo-card-danger { --sa-combo-color: var(--danger); }
    .sa-combo-card-code {
        font-size: 1.4em;
        font-weight: 700;
        color: var(--text);
    }
    .sa-combo-card-score {
        font-size: 1.8em;
        font-weight: 800;
        color: var(--sa-combo-color);
    }
    .sa-combo-card-subjects {
        font-size: 0.8em;
        color: var(--text);
        opacity: 0.72;
    }
    .sa-combo-card-alert {
        color: var(--sa-combo-color);
        font-size: 0.75em;
        font-weight: 700;
    }
    """
    # Embed Google Fonts via @import inside <style> (works reliably in body, unlike <link>)
    # Also add robust fallback stack for networks that block Google Fonts
    font_import = """
    @import url('https://fonts.googleapis.com/css2?family=Overpass+Mono:wght@400;600;700&family=Space+Grotesk:wght@300;400;500;600;700;800;900&display=swap');
    """
    st.markdown(f"<style>{font_import}\n{css}</style>", unsafe_allow_html=True)

