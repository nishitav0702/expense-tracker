import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import database
from expenses import load_expenses
from auth import CATEGORIES

# ── Consistent category colours across every chart ────────────────────────────
# Pass this to every Plotly chart's color_discrete_map argument.
# This means Food is always red, Travel always teal, etc — looks designed.
COLOUR_MAP = {
    "Food":          "#FF6B6B",
    "Travel":        "#4ECDC4",
    "Shopping":      "#45B7D1",
    "Entertainment": "#96CEB4",
    "Health":        "#FFEAA7",
    "Utilities":     "#DDA0DD",
    "Other":         "#B0B0B0",
}


# ── Helper — get this month and last month date ranges ────────────────────────

def get_month_range(month_offset: int = 0):
    """
    Return (from_date, to_date) for a given month.
    month_offset=0 → this month
    month_offset=-1 → last month

    Why this helper?
    Date arithmetic in Python is verbose. Centralising it here
    means you call get_month_range(0) instead of rewriting the
    same 6 lines every time.
    """
    today = datetime.date.today()
    # First day of target month
    month = today.month + month_offset
    year  = today.year

    if month <= 0:
        month += 12
        year  -= 1
    elif month > 12:
        month -= 12
        year  += 1

    from_date = datetime.date(year, month, 1)

    # Last day of target month
    if month == 12:
        to_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        to_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

    # Cap to_date at today so we don't show future dates
    to_date = min(to_date, today)

    return from_date, to_date


# ── Main dashboard function ───────────────────────────────────────────────────

def show_dashboard() -> None:
    """
    Render the full dashboard page.
    Layout:
    1. Overspend warning banners (if any)
    2. Three metric cards
    3. Pie chart + budget progress bars (side by side)
    4. Line chart (full width)
    5. Grouped bar chart — this month vs last month
    """
    st.header("📊 Dashboard")

    user_id = st.session_state["user_id"]
    today   = datetime.date.today()

    # Get this month's date range
    from_date, to_date = get_month_range(0)

    # Load this month's expenses as a DataFrame
    df_this = load_expenses(user_id, from_date=from_date, to_date=to_date)

    # Load last month's expenses for comparison chart
    lm_from, lm_to = get_month_range(-1)
    df_last = load_expenses(user_id, from_date=lm_from, to_date=lm_to)

    # Load budgets for this month
    budgets = database.get_budgets(user_id, today.month, today.year)

    # ── 1. Overspend warning banners ──────────────────────────────
    _show_budget_warnings(df_this, budgets)

    # ── 2. Metric cards ───────────────────────────────────────────
    _show_metric_cards(df_this, budgets)

    st.divider()

    # ── 3. Pie chart + budget bars ────────────────────────────────
    if not df_this.empty:
        col_left, col_right = st.columns([1.2, 1])

        with col_left:
            _show_pie_chart(df_this)

        with col_right:
            _show_budget_progress(df_this, budgets)
    else:
        st.info("Add some expenses to see your spending breakdown.")

    st.divider()

    # ── 4. Daily spending line chart ──────────────────────────────
    if not df_this.empty:
        _show_line_chart(df_this, from_date, to_date)
        st.divider()

    # ── 5. This month vs last month bar chart ─────────────────────
    if not df_this.empty or not df_last.empty:
        _show_comparison_chart(df_this, df_last)


# ── Section renderers — each chart is its own function ───────────────────────
# Why split into functions?
# Each function does one thing and is easy to debug independently.
# If the pie chart breaks, you know exactly where to look.

def _show_budget_warnings(df: pd.DataFrame, budgets: dict) -> None:
    """
    Show a warning banner for any category at 80%+ of its budget.
    Show an error banner for any category at 100%+.

    This runs before anything else so warnings are always visible
    at the top of the page.
    """
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
                f"⚠️ **{category}** is at {pct:.0f}% of budget — "
                f"₹{spent:,.0f} of ₹{limit:,.0f} spent"
            )


