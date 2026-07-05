import streamlit as st
import base64
import os


def _get_base64_bg(image_path: str) -> str:
    """
    Convert background image to base64 so it can be
    embedded directly in CSS without a file server.
    This is required because Streamlit's static file
    serving doesn't expose arbitrary local paths to CSS.
    """
    with open(image_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


def inject_global_css() -> None:
    """
    Inject all global CSS into the Streamlit app.
    Call once at the top of app.py after set_page_config().

    Structure:
    1. Google Fonts import
    2. CSS variables (design tokens)
    3. Background image
    4. Main layout
    5. Sidebar
    6. Typography
    7. Metric cards
    8. Buttons
    9. Inputs and selects
    10. Dataframes
    11. Expanders
    12. Dividers
    13. Scrollbar
    14. Plotly chart containers
    15. Animations
    """

    # ── Load background image ──────────────────────────────────────
    bg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "media", "bg.jpg")
    try:
        bg_b64 = _get_base64_bg(bg_path)
        bg_css = f"url('data:image/jpeg;base64,{bg_b64}')"
    except FileNotFoundError:
        # Fallback gradient if image not found
        bg_css = "linear-gradient(135deg, #0E21A0 0%, #4D2FB2 50%, #B153D7 100%)"

    css = f"""
    <style>

    /* ── 1. Google Fonts ─────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Inter:wght@300;400;500;600&display=swap');

    /* ── 2. CSS variables — single source of truth ───────────── */
    :root {{
        --navy:        #0E21A0;
        --purple:      #4D2FB2;
        --violet:      #B153D7;
        --pink:        #F375C2;
        --white:       #FFFFFF;
        --text-primary:   #F0F0FF;
        --text-secondary: #C8C8E8;
        --text-muted:     #9090B8;

        --glass-bg:      rgba(14, 33, 160, 0.25);
        --glass-bg-dark: rgba(10, 15, 80, 0.45);
        --glass-border:  rgba(177, 83, 215, 0.35);
        --glass-blur:    12px;

        --radius-sm:  8px;
        --radius-md:  14px;
        --radius-lg:  20px;
        --radius-xl:  28px;

        --shadow-glow: 0 0 24px rgba(177, 83, 215, 0.18);
        --shadow-card: 0 8px 32px rgba(10, 10, 60, 0.35);

        --transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }}

    /* ── 3. Background image — fixed, covers all pages ──────── */
    html, body, [data-testid="stAppViewContainer"] {{
        background-image: {bg_css} !important;
        background-size: cover !important;
        background-position: center center !important;
        background-attachment: fixed !important;
        background-repeat: no-repeat !important;
        min-height: 100vh;
    }}

    /* Dark overlay on top of background for readability */
    [data-testid="stAppViewContainer"]::before {{
        content: '';
        position: fixed;
        inset: 0;
        background: linear-gradient(
            160deg,
            rgba(14, 33, 160, 0.55) 0%,
            rgba(77, 47, 178, 0.45) 50%,
            rgba(10, 10, 50, 0.60) 100%
        );
        pointer-events: none;
        z-index: 0;
    }}

    /* Main content sits above overlay */
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

    /* Sidebar title */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] .stTitle {{
        font-family: 'Libre Baskerville', Georgia, serif !important;
        font-size: 1.4rem !important;
        background: linear-gradient(90deg, var(--white), var(--pink));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}

    /* Sidebar nav items */
    [data-testid="stSidebar"] [data-testid="stRadio"] label {{
        font-family: 'Inter', sans-serif !important;
        font-size: 0.9rem !important;
        font-weight: 400;
        padding: 6px 0;
        transition: var(--transition);
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
        color: var(--pink) !important;
    }}

    /* Sidebar divider */
    [data-testid="stSidebar"] hr {{
        border-color: var(--glass-border) !important;
        opacity: 0.5;
    }}

    /* ── 6. Typography ────────────────────────────────────────── */
    html, body, .stApp {{
        font-family: 'Inter', sans-serif !important;
        color: var(--text-primary) !important;
    }}

    /* Page headers */
    h1, .stHeading h1 {{
        font-family: 'Libre Baskerville', Georgia, serif !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: var(--white) !important;
        letter-spacing: -0.02em;
        margin-bottom: 0.25rem;
    }}

    /* Section subheaders */
    h2, h3, .stHeading h2, .stHeading h3 {{
        font-family: 'Libre Baskerville', Georgia, serif !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.01em;
    }}

    /* Body text */
    p, li, span, label {{
        font-family: 'Inter', sans-serif !important;
        color: var(--text-secondary) !important;
        line-height: 1.65;
    }}

    /* Caption text */
    [data-testid="stCaptionContainer"] p,
    .stCaption {{
        color: var(--text-muted) !important;
        font-size: 0.82rem !important;
    }}

    /* ── 7. Metric cards ──────────────────────────────────────── */
    [data-testid="stMetric"] {{
        background: var(--glass-bg) !important;
        backdrop-filter: blur(var(--glass-blur)) !important;
        -webkit-backdrop-filter: blur(var(--glass-blur)) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-md) !important;
        padding: 1rem 1.25rem !important;
        box-shadow: var(--shadow-card) !important;
        transition: var(--transition) !important;
    }}

    [data-testid="stMetric"]:hover {{
        border-color: var(--violet) !important;
        box-shadow: var(--shadow-glow), var(--shadow-card) !important;
        transform: translateY(-2px);
    }}

    /* Metric value — big number */
    [data-testid="stMetricValue"] {{
        font-family: 'Libre Baskerville', Georgia, serif !important;
        font-size: 1.7rem !important;
        font-weight: 700 !important;
        color: var(--white) !important;
    }}

    /* Metric label */
    [data-testid="stMetricLabel"] {{
        font-family: 'Inter', sans-serif !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        color: var(--text-muted) !important;
    }}

    /* Metric delta */
    [data-testid="stMetricDelta"] {{
        font-family: 'Inter', sans-serif !important;
        font-size: 0.8rem !important;
    }}

    /* ── 8. Buttons ───────────────────────────────────────────── */
    .stButton > button {{
        background: linear-gradient(
            135deg, var(--purple) 0%, var(--violet) 100%
        ) !important;
        color: var(--white) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-sm) !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
        padding: 0.5rem 1.25rem !important;
        transition: var(--transition) !important;
        box-shadow: 0 4px 15px rgba(177, 83, 215, 0.25) !important;
        letter-spacing: 0.02em;
    }}

    .stButton > button:hover {{
        background: linear-gradient(
            135deg, var(--violet) 0%, var(--pink) 100%
        ) !important;
        box-shadow: 0 6px 20px rgba(243, 117, 194, 0.4) !important;
        transform: translateY(-1px);
        border-color: var(--pink) !important;
    }}

    .stButton > button:active {{
        transform: translateY(0px);
        box-shadow: 0 2px 8px rgba(177, 83, 215, 0.3) !important;
    }}

    /* Primary button variant */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(
            135deg, var(--violet) 0%, var(--pink) 100%
        ) !important;
        box-shadow: 0 4px 20px rgba(243, 117, 194, 0.35) !important;
    }}

    /* Download button */
    .stDownloadButton > button {{
        background: linear-gradient(
            135deg, var(--navy) 0%, var(--purple) 100%
        ) !important;
        color: var(--white) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-sm) !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        transition: var(--transition) !important;
    }}

    .stDownloadButton > button:hover {{
        border-color: var(--violet) !important;
        box-shadow: var(--shadow-glow) !important;
        transform: translateY(-1px);
    }}

    /* ── 9. Inputs, selects, textareas ───────────────────────── */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {{
        background: var(--glass-bg-dark) !important;
        backdrop-filter: blur(var(--glass-blur)) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--white) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.9rem !important;
        transition: var(--transition) !important;
    }}

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: var(--violet) !important;
        box-shadow: 0 0 0 2px rgba(177, 83, 215, 0.25) !important;
        outline: none !important;
    }}

    /* Selectbox */
    .stSelectbox > div > div {{
        background: var(--glass-bg-dark) !important;
        backdrop-filter: blur(var(--glass-blur)) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--white) !important;
        font-family: 'Inter', sans-serif !important;
        transition: var(--transition) !important;
    }}

    .stSelectbox > div > div:hover {{
        border-color: var(--violet) !important;
    }}

    /* Multiselect */
    .stMultiSelect > div > div {{
        background: var(--glass-bg-dark) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-sm) !important;
    }}

    /* Multiselect tags */
    .stMultiSelect span[data-baseweb="tag"] {{
        background: linear-gradient(
            135deg, var(--purple), var(--violet)
        ) !important;
        border-radius: 20px !important;
        border: none !important;
    }}

    /* Date input */
    .stDateInput > div > div > input {{
        background: var(--glass-bg-dark) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--white) !important;
        font-family: 'Inter', sans-serif !important;
    }}

    /* Number input +/- buttons */
    .stNumberInput button {{
        background: var(--glass-bg) !important;
        border-color: var(--glass-border) !important;
        color: var(--white) !important;
    }}

    .stNumberInput button:hover {{
        background: var(--purple) !important;
    }}

    /* Input labels */
    .stTextInput label,
    .stNumberInput label,
    .stSelectbox label,
    .stMultiSelect label,
    .stDateInput label,
    .stTextArea label,
    .stCheckbox label,
    .stRadio label {{
        font-family: 'Inter', sans-serif !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        letter-spacing: 0.02em;
    }}

    /* ── 10. Dataframes / tables ──────────────────────────────── */
    [data-testid="stDataFrame"] {{
        background: var(--glass-bg) !important;
        backdrop-filter: blur(var(--glass-blur)) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-md) !important;
        overflow: hidden;
    }}

    [data-testid="stDataFrame"] th {{
        background: rgba(77, 47, 178, 0.5) !important;
        color: var(--white) !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        border-bottom: 1px solid var(--glass-border) !important;
    }}

    [data-testid="stDataFrame"] td {{
        color: var(--text-secondary) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.88rem !important;
        border-bottom: 1px solid rgba(177, 83, 215, 0.1) !important;
    }}

    [data-testid="stDataFrame"] tr:hover td {{
        background: rgba(177, 83, 215, 0.08) !important;
        color: var(--white) !important;
    }}

    /* ── 11. Expanders ────────────────────────────────────────── */
    [data-testid="stExpander"] {{
        background: var(--glass-bg) !important;
        backdrop-filter: blur(var(--glass-blur)) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-md) !important;
        margin-bottom: 0.75rem !important;
        box-shadow: var(--shadow-card) !important;
        transition: var(--transition) !important;
        overflow: hidden;
    }}

    [data-testid="stExpander"]:hover {{
        border-color: var(--violet) !important;
        box-shadow: var(--shadow-glow), var(--shadow-card) !important;
    }}

    [data-testid="stExpander"] summary {{
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        color: var(--white) !important;
        padding: 1rem 1.25rem !important;
    }}

    [data-testid="stExpander"] summary:hover {{
        color: var(--pink) !important;
    }}

    /* Expander content */
    [data-testid="stExpander"] > div > div {{
        padding: 0 1.25rem 1rem !important;
    }}

    /* ── 12. Alert boxes (info, warning, error, success) ──────── */
    [data-testid="stAlert"] {{
        backdrop-filter: blur(var(--glass-blur)) !important;
        border-radius: var(--radius-md) !important;
        border-width: 1px !important;
        font-family: 'Inter', sans-serif !important;
    }}

    /* Info */
    [data-testid="stAlert"][data-type="info"] {{
        background: rgba(77, 47, 178, 0.25) !important;
        border-color: rgba(177, 83, 215, 0.5) !important;
        color: var(--text-primary) !important;
    }}

    /* Success */
    [data-testid="stAlert"][data-type="success"] {{
        background: rgba(29, 158, 117, 0.2) !important;
        border-color: rgba(29, 158, 117, 0.5) !important;
    }}

    /* Warning */
    [data-testid="stAlert"][data-type="warning"] {{
        background: rgba(245, 158, 11, 0.2) !important;
        border-color: rgba(245, 158, 11, 0.5) !important;
    }}

    /* Error */
    [data-testid="stAlert"][data-type="error"] {{
        background: rgba(239, 68, 68, 0.2) !important;
        border-color: rgba(239, 68, 68, 0.5) !important;
    }}

    /* ── 13. Progress bar ─────────────────────────────────────── */
    [data-testid="stProgress"] > div > div > div > div {{
        background: linear-gradient(
            90deg, var(--purple), var(--violet), var(--pink)
        ) !important;
        border-radius: 4px !important;
    }}

    [data-testid="stProgress"] > div > div > div {{
        background: rgba(14, 33, 160, 0.4) !important;
        border-radius: 4px !important;
        border: 1px solid var(--glass-border) !important;
    }}

    /* ── 14. Dividers ─────────────────────────────────────────── */
    hr {{
        border: none !important;
        height: 1px !important;
        background: linear-gradient(
            90deg,
            transparent,
            var(--glass-border),
            var(--violet),
            var(--glass-border),
            transparent
        ) !important;
        margin: 1.5rem 0 !important;
        opacity: 0.7;
    }}

    /* ── 15. Tabs ─────────────────────────────────────────────── */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {{
        background: var(--glass-bg-dark) !important;
        backdrop-filter: blur(var(--glass-blur)) !important;
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--glass-border) !important;
        padding: 4px !important;
        gap: 4px !important;
    }}

    [data-testid="stTabs"] [data-baseweb="tab"] {{
        background: transparent !important;
        color: var(--text-muted) !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        border-radius: var(--radius-sm) !important;
        transition: var(--transition) !important;
        border: none !important;
    }}

    [data-testid="stTabs"] [aria-selected="true"] {{
        background: linear-gradient(
            135deg, var(--purple), var(--violet)
        ) !important;
        color: var(--white) !important;
        box-shadow: 0 2px 10px rgba(177, 83, 215, 0.4) !important;
    }}

    [data-testid="stTabs"] [data-baseweb="tab"]:hover {{
        color: var(--white) !important;
        background: rgba(177, 83, 215, 0.15) !important;
    }}

    /* ── 16. Slider ───────────────────────────────────────────── */
    [data-testid="stSlider"] > div > div > div > div {{
        background: linear-gradient(
            90deg, var(--purple), var(--violet)
        ) !important;
    }}

    [data-testid="stSlider"] > div > div > div > div > div {{
        background: var(--pink) !important;
        border: 2px solid var(--white) !important;
        box-shadow: 0 0 10px rgba(243, 117, 194, 0.5) !important;
    }}

    /* ── 17. Checkbox and radio ───────────────────────────────── */
    [data-testid="stCheckbox"] input:checked + div,
    [data-testid="stRadio"] input:checked + div {{
        background: var(--violet) !important;
        border-color: var(--violet) !important;
    }}

    /* ── 18. Forms ────────────────────────────────────────────── */
    [data-testid="stForm"] {{
        background: var(--glass-bg) !important;
        backdrop-filter: blur(var(--glass-blur)) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-lg) !important;
        padding: 1.5rem !important;
        box-shadow: var(--shadow-card) !important;
    }}

    /* ── 19. Scrollbar ────────────────────────────────────────── */
    ::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}

    ::-webkit-scrollbar-track {{
        background: rgba(14, 33, 160, 0.2);
    }}

    ::-webkit-scrollbar-thumb {{
        background: linear-gradient(var(--purple), var(--violet));
        border-radius: 3px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: var(--pink);
    }}

    /* ── 20. Plotly chart containers ──────────────────────────── */
    [data-testid="stPlotlyChart"] {{
        background: var(--glass-bg) !important;
        backdrop-filter: blur(var(--glass-blur)) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-md) !important;
        padding: 0.75rem !important;
        box-shadow: var(--shadow-card) !important;
    }}

    /* ── 21. Spinner ──────────────────────────────────────────── */
    [data-testid="stSpinner"] {{
        color: var(--violet) !important;
    }}

    /* ── 22. Toast notifications ──────────────────────────────── */
    [data-testid="stToast"] {{
        background: var(--glass-bg-dark) !important;
        backdrop-filter: blur(var(--glass-blur)) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-md) !important;
        color: var(--white) !important;
        font-family: 'Inter', sans-serif !important;
        box-shadow: var(--shadow-glow), var(--shadow-card) !important;
    }}

    /* ── 23. Hide Streamlit branding ──────────────────────────── */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* ── 24. Page fade-in animation ───────────────────────────── */
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

    .main .block-container {{
        animation: fadeInUp 0.45s ease-out forwards;
    }}

    /* ── 25. Shimmer animation for loading states ─────────────── */
    @keyframes shimmer {{
        0%   {{ background-position: -1000px 0; }}
        100% {{ background-position: 1000px 0; }}
    }}

    .shimmer {{
        background: linear-gradient(
            90deg,
            rgba(77, 47, 178, 0.1) 25%,
            rgba(177, 83, 215, 0.2) 50%,
            rgba(77, 47, 178, 0.1) 75%
        );
        background-size: 1000px 100%;
        animation: shimmer 2s infinite linear;
        border-radius: var(--radius-sm);
    }}

    /* ── 26. Glow pulse for active elements ───────────────────── */
    @keyframes glowPulse {{
        0%, 100% {{ box-shadow: 0 0 8px rgba(177, 83, 215, 0.3); }}
        50%       {{ box-shadow: 0 0 24px rgba(243, 117, 194, 0.6); }}
    }}

    /* ── Fix 1: Hide sidebar collapse button text ─────────────── */
    [data-testid="stSidebarCollapseButton"] {{
        visibility: hidden !important;
    }}

    [data-testid="stSidebarCollapseButton"] svg {{
        visibility: visible !important;
    }}

    /* Hide the keyboard_double_arrow text specifically */
    [data-testid="stSidebarCollapseButton"] span {{
        display: none !important;
    }}

    /* ── Fix 2: Style radio nav as clean text links ────────────── */

    /* Hide the actual radio circle buttons */
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {{
        gap: 4px !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {{
        display: none !important;
    }}

    /* Nav item base style */
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

    /* Nav item hover */
    [data-testid="stSidebar"]

    </style>
    """

    st.markdown(css, unsafe_allow_html=True)