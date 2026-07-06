import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import database
from expenses import load_expenses
from auth import CATEGORIES
from email_alerts import check_and_alert

COLOUR_MAP = {
    "Food":          "#FF6B6B",
    "Travel":        "#4ECDC4",
    "Shopping":      "#45B7D1",
    "Entertainment": "#96CEB4",
    "Health":        "#FFEAA7",
    "Utilities":     "#DDA0DD",
    "Other":         "#B0B0B0",
}


def get_month_range(month_offset: int = 0):
    today = datetime.date.today()
    month = today.month + month_offset
    year  = today.year

    if month <= 0:
        month += 12
        year  -= 1
    elif month > 12:
        month -= 12
        year  += 1

    from_date = datetime.date(year, month, 1)

    if month == 12:
        to_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        to_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

    to_date = min(to_date, today)
    return from_date, to_date


def show_dashboard() -> None:
    st.header("📊 Dashboard")

    user_id  = st.session_state["user_id"]
    email    = st.session_state.get("email", "")
    username = st.session_state.get("username", "")
    today    = datetime.date.today()

    from_date, to_date = get_month_range(0)
    df_this  = load_expenses(user_id, from_date=from_date, to_date=to_date)

    lm_from, lm_to = get_month_range(-1)
    df_last  = load_expenses(user_id, from_date=lm_from, to_date=lm_to)

    budgets  = database.get_budgets(user_id, today.month, today.year)

    # ── Email alerts ──────────────────────────────────────────────
    if email and username:
        triggered = check_and_alert(user_id, email, username)
        for cat in triggered:
            st.toast(f"📧 Budget alert sent for {cat}", icon="✉️")

    # ── 1. Overspend warnings ─────────────────────────────────────
    _show_budget_warnings(df_this, budgets)

    # ── 2. Metric cards ───────────────────────────────────────────
    _show_metric_cards(df_this, budgets)

    st.divider()

    # ── 3. Pie + budget bars ──────────────────────────────────────
    if not df_this.empty:
        col_left, col_right = st.columns([1.2, 1])
        with col_left:
            _show_pie_chart(df_this)
        with col_right:
            _show_budget_progress(df_this, budgets)
    else:
        st.info("No expenses this month yet. Add some to see your dashboard.")
        return

    st.divider()

    # ── 4. Line chart ─────────────────────────────────────────────
    _show_line_chart(df_this, from_date, to_date)

    st.divider()

    # ── 5. Comparison bar chart ───────────────────────────────────
    _show_comparison_chart(df_this, df_last)


def _show_budget_warnings(df: pd.DataFrame, budgets: dict) -> None:
    if df.empty or not budgets:
        return

    category_totals = df.groupby("category")["amount_inr"].sum()

    for category, limit in budgets.items():
        if limit <= 0:
            continue
        spent = category_totals.get(category, 0)
        pct   = (spent / limit) * 100

        if pct >= 100:
            st.error(
                f"🚨 **{category}** budget exceeded! "
                f"Spent ₹{spent:,.0f} of ₹{limit:,.0f} ({pct:.0f}%)"
            )
        elif pct >= 80:
            st.warning(
                f"⚠️ **{category}** at {pct:.0f}% of budget — "
                f"₹{spent:,.0f} of ₹{limit:,.0f} spent"
            )


def _show_metric_cards(df: pd.DataFrame, budgets: dict) -> None:
    total_spent  = df["amount_inr"].sum() if not df.empty else 0
    total_budget = sum(budgets.values())
    remaining    = total_budget - total_spent

    if not df.empty:
        top_cat = (
            df.groupby("category")["amount_inr"]
            .sum()
            .idxmax()
        )
    else:
        top_cat = "—"

    col1, col2, col3 = st.columns(3)
    col1.metric("Spent this month", f"₹{total_spent:,.0f}")
    col2.metric(
        "Budget remaining",
        f"₹{remaining:,.0f}",
        delta=f"of ₹{total_budget:,.0f} total" if total_budget > 0 else "No budget set",
        delta_color="off"
    )
    col3.metric("Top category", top_cat)


def _show_pie_chart(df: pd.DataFrame) -> None:
    st.subheader("Spending by category")

    category_totals = (
        df.groupby("category")["amount_inr"]
        .sum()
        .reset_index()
    )

    fig = px.pie(
        category_totals,
        values="amount_inr",
        names="category",
        hole=0.4,
        color="category",
        color_discrete_map=COLOUR_MAP,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<br>%{percent}"
    )
    fig.update_layout(
        showlegend=True,
        margin=dict(t=20, b=20, l=0, r=0),
        height=320
    )
    st.plotly_chart(fig, use_container_width=True)


def _show_budget_progress(df: pd.DataFrame, budgets: dict) -> None:
    st.subheader("Budget usage")

    if not budgets:
        st.caption("No budgets set. Go to ⚙️ Settings to add them.")
        return

    category_totals = df.groupby("category")["amount_inr"].sum()

    from expenses import get_all_categories
    all_cats = get_all_categories(
        st.session_state.get("user_id", 0)
    )
    for category in all_cats:
        limit = budgets.get(category, 0)
        if limit <= 0:
            continue

        spent = category_totals.get(category, 0)
        pct   = min(spent / limit, 1.0)

        if pct >= 0.85:
            icon = "🔴"
        elif pct >= 0.60:
            icon = "🟠"
        else:
            icon = "🟢"

        st.caption(
            f"{icon} **{category}** — "
            f"₹{spent:,.0f} / ₹{limit:,.0f} ({pct*100:.0f}%)"
        )
        st.progress(float(pct))


def _show_line_chart(df: pd.DataFrame,
                     from_date: datetime.date,
                     to_date: datetime.date) -> None:
    st.subheader("Daily spending this month")

    all_days = pd.date_range(start=from_date, end=to_date, freq="D")

    daily = (
        df.groupby(df["date"].dt.date)["amount_inr"]
        .sum()
        .reindex(all_days, fill_value=0)
        .reset_index()
    )
    daily.columns = ["Date", "Amount (₹)"]

    fig = px.line(
        daily,
        x="Date",
        y="Amount (₹)",
        markers=True,
        color_discrete_sequence=["#6C63FF"]
    )
    fig.update_layout(
        margin=dict(t=20, b=20, l=0, r=0),
        height=280,
        hovermode="x unified"
    )
    fig.update_traces(hovertemplate="₹%{y:,.0f}")
    st.plotly_chart(fig, use_container_width=True)


def _show_comparison_chart(df_this: pd.DataFrame,
                            df_last: pd.DataFrame) -> None:
    st.subheader("This month vs last month")

    def make_totals(df: pd.DataFrame, label: str) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["category", "amount_inr", "Month"])
        totals = (
            df.groupby("category")["amount_inr"]
            .sum()
            .reset_index()
        )
        totals["Month"] = label
        return totals

    combined = pd.concat(
        [make_totals(df_last, "Last month"),
         make_totals(df_this, "This month")],
        ignore_index=True
    )

    if combined.empty:
        st.info("Not enough data for comparison yet.")
        return

    fig = px.bar(
        combined,
        x="category",
        y="amount_inr",
        color="Month",
        barmode="group",
        color_discrete_map={
            "This month": "#6C63FF",
            "Last month": "#B0B0B0"
        },
        labels={"amount_inr": "Amount (₹)", "category": "Category"}
    )
    fig.update_layout(
        margin=dict(t=20, b=20, l=0, r=0),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>₹%{y:,.0f}")
    st.plotly_chart(fig, use_container_width=True)