def _show_metric_cards(df: pd.DataFrame, budgets: dict) -> None:
    """
    Three st.metric() cards:
    - Total spent this month
    - Total budget remaining
    - Top spending category
    """
    total_spent  = df["amount_inr"].sum() if not df.empty else 0
    total_budget = sum(budgets.values())
    remaining    = total_budget - total_spent

    # Top category by spend
    if not df.empty:
        top_cat = (
            df.groupby("category")["amount_inr"]
            .sum()
            .idxmax()
        )
    else:
        top_cat = "—"

    col1, col2, col3 = st.columns(3)

    col1.metric(
        label="Spent this month",
        value=f"₹{total_spent:,.0f}",
    )
    col2.metric(
        label="Budget remaining",
        value=f"₹{remaining:,.0f}",
        delta=f"of ₹{total_budget:,.0f} total" if total_budget > 0 else "No budget set",
        delta_color="off"
    )
    col3.metric(
        label="Top category",
        value=top_cat
    )


def _show_pie_chart(df: pd.DataFrame) -> None:
    """
    Donut chart showing % of total spending per category.

    px.pie() takes a DataFrame, a values column, and a names column.
    hole=0.4 makes it a donut instead of a full pie.
    color_discrete_map ensures consistent colours.
    """
    st.subheader("Spending by category")

    category_totals = (
        df.groupby("category")["amount_inr"]
        .sum()
        .reset_index()
    )
    # reset_index() converts the grouped Series back into a
    # regular DataFrame with "category" and "amount_inr" columns
    # — required by plotly express

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
    """
    Progress bar per category showing budget usage.
    Green < 60%, Orange 60-85%, Red > 85%.

    st.progress() takes a float between 0.0 and 1.0.
    """
    st.subheader("Budget usage")

    if not budgets:
        st.caption("No budgets set. Go to ⚙️ Settings to add them.")
        return

    category_totals = df.groupby("category")["amount_inr"].sum()

    for category in CATEGORIES:
        limit = budgets.get(category, 0)
        if limit <= 0:
            continue

        spent = category_totals.get(category, 0)
        pct   = min(spent / limit, 1.0)  # cap at 1.0 so bar doesn't overflow

        # Colour label based on usage
        if pct >= 0.85:
            label_colour = "🔴"
        elif pct >= 0.60:
            label_colour = "🟠"
        else:
            label_colour = "🟢"

        st.caption(
            f"{label_colour} **{category}** — "
            f"₹{spent:,.0f} / ₹{limit:,.0f} ({pct*100:.0f}%)"
        )
        st.progress(float(pct))


def _show_line_chart(df: pd.DataFrame,
                     from_date: datetime.date,
                     to_date: datetime.date) -> None:
    """
    Line chart of daily spending across the current month.

    Steps:
    1. Group expenses by date → sum of amount_inr per day
    2. Reindex to fill in missing days with 0 (days with no spending)
    3. Plot with px.line()

    reindex() is the key pandas trick here — without it, days with
    no expenses are simply missing from the chart, creating gaps.
    """
    st.subheader("Daily spending this month")

    # Build a complete date index for the month
    all_days = pd.date_range(start=from_date, end=to_date, freq="D")

    # Group by date
    daily = (
        df.groupby(df["date"].dt.date)["amount_inr"]
        .sum()
        .reindex(all_days, fill_value=0)  # fills missing days with 0
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
    fig.update_traces(
        hovertemplate="₹%{y:,.0f}"
    )

    st.plotly_chart(fig, use_container_width=True)


def _show_comparison_chart(df_this: pd.DataFrame,
                            df_last: pd.DataFrame) -> None:
    """
    Grouped bar chart comparing this month vs last month per category.

    Steps:
    1. Compute per-category totals for each month
    2. Combine into one DataFrame with a "Month" column
    3. Plot with px.bar(barmode="group")

    The "Month" column is what tells Plotly to group the bars.
    """
    st.subheader("This month vs last month")

    def category_totals(df: pd.DataFrame, label: str) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["category", "amount_inr", "Month"])
        totals = (
            df.groupby("category")["amount_inr"]
            .sum()
            .reset_index()
        )
        totals["Month"] = label
        return totals

    this_totals = category_totals(df_this, "This month")
    last_totals = category_totals(df_last, "Last month")

    combined = pd.concat([last_totals, this_totals], ignore_index=True)

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
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>₹%{y:,.0f}"
    )

    st.plotly_chart(fig, use_container_width=True)