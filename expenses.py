import streamlit as st
import pandas as pd
import datetime
import database
from auth import CATEGORIES
from api_client import CURRENCIES, convert_to_inr
from streamlit.components.v1 import html

# ── Category colours ──────────────────────────────────────────────────────────

CATEGORY_COLOURS = {
    "Food":          "#FF6B6B",
    "Travel":        "#4ECDC4",
    "Shopping":      "#45B7D1",
    "Entertainment": "#96CEB4",
    "Health":        "#FFEAA7",
    "Utilities":     "#DDA0DD",
    "Other":         "#B0B0B0",
}


def get_category_colour(category: str) -> str:
    """Return colour for a category, generating one for custom categories."""
    if category in CATEGORY_COLOURS:
        return CATEGORY_COLOURS[category]
    hash_val = abs(hash(category)) % 360
    return f"hsl({hash_val}, 60%, 65%)"


def render_expense_table(df: pd.DataFrame, max_rows: int = None) -> str:
    """
    Render expenses as a styled HTML table with glassmorphism background,
    category colour pills, and alternating row shading.
    """
    if df.empty:
        return ""

    display = df.copy()
    if max_rows:
        display = display.head(max_rows)

    rows_html = ""
    for i, (_, row) in enumerate(display.iterrows()):
        bg = "rgba(77,47,178,0.12)" if i % 2 == 0 else "rgba(14,33,160,0.08)"

        try:
            date_str = pd.to_datetime(row["date"]).strftime("%d %b %Y")
        except Exception:
            date_str = str(row["date"])

        cat    = str(row.get("category", "Other"))
        colour = get_category_colour(cat)
        cat_pill = (
            f"<span style='"
            f"background:{colour}22;"
            f"border:1px solid {colour}88;"
            f"color:{colour};"
            f"font-size:0.75rem;"
            f"font-weight:600;"
            f"padding:2px 10px;"
            f"border-radius:20px;"
            f"letter-spacing:0.03em;"
            f"white-space:nowrap;"
            f"'>{cat}</span>"
        )

        try:
            amt = f"&#8377;{float(row.get('amount_inr', 0)):,.2f}"
        except Exception:
            amt = str(row.get("amount_inr", ""))

        raw_desc = str(row.get("description", "")).strip()
        desc = raw_desc if raw_desc else \
            "<span style='color:#9090B8;font-style:italic;'>—</span>"

        currency = str(row.get("currency", "INR"))

        is_rec = row.get("is_recurring", 0)
        rec_badge = (
            "<span style='"
            "background:rgba(177,83,215,0.2);"
            "border:1px solid rgba(177,83,215,0.5);"
            "color:#B153D7;"
            "font-size:0.7rem;"
            "padding:1px 7px;"
            "border-radius:20px;"
            "margin-left:6px;"
            "'>&#x1F501;</span>"
            if is_rec else ""
        )

        rows_html += f"""
        <tr style="background:{bg};">
            <td style="padding:10px 14px; color:#C8C8E8;
                       font-size:0.85rem; white-space:nowrap;">
                {date_str}
            </td>
            <td style="padding:10px 14px; color:#C8C8E8;
                       font-size:0.85rem; max-width:220px;
                       overflow:hidden; text-overflow:ellipsis;
                       white-space:nowrap;">
                {desc}{rec_badge}
            </td>
            <td style="padding:10px 14px;">{cat_pill}</td>
            <td style="padding:10px 14px; color:#F0F0FF;
                       font-family:'Libre Baskerville',Georgia,serif;
                       font-weight:700; font-size:0.9rem;
                       text-align:right; white-space:nowrap;">
                {amt}
            </td>
            <td style="padding:10px 14px; color:#9090B8;
                       font-size:0.8rem; text-align:center;">
                {currency}
            </td>
        </tr>
        """

    return f"""
    <div style="
        background: rgba(14,33,160,0.25);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(177,83,215,0.35);
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(10,10,60,0.35);
        margin-bottom: 1rem;
    ">
        <table style="width:100%; border-collapse:collapse;
                      font-family:Inter,sans-serif;">
            <thead>
                <tr style="background:rgba(77,47,178,0.5);
                           border-bottom:1px solid rgba(177,83,215,0.35);">
                    <th style="padding:10px 14px; text-align:left;
                               font-size:0.75rem; font-weight:600;
                               text-transform:uppercase;
                               letter-spacing:0.07em; color:#9090B8;">
                        Date
                    </th>
                    <th style="padding:10px 14px; text-align:left;
                               font-size:0.75rem; font-weight:600;
                               text-transform:uppercase;
                               letter-spacing:0.07em; color:#9090B8;">
                        Description
                    </th>
                    <th style="padding:10px 14px; text-align:left;
                               font-size:0.75rem; font-weight:600;
                               text-transform:uppercase;
                               letter-spacing:0.07em; color:#9090B8;">
                        Category
                    </th>
                    <th style="padding:10px 14px; text-align:right;
                               font-size:0.75rem; font-weight:600;
                               text-transform:uppercase;
                               letter-spacing:0.07em; color:#9090B8;">
                        Amount
                    </th>
                    <th style="padding:10px 14px; text-align:center;
                               font-size:0.75rem; font-weight:600;
                               text-transform:uppercase;
                               letter-spacing:0.07em; color:#9090B8;">
                        Currency
                    </th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """


