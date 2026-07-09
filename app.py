import streamlit as st
import database
import auth
import expenses
import dashboard
import ml_insights
import ai_insights
import export
import statement_import

from styles.global_css import inject_global_css


from styles.components import (
    page_banner, section_header, glass_card,
    risk_badge, stat_card, tip_card,
    ai_commentary, category_pill, empty_state
)

st.set_page_config(
    page_title="SpendWise",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_global_css()
    # ← add this line

database.init_db()
auth.init_session()

if not auth.is_logged_in():
    # ── Logged out sidebar — keep it populated so it never auto-collapses ──
    st.sidebar.markdown(
        """
        <div style="padding: 0.5rem 0 1rem;">
            <div style="
                font-family: 'Libre Baskerville', Georgia, serif;
                font-size: 1.5rem;
                font-weight: 700;
                background: linear-gradient(90deg, #FFFFFF, #F375C2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 0.4rem;
            ">SpendWise </div>
            <div style="
                font-family: Inter, sans-serif;
                font-size: 0.82rem;
                color: #9090B8;
                line-height: 1.7;
            ">Track smarter.<br>Spend better.</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.sidebar.divider()
    st.sidebar.caption("New here? Register to get started.")
    st.sidebar.markdown("<br>", unsafe_allow_html=True)

    page = st.sidebar.radio("", ["Login", "Register"])

    if page == "Login":
        auth.show_login_form()
    else:
        auth.show_register_form()

else:
    # ── Logged in sidebar ──────────────────────────────────────────────────
    st.sidebar.markdown(
        f"""
        <div style="padding: 0.5rem 0 0.75rem;">
            <div style="
                font-family: 'Libre Baskerville', Georgia, serif;
                font-size: 1.4rem;
                font-weight: 700;
                background: linear-gradient(90deg, #FFFFFF, #F375C2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 4px;
            ">SpendWise</div>
            <div style="
                font-family: Inter, sans-serif;
                font-size: 0.78rem;
                color: #9090B8;
            ">Logged in as <span style="
                color: #F375C2;
                font-weight: 600;
            ">{st.session_state['username']}</span></div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.sidebar.divider()

    page = st.sidebar.radio("Navigate", [
        "Dashboard",
        "Add Expense",
        "My Expenses",
        "Import Statement", 
        "ML Insights",
        "AI Insights",
        "Export",
        "Settings"
    ])

    st.sidebar.divider()
    if st.sidebar.button("Logout", use_container_width=True):
        auth.logout_user()

    if page == "Dashboard":
        dashboard.show_dashboard()

    elif page == "Add Expense":
        expenses.show_add_expense_page()

    elif page == "My Expenses":
        expenses.show_expenses_page()

    elif page == "Import Statement":
        statement_import.show_import_page()

    elif page == "ML Insights":
        ml_insights.show_ml_insights_page()

    elif page == "AI Insights":
        ai_insights.show_ai_page()

    elif page == "Export":
        export.show_export_page()

    elif page == "Settings":
        auth.show_settings_page()