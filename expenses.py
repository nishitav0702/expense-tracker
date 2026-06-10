import streamlit as st
import pandas as pd
import datetime
import database
from auth import CATEGORIES
from api_client import CURRENCIES, convert_to_inr

# Consistent colour per category
CATEGORY_COLOURS = {
    "Food":          "#FF6B6B",
    "Travel":        "#4ECDC4",
    "Shopping":      "#45B7D1",
    "Entertainment": "#96CEB4",
    "Health":        "#FFEAA7",
    "Utilities":     "#DDA0DD",
    "Other":         "#B0B0B0",
}


# ── Helper — load expenses as a pandas DataFrame ──────────────────────────────

def load_expenses(user_id: int, from_date=None, to_date=None,
                  categories=None) -> pd.DataFrame:
    """
    Fetch expenses from SQLite and return as a DataFrame.
    Empty DataFrame if no expenses yet.
    """
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
            CATEGORIES,
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

        # Convert to INR if needed
        amount_inr, used_fallback = convert_to_inr(amount, currency)

        if used_fallback and currency != "INR":
            st.warning(
                "⚠️ Live exchange rates unavailable — "
                "using approximate rates for conversion."
            )

        # Check for anomaly BEFORE saving
        from ml_insights import check_anomaly
        is_anomaly, z_score = check_anomaly(user_id, amount_inr, selected_category)

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
                f"under **{selected_category}** on {date.strftime('%d %b %Y')}"
            )
        else:
            st.success(
                f"✅ ₹{amount:,.2f} added under **{selected_category}** "
                f"on {date.strftime('%d %b %Y')}"
            )

        if is_anomaly:
            cat_expenses = database.get_expenses(user_id, categories=[selected_category])
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

    recent = df.head(5)[["date", "description", "category", "amount_inr", "currency"]].copy()
    recent["date"]       = recent["date"].dt.strftime("%d %b %Y")
    recent["amount_inr"] = recent["amount_inr"].apply(lambda x: f"₹{x:,.2f}")
    recent.columns       = ["Date", "Description", "Category", "Amount (INR)", "Currency"]

    st.dataframe(recent, use_container_width=True, hide_index=True)


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
        selected_cats = st.multiselect(
            "Categories",
            CATEGORIES,
            default=CATEGORIES,
            help="Unselect categories to hide them"
        )

    # ── Load and display ──────────────────────────────────────────
    df = load_expenses(
        user_id,
        from_date=from_date,
        to_date=to_date,
        categories=selected_cats if selected_cats else CATEGORIES
    )

    if df.empty:
        st.info("No expenses found for the selected filters.")
        return

    # ── Summary row ───────────────────────────────────────────────
    total = df["amount_inr"].sum()
    count = len(df)
    avg   = df["amount_inr"].mean()

    m1, m2, m3 = st.columns(3)
    m1.metric("Total spent", f"₹{total:,.2f}")
    m2.metric("Transactions", count)
    m3.metric("Average", f"₹{avg:,.2f}")

    st.divider()

    # ── Expense table ─────────────────────────────────────────────
    st.subheader("Transactions")

    display_df = df[["date", "description", "category",
                      "amount_inr", "currency", "is_recurring"]].copy()
    display_df["date"]         = display_df["date"].dt.strftime("%d %b %Y")
    display_df["amount_inr"]   = display_df["amount_inr"].apply(lambda x: f"₹{x:,.2f}")
    display_df["is_recurring"] = display_df["is_recurring"].apply(
        lambda x: "🔁 Yes" if x else ""
    )
    display_df.columns = ["Date", "Description", "Category",
                           "Amount (₹)", "Currency", "Recurring"]

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── Edit / Delete ─────────────────────────────────────────────
    st.divider()
    st.subheader("Edit or delete an expense")
    st.caption("Select an expense to edit or delete it.")

    expense_labels = {
        row["id"]: (
            f"{pd.to_datetime(row['date']).strftime('%d %b')}  |  "
            f"{row['category']}  |  ₹{row['amount_inr']:,.0f}  |  "
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
                        CATEGORIES,
                        index=CATEGORIES.index(selected_row["category"])
                        if selected_row["category"] in CATEGORIES else 0
                    )
                    new_currency = st.selectbox(
                        "Currency",
                        CURRENCIES,
                        index=CURRENCIES.index(selected_row["currency"])
                        if selected_row["currency"] in CURRENCIES else 0
                    )
                save_edit = st.form_submit_button("Save changes", type="primary")

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
                f"You are about to delete: **{selected_row['category']}** — "
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