def get_all_categories(user_id: int) -> list[str]:
    """Merge default CATEGORIES with any custom ones the user created."""
    custom = database.get_custom_categories(user_id)
    extras = [c for c in custom if c not in CATEGORIES]
    return CATEGORIES + extras


# ── Helper — load expenses as DataFrame ──────────────────────────────────────

def load_expenses(user_id: int, from_date=None, to_date=None,
                  categories=None) -> pd.DataFrame:
    rows = database.get_expenses(
        user_id,
        from_date=str(from_date) if from_date else None,
        to_date=str(to_date) if to_date else None,
        categories=categories if categories else None
    )

    if not rows:
        return pd.DataFrame(columns=[
            "id", "user_id", "amount", "description",
            "category", "date", "currency", "amount_inr",
            "is_recurring", "created_at"
        ])

    df = pd.DataFrame([dict(row) for row in rows])
    df["date"] = pd.to_datetime(df["date"])
    return df


# ── Add expense page ──────────────────────────────────────────────────────────

def show_add_expense_page() -> None:
    st.header("➕ Add Expense")

    user_id = st.session_state["user_id"]

    # ── Custom category manager ───────────────────────────────────
    with st.expander("➕ Manage custom categories", expanded=False):
        custom_cats = database.get_custom_categories(user_id)

        col_input, col_btn = st.columns([3, 1])
        with col_input:
            new_cat_name = st.text_input(
                "New category name",
                placeholder="e.g. Stocks, Loan repayment, Rent...",
                key="new_category_input",
                label_visibility="collapsed"
            )
        with col_btn:
            if st.button("Add", key="add_cat_btn", use_container_width=True):
                if not new_cat_name.strip():
                    st.error("Please enter a category name.")
                elif new_cat_name.strip().title() in CATEGORIES:
                    st.error(
                        f"'{new_cat_name.strip().title()}' "
                        f"is already a default category."
                    )
                else:
                    success = database.add_custom_category(
                        user_id, new_cat_name
                    )
                    if success:
                        st.success(
                            f"'{new_cat_name.strip().title()}' added!"
                        )
                        st.rerun()
                    else:
                        st.error(
                            "Category already exists or couldn't be added."
                        )

        if custom_cats:
            st.caption("Your custom categories:")
            for cat in custom_cats:
                col_cat, col_del = st.columns([4, 1])
                with col_cat:
                    colour = get_category_colour(cat)
                    st.markdown(
                        f"<span style='color:{colour}; "
                        f"font-size:0.88rem;'>● {cat}</span>",
                        unsafe_allow_html=True
                    )
                with col_del:
                    if st.button("✕", key=f"del_cat_{cat}",
                                 help=f"Delete {cat}"):
                        database.delete_custom_category(user_id, cat)
                        st.rerun()
        else:
            st.caption("No custom categories yet.")

    # ── Expense form ──────────────────────────────────────────────
    all_categories = get_all_categories(user_id)

    with st.form("add_expense_form", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])

        with col1:
            amount = st.number_input(
                "Amount",
                min_value=0.01,
                step=1.0,
                format="%.2f",
                help="Enter the amount you spent"
            )
            description = st.text_input(
                "Description (optional)",
                placeholder="e.g. Zomato order, Ola cab..."
            )

        with col2:
            date = st.date_input(
                "Date",
                value=datetime.date.today(),
                help="When did you spend this?"
            )
            currency = st.selectbox(
                "Currency",
                CURRENCIES,
                index=0,
                help="Select currency — will be converted to INR"
            )
            recurring = st.checkbox(
                "Recurring expense",
                help="E.g. Netflix, gym membership"
            )

        st.markdown("**Select category:**")
        selected_category = st.selectbox(
            "Category",
            all_categories,
            help="Pick the category that fits best"
        )

        submitted = st.form_submit_button(
            "Save Expense",
            use_container_width=True,
            type="primary"
        )

    if submitted:
        if amount <= 0:
            st.error("Amount must be greater than zero.")
            return

        amount_inr, used_fallback = convert_to_inr(amount, currency)

        if used_fallback and currency != "INR":
            st.warning(
                "⚠️ Live exchange rates unavailable — "
                "using approximate rates for conversion."
            )

        from ml_insights import check_anomaly
        is_anomaly, z_score = check_anomaly(
            user_id, amount_inr, selected_category
        )

        database.add_expense(
            user_id=user_id,
            amount=amount,
            description=description,
            category=selected_category,
            date=str(date),
            currency=currency,
            amount_inr=amount_inr,
            is_recurring=int(recurring)
        )

        if currency != "INR":
            st.success(
                f"✅ {currency} {amount:,.2f} → ₹{amount_inr:,.2f} added "
                f"under **{selected_category}** "
                f"on {date.strftime('%d %b %Y')}"
            )
        else:
            st.success(
                f"✅ ₹{amount:,.2f} added under **{selected_category}** "
                f"on {date.strftime('%d %b %Y')}"
            )

        if is_anomaly:
            cat_expenses = database.get_expenses(
                user_id, categories=[selected_category]
            )
            if cat_expenses:
                amounts = [r["amount_inr"] for r in cat_expenses]
                avg = sum(amounts) / len(amounts)
                st.warning(
                    f"⚠️ This is **{amount_inr / avg:.1f}x** your average "
                    f"{selected_category} expense (avg ₹{avg:,.0f}). "
                    f"Looks unusual — double check this entry."
                )

    # ── Recent expenses preview ───────────────────────────────────
    st.divider()
    st.subheader("Recent additions")

    df = load_expenses(user_id)

    if df.empty:
        st.info("No expenses yet. Add your first one above!")
        return

    html(
    render_expense_table(df, max_rows=5),
    height=350,
    scrolling=False,
)


