import bcrypt
import streamlit as st
import plotly.express as px
import pandas as pd
import datetime
import database

CATEGORIES = ["Food", "Travel", "Shopping", "Entertainment", "Health", "Utilities", "Other"]

COLOUR_MAP = {
    "Food":          "#FF6B6B",
    "Travel":        "#4ECDC4",
    "Shopping":      "#45B7D1",
    "Entertainment": "#96CEB4",
    "Health":        "#FFEAA7",
    "Utilities":     "#DDA0DD",
    "Other":         "#B0B0B0",
}


# ── Password utilities ────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    password_bytes = plain_password.encode("utf-8")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


# ── Session utilities ─────────────────────────────────────────────────────────

def init_session():
    defaults = {
        "logged_in": False,
        "user_id":   None,
        "username":  None,
        "email":     None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def login_user(user_row) -> None:
    st.session_state["logged_in"] = True
    st.session_state["user_id"]   = user_row["id"]
    st.session_state["username"]  = user_row["username"]
    st.session_state["email"]     = user_row["email"]


def logout_user() -> None:
    for key in ["logged_in", "user_id", "username", "email"]:
        st.session_state[key] = None
    st.session_state["logged_in"] = False
    st.rerun()


def is_logged_in() -> bool:
    return st.session_state.get("logged_in", False)


# ── Registration ──────────────────────────────────────────────────────────────

def show_register_form() -> None:
    st.title("Create your SpendWise account")

    with st.form("register_form"):
        username = st.text_input("Username")
        email    = st.text_input("Email address")
        password = st.text_input("Password", type="password",
                                 help="Minimum 8 characters")
        confirm  = st.text_input("Confirm password", type="password")
        submit   = st.form_submit_button("Register")

    if submit:
        if not username or not email or not password:
            st.error("All fields are required.")
            return
        if len(password) < 8:
            st.error("Password must be at least 8 characters.")
            return
        if password != confirm:
            st.error("Passwords do not match.")
            return
        if "@" not in email or "." not in email:
            st.error("Please enter a valid email address.")
            return

        hashed  = hash_password(password)
        success = database.create_user(username, email, hashed)

        if success:
            st.success("Account created! Please log in.")
        else:
            st.error("That username or email is already registered.")


# ── Login ─────────────────────────────────────────────────────────────────────

def show_login_form() -> None:
    st.title("Welcome back to SpendWise 👋")

    with st.form("login_form"):
        email    = st.text_input("Email address")
        password = st.text_input("Password", type="password")
        submit   = st.form_submit_button("Log in")

    if submit:
        if not email or not password:
            st.error("Please enter your email and password.")
            return

        user = database.get_user_by_email(email)

        if user is None:
            st.error("Invalid email or password.")
            return

        if not verify_password(password, user["password"]):
            st.error("Invalid email or password.")
            return

        login_user(user)
        st.rerun()


# ── Settings page ─────────────────────────────────────────────────────────────

def show_settings_page() -> None:
    st.header("⚙️ Settings")

    user_id = st.session_state["user_id"]
    today   = datetime.datetime.now()

    # ── Month scope selector ──────────────────────────────────────
    st.subheader("Budget scope")
    st.caption(
        "Choose whether to update budgets for this month only, "
        "or apply the same limits to all months going forward."
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        scope = st.radio(
            "Apply budget to",
            ["This month only", "All months (past + future)"],
            help=(
                "This month only — updates just the current month's budget. "
                "All months — sets the same budget across every month in your history "
                "and going forward."
            )
        )

    # ── Load existing budgets ─────────────────────────────────────
    existing = database.get_budgets(user_id, today.month, today.year)

    # ── Budget pie chart ──────────────────────────────────────────
    st.subheader("Current budget allocation")

    from expenses import get_all_categories
    all_categories_for_user = get_all_categories(user_id)
    budget_values = {
        cat: existing.get(cat, 0.0) for cat in all_categories_for_user
    }
    total_budget = sum(budget_values.values())

    if total_budget > 0:
        pie_df = pd.DataFrame([
            {"Category": cat, "Budget": val}
            for cat, val in budget_values.items()
            if val > 0
        ])

        col_chart, col_summary = st.columns([1.2, 1])

        with col_chart:
            fig = px.pie(
                pie_df,
                values="Budget",
                names="Category",
                hole=0.4,
                color="Category",
                color_discrete_map=COLOUR_MAP,
            )
            fig.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate="<b>%{label}</b><br>Rs%{value:,.0f}<br>%{percent}"
            )
            fig.update_layout(
                showlegend=False,
                margin=dict(t=10, b=10, l=0, r=0),
                height=280,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_summary:
            st.markdown("**Budget breakdown**")
            for cat in CATEGORIES:
                val = budget_values.get(cat, 0.0)
                if val > 0:
                    pct = val / total_budget * 100
                    colour = COLOUR_MAP.get(cat, "#888")
                    st.markdown(
                        f"<div style='display:flex; justify-content:space-between; "
                        f"padding: 4px 0; border-bottom: 1px solid #2D2D3F;'>"
                        f"<span style='color:{colour}; font-weight:500;'>{cat}</span>"
                        f"<span>Rs{val:,.0f} &nbsp;<span style='color:#888;'>"
                        f"({pct:.0f}%)</span></span></div>",
                        unsafe_allow_html=True
                    )
            st.markdown(
                f"<div style='padding: 8px 0; font-weight:600;'>"
                f"Total &nbsp; Rs{total_budget:,.0f}</div>",
                unsafe_allow_html=True
            )
    else:
        st.info("No budgets set yet — enter your limits below to see the allocation chart.")

    st.divider()

    # ── Budget input form ─────────────────────────────────────────
    st.subheader("Set monthly budgets")
    st.caption(
        f"Currently editing: **{today.strftime('%B %Y')}**"
        if scope == "This month only"
        else "Setting budgets for **all months**"
    )

    with st.form("budget_form"):
        budgets = {}

        # Two columns for the inputs
        col1, col2 = st.columns(2)
        from expenses import get_all_categories
        all_categories = get_all_categories(user_id)

        for i, category in enumerate(all_categories):
            current_limit = existing.get(category, 0.0)
            with col1 if i % 2 == 0 else col2:
                budgets[category] = st.number_input(
                    f"{category} (Rs)",
                    min_value=0.0,
                    value=float(current_limit),
                    step=100.0,
                    key=f"budget_{category}"
                )

        save = st.form_submit_button("💾 Save budgets", use_container_width=True,
                                     type="primary")

    if save:
        if scope == "This month only":
            # Save only for current month
            for category, limit in budgets.items():
                database.set_budget(
                    user_id, category, limit,
                    today.month, today.year
                )
            st.success(
                f"Budgets saved for {today.strftime('%B %Y')} only."
            )

        else:
            # Apply to all months that exist in the database
            # plus the next 12 months going forward
            months_to_update = set()

            # Past months — find all months with existing expense data
            from expenses import load_expenses
            all_df = load_expenses(user_id)

            if not all_df.empty:
                import pandas as pd_inner
                all_df["date"] = pd_inner.to_datetime(all_df["date"])
                for _, row in all_df.iterrows():
                    months_to_update.add(
                        (row["date"].month, row["date"].year)
                    )

            # Current month
            months_to_update.add((today.month, today.year))

            # Next 12 months
            for offset in range(1, 13):
                m = today.month + offset
                y = today.year
                if m > 12:
                    m -= 12
                    y += 1
                months_to_update.add((m, y))

            for month, year in months_to_update:
                for category, limit in budgets.items():
                    database.set_budget(user_id, category, limit, month, year)

            st.success(
                f"Budgets applied across {len(months_to_update)} months "
                f"(all history + next 12 months)."
            )

        # Rerun so pie chart updates immediately
        st.rerun()

    # ── Change password ───────────────────────────────────────────
    st.divider()
    st.subheader("Change password")

    with st.form("password_form"):
        current_pw  = st.text_input("Current password", type="password")
        new_pw      = st.text_input("New password", type="password",
                                    help="Minimum 8 characters")
        confirm_pw  = st.text_input("Confirm new password", type="password")
        change_btn  = st.form_submit_button("Update password")

    if change_btn:
        if not current_pw or not new_pw or not confirm_pw:
            st.error("All fields are required.")
        elif len(new_pw) < 8:
            st.error("New password must be at least 8 characters.")
        elif new_pw != confirm_pw:
            st.error("New passwords do not match.")
        else:
            user = database.get_user_by_id(user_id)
            if not verify_password(current_pw, user["password"]):
                st.error("Current password is incorrect.")
            else:
                new_hash = hash_password(new_pw)
                conn = database.get_connection()
                conn.execute(
                    "UPDATE users SET password = ? WHERE id = ?",
                    (new_hash, user_id)
                )
                conn.commit()
                conn.close()
                st.success("Password updated successfully.")