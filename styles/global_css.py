import streamlit as st
import base64
import os

# FIX 1: Native control to force the sidebar open. 
# This MUST be the absolute first Streamlit command in your script.
st.set_page_config(initial_sidebar_state="expanded")


def _get_base64_bg(image_path: str) -> str:
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return ""


def inject_global_css() -> None:
    bg_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "media", "bg.jpg"
    )
    bg_b64 = _get_base64_bg(bg_path)
    if bg_b64:
        bg_css = f"url('data:image/jpeg;base64,{bg_b64}')"
    else:
        bg_css = "linear-gradient(135deg, #0E21A0 0%, #4D2FB2 50%, #B153D7 100%)"

    css = f"""
    <style>
    /* ── 1. Google Fonts ─────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Inter:wght@300;400;500;600&display=swap');

    /* ── 2. CSS variables ────────────────────────────────────── */
    :root {{
        --navy:         #0E21A0;
        --purple:       #4D2FB2;
        --violet:       #B153D7;
        --pink:         #F375C2;
        --white:        #FFFFFF;
        --text-primary:   #F0F0FF;
        --text-secondary: #C8C8E8;
        --text-muted:     #9090B8;

        --glass-bg:      rgba(14, 33, 160, 0.25);
        --glass-bg-dark: rgba(10, 15, 80, 0.45);
        --glass-border:  rgba(177, 83, 215, 0.35);
        --glass-blur:    12px;

        --radius-sm: 8px;
        --radius-md: 14px;
        --radius-lg: 20px;
        --radius-xl: 28px;

        --shadow-glow: 0 0 24px rgba(177, 83, 215, 0.18);
        --shadow-card: 0 8px 32px rgba(10, 10, 60, 0.35);
        --transition:  all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }}

    /* ── 3. Background image ─────────────────────────────────── */
    html, body, [data-testid="stAppViewContainer"] {{
        background-image: {bg_css} !important;
        background-size: cover !important;
        background-position: center center !important;
        background-attachment: fixed !important;
        background-repeat: no-repeat !important;
        min-height: 100vh;
    }}

    [data-testid="stAppViewContainer"]::before {{
        content: '';
        position: fixed;
        inset: 0;
        background: linear-gradient(
            160deg,
            rgba(14, 33, 160, 0.55) 0%,
            rgba(77, 47, 178, 0.45) 50%,
            rgba(10, 10, 60, 0.60) 100%
        );
        pointer-events: none;
        z-index: 0;
    }}

    [data-testid="stAppViewContainer"] > * {{
        position: relative;
        z-index: 1;
    }}

    /* ── 4. Main content area ─────────────────────────────────── */
    [data-testid="stMain"] {{
        background: transparent !important;
    }}

    .main .block-container {{
        background: transparent !important;
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
        animation: fadeInUp 0.45s ease-out forwards;
    }}

    /* ── 5. Sidebar ───────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background: linear-gradient(
            180deg,
            rgba(14, 33, 160, 0.65) 0%,
            rgba(77, 47, 178, 0.55) 60%,
            rgba(10, 10, 60, 0.70) 100%
        ) !important;
        backdrop-filter: blur(var(--glass-blur)) !important;
        -webkit-backdrop-filter: blur(var(--glass-blur)) !important;
        border-right: 1px solid var(--glass-border) !important;
        box-shadow: 4px 0 24px rgba(10, 10, 60, 0.4);
    }}

    [data-testid="stSidebar"] * {{
        color: var(--text-primary) !important;
    }}

    [data-testid="stSidebar"] hr {{
        border-color: var(--glass-border) !important;
        opacity: 0.5;
    }}

    /* ── 6. Sidebar collapse button ───────────────────────────── */
    [data-testid="stSidebarCollapseButton"] {{
        background: transparent !important;
        border: none !important;
        opacity: 0.65 !important;
        transition: var(--transition) !important;
        position: relative !important;
        
        /* Give the button container clear, explicit clickable dimensions */
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 2.2rem !important;
        height: 2.2rem !important;
        cursor: pointer !important;
        
        /* Safely turns off the fallback text without breaking the element */
        color: transparent !important; 
    }}

    /* Target ONLY the native SVG graphic so the button element stays fully active */
    [data-testid="stSidebarCollapseButton"] svg {{
        display: none !important;
    }}

    [data-testid="stSidebarCollapseButton"]:hover {{
        opacity: 1 !important;
    }}

    /* Absolute position our custom arrows perfectly over the clickable button frame */
    [data-testid="stSidebarCollapseButton"]::before {{
        position: absolute !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 1.3rem !important;
        color: var(--text-primary) !important; /* Overrides the parent transparency */
        line-height: 1 !important;
        pointer-events: none !important; /* Clicks pass straight through to the button */
    }}

    /* When sidebar is OPEN -> display "«" */
    [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"]::before {{
        content: "«" !important;
    }}

    /* When sidebar is CLOSED -> display "»" */
    [data-testid="stHeader"] [data-testid="stSidebarCollapseButton"]::before,
    [data-testid="stMain"] [data-testid="stSidebarCollapseButton"]::before {{
        content: "»" !important;
    }}
    /* ── 7. Sidebar nav — hide radio circles, style as pills ──── */
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {{
        gap: 4px !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {{
        display: none !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label {{
        display: block !important;
        width: 100% !important;
        padding: 10px 16px !important;
        border-radius: 30px !important;
        border: 1px solid transparent !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        cursor: pointer !important;
        transition: var(--transition) !important;
        background: transparent !important;
        margin-bottom: 2px !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
        color: var(--white) !important;
        background: rgba(177, 83, 215, 0.15) !important;
        border-color: rgba(177, 83, 215, 0.3) !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
        color: var(--white) !important;
        background: linear-gradient(
            135deg,
            rgba(77, 47, 178, 0.45) 0%,
            rgba(177, 83, 215, 0.35) 100%
        ) !important;
        border-color: transparent !important;
        box-shadow:
            0 0 0 1.5px #B153D7,
            0 4px 15px rgba(177, 83, 215, 0.3) !important;
        font-weight: 600 !important;
    }}

    /* ── 8. Typography ────────────────────────────────────────── */
    html, body, .stApp {{
        font-family: 'Inter', sans-serif !important;
        color: var(--text-primary) !important;
    }}

    h1, .stHeading h1 {{
        font-family: 'Libre Baskerville', Georgia, serif !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: var(--white) !important;
        letter-spacing: -0.02em;
        margin-bottom: 0.25rem;
    }}

    h2, h3, .stHeading h2, .stHeading h3 {{
        font-family: 'Libre Baskerville', Georgia, serif !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.01em;
    }}

    /* REMOVED 'span' from this blanket selector below to stop it from breaking other UI icons */
    p, li, label {{
        font-family: 'Inter', sans-serif !important;
        color: var(--text-secondary) !important;
        line-height: 1.65;
    }}

    /* ── 24. Hide Streamlit branding safely ───────────────────── */
    #MainMenu {{visibility: hidden;}}
    footer    {{visibility: hidden;}}
    
    /* FIX 3: Instead of hiding the complete top header bar element (which contains the open button),
       we leave the layout intact and just strip out its background and individual default components */
    [data-testid="stHeader"] {{
        background: transparent !important;
    }}
    [data-testid="stAppDeployButton"] {{
        display: none !important;
    }}

    /* ── 25. Animations ───────────────────────────────────────── */
    @keyframes fadeInUp {{
        from {{
            opacity: 0;
            transform: translateY(16px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# You can now completely remove the force_sidebar_open() JS function entirely.