# ── My Expenses page ──────────────────────────────────────────────────────────

def show_expenses_page() -> None:
    st.header("📋 My Expenses")

    user_id = st.session_state["user_id"]
    today   = datetime.date.today()

    # ── Filters ───────────────────────────────────────────────────
    st.subheader("Filters")
    col1, col2, col3 = st.columns(3)

    with col1:
        preset = st.selectbox(
            "Quick range",
            ["This month", "Last 7 days", "Last month", "All time", "Custom"]
        )

    if preset == "This month":
        from_date = today.replace(day=1)
        to_date   = today
    elif preset == "Last 7 days":
        from_date = today - datetime.timedelta(days=7)
        to_date   = today
    elif preset == "Last month":
        first_this_month = today.replace(day=1)
        to_date   = first_this_month - datetime.timedelta(days=1)
        from_date = to_date.replace(day=1)
    elif preset == "All time":
        from_date = datetime.date(2000, 1, 1)
        to_date   = today
    else:
        with col2:
            from_date = st.date_input("From", value=today.replace(day=1))
        with col3:
            to_date = st.date_input("To", value=today)

    with col2 if preset != "Custom" else st.columns(1)[0]:
        all_categories = get_all_categories(user_id)
        selected_cats = st.multiselect(
            "Categories",
            all_categories,
            default=all_categories,
            help="Unselect categories to hide them"
        )

    # ── Load data ─────────────────────────────────────────────────
    all_categories = get_all_categories(user_id)
    df = load_expenses(
        user_id,
        from_date=from_date,
        to_date=to_date,
        categories=selected_cats if selected_cats else all_categories
    )

    if df.empty:
        st.info("No expenses found for the selected filters.")
        return

    # ── Summary metrics ───────────────────────────────────────────
    total = df["amount_inr"].sum()
    count = len(df)
    avg   = df["amount_inr"].mean()

    m1, m2, m3 = st.columns(3)
    m1.metric("Total spent",  f"₹{total:,.2f}")
    m2.metric("Transactions", count)
    m3.metric("Average",      f"₹{avg:,.2f}")

    st.divider()

    # ── Styled transactions table ─────────────────────────────────
    st.subheader("Transactions")
    html(
    render_expense_table(df),
    height=500,
    scrolling=False,
)

    # ── Edit / Delete ─────────────────────────────────────────────
    st.divider()
    st.subheader("Edit or delete an expense")
    st.caption("Select an expense to edit or delete it.")

    expense_labels = {
        row["id"]: (
            f"{pd.to_datetime(row['date']).strftime('%d %b')}  |  "
            f"{row['category']}  |  "
            f"₹{row['amount_inr']:,.0f}  |  "
            f"{row['description'] or '(no description)'}"
        )
        for _, row in df.iterrows()
    }

    selected_id = st.selectbox(
        "Select expense",
        options=list(expense_labels.keys()),
        format_func=lambda x: expense_labels[x]
    )

    if selected_id:
        selected_row = df[df["id"] == selected_id].iloc[0]
        all_cats_for_edit = get_all_categories(user_id)

        tab_edit, tab_delete = st.tabs(["✏️ Edit", "🗑️ Delete"])

        with tab_edit:
            with st.form("edit_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_amount = st.number_input(
                        "Amount",
                        value=float(selected_row["amount_inr"]),
                        min_value=0.01,
                        step=1.0
                    )
                    new_desc = st.text_input(
                        "Description",
                        value=selected_row["description"] or ""
                    )
                with col2:
                    new_date = st.date_input(
                        "Date",
                        value=pd.to_datetime(selected_row["date"]).date()
                    )
                    new_cat = st.selectbox(
                        "Category",
                        all_cats_for_edit,
                        index=all_cats_for_edit.index(
                            selected_row["category"]
                        ) if selected_row["category"]
                        in all_cats_for_edit else 0
                    )
                    new_currency = st.selectbox(
                        "Currency",
                        CURRENCIES,
                        index=CURRENCIES.index(selected_row["currency"])
                        if selected_row["currency"] in CURRENCIES else 0
                    )
                save_edit = st.form_submit_button(
                    "Save changes", type="primary"
                )

            if save_edit:
                new_amount_inr, _ = convert_to_inr(new_amount, new_currency)
                updated = database.update_expense(
                    expense_id=int(selected_id),
                    user_id=user_id,
                    amount=new_amount,
                    description=new_desc,
                    category=new_cat,
                    date=str(new_date),
                    currency=new_currency,
                    amount_inr=new_amount_inr
                )
                if updated:
                    st.success("Expense updated successfully.")
                    st.rerun()
                else:
                    st.error("Could not update — please try again.")

        with tab_delete:
            st.warning(
                f"You are about to delete: "
                f"**{selected_row['category']}** — "
                f"₹{selected_row['amount_inr']:,.2f} on "
                f"{pd.to_datetime(selected_row['date']).strftime('%d %b %Y')}"
            )
            st.caption("This cannot be undone.")

            col1, col2 = st.columns([1, 3])
            with col1:
                confirm_delete = st.button(
                    "Yes, delete it",
                    type="primary",
                    use_container_width=True
                )

            if confirm_delete:
                deleted = database.delete_expense(
                    expense_id=int(selected_id),
                    user_id=user_id
                )
                if deleted:
                    st.success("Expense deleted.")
                    st.rerun()
                else:
                    st.error("Could not delete — please try again.")