import streamlit as st
import database
import auth
import expenses
import dashboard
import ml_insights
import ai_insights        # ← add
import export             # ← add

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
        "🤖 ML Insights",
        "✨ AI Insights",       # ← add
        "📁 Export",            # ← add
        "⚙️ Settings"
    ])

    st.sidebar.divider()
    if st.sidebar.button("Logout", use_container_width=True):
        auth.logout_user()

    if page == "📊 Dashboard":
        dashboard.show_dashboard()

    elif page == "➕ Add Expense":
        expenses.show_add_expense_page()

    elif page == "📋 My Expenses":
        expenses.show_expenses_page()

    elif page == "🤖 ML Insights":
        ml_insights.show_ml_insights_page()

    elif page == "✨ AI Insights":
        ai_insights.show_ai_page()             # ← add

    elif page == "📁 Export":
        export.show_export_page()              # ← add

    elif page == "⚙️ Settings":
        auth.show_settings_page()