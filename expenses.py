import streamlit as st
import pandas as pd
import datetime
import database
from auth import CATEGORIES

# Consistent colour per category — used in the table badges
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

    Why DataFrame?
    sqlite3.Row objects are hard to filter and display.
    pandas gives us filtering, sorting, and groupby for free.
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

    # Convert list of sqlite3.Row → list of dicts → DataFrame
    df = pd.DataFrame([dict(row) for row in rows])
    df["date"] = pd.to_datetime(df["date"])   # string → datetime for sorting
    return df


# ── Add expense page ──────────────────────────────────────────────────────────

def show_add_expense_page() -> None:
    """
    Render the Add Expense page.

    Layout:
    - Amount + description + date in a form
    - Category buttons below (outside the form so they feel instant)
    - On save: validate → insert → success message → clear inputs
    """
    st.header("➕ Add Expense")

    user_id = st.session_state["user_id"]

    # ── Input form ────────────────────────────────────────────────
    with st.form("add_expense_form", clear_on_submit=True):
        col1, col2 = st.columns([2, 1])

        with col1:
            amount = st.number_input(
                "Amount (₹)",
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
            recurring = st.checkbox(
                "Recurring expense",
                help="E.g. Netflix, gym membership"
            )

        st.markdown("**Select category:**")

        # Category buttons — 4 per row using columns
        # We use session_state to track which category is selected
        if "selected_category" not in st.session_state:
            st.session_state["selected_category"] = None

        # Display category buttons in a grid
        cols = st.columns(4)
        for i, cat in enumerate(CATEGORIES):
            with cols[i % 4]:
                st.write(f"**{cat}**")

        # Selectbox as fallback (also used as the actual value)
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

    # ── Handle submission ─────────────────────────────────────────
    if submitted:
        if amount <= 0:
            st.error("Amount must be greater than zero.")
            return

        # Check for anomaly BEFORE saving so z-score uses existing history
        from ml_insights import check_anomaly
        is_anomaly, z_score = check_anomaly(user_id, amount, selected_category)

        expense_id = database.add_expense(
            user_id=user_id,
            amount=amount,
            description=description,
            category=selected_category,
            date=str(date),
            currency="INR",
            amount_inr=amount,
            is_recurring=int(recurring)
        )

        st.success(
            f"✅ ₹{amount:,.2f} added under **{selected_category}** "
            f"on {date.strftime('%d %b %Y')}"
        )

        # Show anomaly warning after saving
        if is_anomaly:
            cat_expenses = database.get_expenses(user_id, categories=[selected_category])
            if cat_expenses:
                import pandas as pd
                amounts = [r["amount_inr"] for r in cat_expenses]
                avg = sum(amounts) / len(amounts)
                st.warning(
                    f"⚠️ This is **{amount / avg:.1f}x** your average "
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

    # Show last 5 only in this preview
    recent = df.head(5)[["date", "description", "category", "amount_inr"]].copy()
    recent["date"] = recent["date"].dt.strftime("%d %b %Y")
    recent["amount_inr"] = recent["amount_inr"].apply(lambda x: f"₹{x:,.2f}")
    recent.columns = ["Date", "Description", "Category", "Amount"]

    st.dataframe(recent, use_container_width=True, hide_index=True)


# ── My Expenses page ──────────────────────────────────────────────────────────

def show_expenses_page() -> None:
    """
    Render the My Expenses page with filters, table, edit and delete.
    """
    st.header("📋 My Expenses")

    user_id = st.session_state["user_id"]
    today   = datetime.date.today()

    # ── Filters ───────────────────────────────────────────────────
    st.subheader("Filters")
    col1, col2, col3 = st.columns(3)

    with col1:
        # Quick date range presets
        preset = st.selectbox(
            "Quick range",
            ["This month", "Last 7 days", "Last month", "All time", "Custom"]
        )

    # Compute from/to dates based on preset
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
        # Custom — show date pickers
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

    # ── Summary row above table ───────────────────────────────────
    total = df["amount_inr"].sum()
    count = len(df)
    avg   = df["amount_inr"].mean()

    m1, m2, m3 = st.columns(3)
    m1.metric("Total spent", f"₹{total:,.2f}")
    m2.metric("Transactions", count)
    m3.metric("Average", f"₹{avg:,.2f}")

    st.divider()

    # ── Expense table with edit/delete ────────────────────────────
    st.subheader("Transactions")

    # Display table
    display_df = df[["date", "description", "category",
                      "amount_inr", "currency", "is_recurring"]].copy()
    display_df["date"]        = display_df["date"].dt.strftime("%d %b %Y")
    display_df["amount_inr"]  = display_df["amount_inr"].apply(lambda x: f"₹{x:,.2f}")
    display_df["is_recurring"] = display_df["is_recurring"].apply(
        lambda x: "🔁 Yes" if x else ""
    )
    display_df.columns = ["Date", "Description", "Category",
                           "Amount (₹)", "Currency", "Recurring"]

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── Edit / Delete section ─────────────────────────────────────
    st.divider()
    st.subheader("Edit or delete an expense")
    st.caption("Select an expense by its row number to edit or delete it.")

    # Build a readable label for each expense for the selectbox
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

        # ── Edit tab ──────────────────────────────────────────────
        with tab_edit:
            with st.form("edit_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_amount = st.number_input(
                        "Amount (₹)",
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
                save_edit = st.form_submit_button("Save changes", type="primary")

            if save_edit:
                updated = database.update_expense(
                    expense_id=int(selected_id),
                    user_id=user_id,
                    amount=new_amount,
                    description=new_desc,
                    category=new_cat,
                    date=str(new_date),
                    amount_inr=new_amount
                )
                if updated:
                    st.success("Expense updated successfully.")
                    st.rerun()
                else:
                    st.error("Could not update — please try again.")

        # ── Delete tab ────────────────────────────────────────────
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
