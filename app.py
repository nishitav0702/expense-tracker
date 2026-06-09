import streamlit as st
import database
import auth
import expenses  # add this import

st.set_page_config(
    page_title="SpendWise",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

database.init_db()
auth.init_session()

if not auth.is_logged_in():
    st.sidebar.title("SpendWise 💸")
    page = st.sidebar.radio("", ["Login", "Register"])

    if page == "Login":
        auth.show_login_form()
    else:
        auth.show_register_form()

else:
    st.sidebar.title("SpendWise 💸")
    st.sidebar.caption(f"Logged in as **{st.session_state['username']}**")
    st.sidebar.divider()

    page = st.sidebar.radio("Navigate", [
        "📊 Dashboard",
        "➕ Add Expense",
        "📋 My Expenses",
        "⚙️ Settings"
    ])

    st.sidebar.divider()
    if st.sidebar.button("Logout", use_container_width=True):
        auth.logout_user()

    # ── Page rendering ────────────────────────────────────────────
    if page == "📊 Dashboard":
        st.header("📊 Dashboard")
        st.info("Coming in Phase 4 — charts and analytics will live here.")

    elif page == "➕ Add Expense":
        expenses.show_add_expense_page()       # ← replaced

    elif page == "📋 My Expenses":
        expenses.show_expenses_page()          # ← replaced

    elif page == "⚙️ Settings":
        auth.show_settings_page()
