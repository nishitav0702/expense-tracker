import os
import datetime
import streamlit as st
import plotly.graph_objects as go
from groq import Groq
from dotenv import load_dotenv
import database
from expenses import load_expenses
from auth import CATEGORIES

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL        = "llama-3.3-70b-versatile"

COLOUR_MAP = {
    "Food":          "#FF6B6B",
    "Travel":        "#4ECDC4",
    "Shopping":      "#45B7D1",
    "Entertainment": "#96CEB4",
    "Health":        "#FFEAA7",
    "Utilities":     "#DDA0DD",
    "Other":         "#B0B0B0",
}


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_client():
    if not GROQ_API_KEY:
        return None
    return Groq(api_key=GROQ_API_KEY)


# ── Build spending context ────────────────────────────────────────────────────

def _build_spending_context(user_id: int) -> str:
    today     = datetime.date.today()
    from_date = today.replace(day=1)

    df      = load_expenses(user_id, from_date=from_date, to_date=today)
    budgets = database.get_budgets(user_id, today.month, today.year)

    if df.empty:
        return "No expenses recorded this month."

    total_spent = df["amount_inr"].sum()
    lines       = [
        f"Month: {today.strftime('%B %Y')}",
        f"Total spent: Rs{total_spent:,.0f}",
        f"Days elapsed: {today.day} of {_days_in_month(today)}",
        "",
        "Category breakdown:"
    ]

    category_totals = df.groupby("category")["amount_inr"].sum()

    from expenses import get_all_categories
    for cat in get_all_categories(user_id):
        spent  = float(category_totals.get(cat, 0))
        budget = float(budgets.get(cat, 0))

        if spent == 0 and budget == 0:
            continue

        pct        = (spent / budget * 100) if budget > 0 else 0
        status     = "over budget" if pct > 100 else f"{pct:.0f}% of budget used"
        budget_str = f"Rs{budget:,.0f}" if budget > 0 else "no budget set"

        lines.append(
            f"  {cat}: spent Rs{spent:,.0f} ({budget_str}, {status})"
        )

    top3 = df.nlargest(3, "amount_inr")[["description", "category", "amount_inr"]]
    lines.append("")
    lines.append("Top 3 single expenses:")
    for _, row in top3.iterrows():
        lines.append(
            f"  Rs{row['amount_inr']:,.0f} - {row['description']} ({row['category']})"
        )

    return "\n".join(lines)


def _days_in_month(date: datetime.date) -> int:
    if date.month == 12:
        return 31
    return (datetime.date(date.year, date.month + 1, 1)
            - datetime.timedelta(days=1)).day


# ── Radial gauge chart ────────────────────────────────────────────────────────

def _make_gauge(category: str, spent: float,
                budget: float, colour: str) -> go.Figure:
    """
    Single radial gauge for one category.
    Green → yellow → red as % used increases.
    Shows spent vs budget below the needle.
    """
    pct = min((spent / budget * 100) if budget > 0 else 0, 150)

    # Colour based on percentage
    if pct >= 100:
        bar_colour = "#EF4444"   # red
    elif pct >= 70:
        bar_colour = "#F59E0B"   # amber
    else:
        bar_colour = "#1D9E75"   # green

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=spent,
        delta={
            "reference": budget,
            "increasing": {"color": "#EF4444"},
            "decreasing": {"color": "#1D9E75"},
            "valueformat": ",.0f",
            "prefix": "Rs"
        },
        number={
            "prefix": "Rs",
            "valueformat": ",.0f",
            "font": {"size": 16}
        },
        title={
            "text": f"<b>{category}</b><br>"
                    f"<span style='font-size:11px;color:#888'>"
                    f"Budget Rs{budget:,.0f}</span>",
            "font": {"size": 13}
        },
        gauge={
            "axis": {
                "range": [0, max(budget * 1.3, spent * 1.1)],
                "tickwidth": 1,
                "tickcolor": "#444",
                "tickfont": {"size": 9}
            },
            "bar":  {"color": bar_colour, "thickness": 0.25},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, budget * 0.6],
                 "color": "rgba(29,158,117,0.1)"},
                {"range": [budget * 0.6, budget * 0.85],
                 "color": "rgba(245,158,11,0.1)"},
                {"range": [budget * 0.85, max(budget * 1.3, spent * 1.1)],
                 "color": "rgba(239,68,68,0.1)"},
            ],
            "threshold": {
                "line": {"color": "#ffffff", "width": 2},
                "thickness": 0.75,
                "value": budget
            }
        }
    ))

    fig.update_layout(
        height=200,
        margin=dict(t=60, b=10, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#E8E8F0"}
    )

    return fig


def _show_visual_summary(user_id: int) -> None:
    """
    Visual monthly summary using radial gauges.
    One gauge per category that has a budget set.
    3 gauges per row.
    """
    today     = datetime.date.today()
    from_date = today.replace(day=1)

    df      = load_expenses(user_id, from_date=from_date, to_date=today)
    budgets = database.get_budgets(user_id, today.month, today.year)

    if df.empty or not budgets:
        st.info("Add expenses and set budgets to see your visual summary.")
        return

    # ── Top metric cards ──────────────────────────────────────────
    total_spent  = df["amount_inr"].sum()
    total_budget = sum(budgets.values())
    days_left    = _days_in_month(today) - today.day
    daily_avg    = total_spent / max(today.day, 1)

    if not df.empty:
        top_cat = (
            df.groupby("category")["amount_inr"]
            .sum()
            .idxmax()
        )
    else:
        top_cat = "—"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total spent",    f"Rs{total_spent:,.0f}")
    c2.metric("Budget left",    f"Rs{total_budget - total_spent:,.0f}",
              delta=f"of Rs{total_budget:,.0f}",
              delta_color="off")
    c3.metric("Daily average",  f"Rs{daily_avg:,.0f}")
    c4.metric("Days remaining", str(days_left))

    st.markdown("---")

    # ── Gauges — 3 per row ────────────────────────────────────────
    category_totals = df.groupby("category")["amount_inr"].sum()

    # Only show categories that have a budget set
    from expenses import get_all_categories
    all_cats = get_all_categories(user_id)
    active_cats = [
        cat for cat in all_cats
        if budgets.get(cat, 0) > 0
    ]

    if not active_cats:
        st.info("Set budgets in Settings to see gauges.")
        return

    # Chunk into rows of 3
    for row_start in range(0, len(active_cats), 3):
        row_cats = active_cats[row_start: row_start + 3]
        cols     = st.columns(len(row_cats))

        for col, cat in zip(cols, row_cats):
            spent  = float(category_totals.get(cat, 0))
            budget = float(budgets.get(cat, 0))
            colour = COLOUR_MAP.get(cat, "#888888")

            with col:
                fig = _make_gauge(cat, spent, budget, colour)
                st.plotly_chart(fig, use_container_width=True)


# ── AI calls ──────────────────────────────────────────────────────────────────

def get_weekly_summary(user_id: int) -> str:
    """
    One punchy AI sentence summarising the month.
    Cached in session_state.
    """
    cache_key = f"ai_summary_{user_id}"

    if cache_key in st.session_state:
        return st.session_state[cache_key]

    client = _get_client()
    if not client:
        return "AI insights unavailable — add GROQ_API_KEY to your .env file."

    context = _build_spending_context(user_id)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=150,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a personal finance assistant. "
                        "Give one punchy sentence summarising the month. "
                        "Always reference specific numbers. "
                        "Use Rs for amounts. Be direct, no fluff."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Here is my spending data:\n\n{context}\n\n"
                        "Give me one sentence: how is my month going overall?"
                    )
                }
            ]
        )
        result = response.choices[0].message.content.strip()

    except Exception as e:
        result = f"Could not generate summary - {str(e)}"

    st.session_state[cache_key] = result
    return result


def get_saving_tips(user_id: int) -> list[dict]:
    """
    Generate 3 saving tips as structured JSON.
    Each tip has a headline and detail.
    Cached in session_state.

    Returns list of {"headline": str, "detail": str}
    """
    cache_key = f"ai_tips_{user_id}"

    if cache_key in st.session_state:
        return st.session_state[cache_key]

    client = _get_client()
    if not client:
        return [{"headline": "AI unavailable",
                 "detail": "Add GROQ_API_KEY to your .env file."}]

    context = _build_spending_context(user_id)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=500,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a personal finance coach. "
                        "Return ONLY valid JSON, no markdown, no backticks, "
                        "no explanation. "
                        "Format: "
                        '{\"tips\": ['
                        '{\"headline\": \"short bold title\", '
                        '\"detail\": \"one specific actionable sentence '
                        'referencing actual Rs amounts from the data\"}'
                        "]} "
                        "Give exactly 3 tips. "
                        "Each headline must be under 8 words. "
                        "Each detail must mention a specific Rs amount. "
                        "Never give generic advice."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Here is my spending data:\n\n{context}\n\n"
                        "Give me 3 specific saving tips as JSON."
                    )
                }
            ]
        )

        raw = response.choices[0].message.content.strip()

        # Strip any accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        import json
        parsed = json.loads(raw.strip())
        result = parsed.get("tips", [])

        # Fallback if parsing gives unexpected shape
        if not result or not isinstance(result, list):
            raise ValueError("Unexpected JSON shape")

    except Exception as e:
        result = [
            {
                "headline": "Could not generate tips",
                "detail": f"Error: {str(e)}"
            }
        ]

    st.session_state[cache_key] = result
    return result


def answer_question(user_id: int, question: str) -> str:
    """
    Answer a free-form question about spending.
    Not cached — fresh call every time.
    """
    client = _get_client()
    if not client:
        return "AI unavailable — add GROQ_API_KEY to your .env file."

    context = _build_spending_context(user_id)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=400,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a personal finance assistant. "
                        "Answer based only on the spending data provided. "
                        "Be specific, reference actual Rs amounts. "
                        "Keep answers concise — 3-4 sentences max."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Here is my spending data:\n\n{context}\n\n"
                        f"Question: {question}"
                    )
                }
            ]
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Could not answer - {str(e)}"


# ── Streamlit UI ──────────────────────────────────────────────────────────────

def show_ai_page() -> None:
    st.header("✨ AI Insights")
    st.caption("Powered by Groq · LLaMA 3.3 · Your data never leaves your session")

    user_id = st.session_state["user_id"]

    from expenses import load_expenses as _le
    if _le(user_id).empty:
        st.info("Add some expenses first — AI needs data to analyse.")
        return

    # ── Refresh button ────────────────────────────────────────────
    col_refresh, _ = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Refresh insights",
                     help="Clear cache and fetch fresh AI insights"):
            for key in [f"ai_summary_{user_id}", f"ai_tips_{user_id}"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # ── Section 1 — Visual monthly summary ───────────────────────
    st.subheader("📊 Monthly summary")
    st.caption(f"Budget usage at a glance — {datetime.date.today().strftime('%B %Y')}")

    _show_visual_summary(user_id)

    # AI one-liner below the gauges
    with st.spinner("Generating AI commentary..."):
        summary = get_weekly_summary(user_id)

    st.markdown(
        f"""
        <div style="
            background: #1A1A2E;
            border-left: 4px solid #6C63FF;
            border-radius: 0 8px 8px 0;
            padding: 12px 16px;
            margin: 12px 0;
            font-size: 14px;
            color: #E8E8F0;
            font-style: italic;
        ">
        💬 {summary}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    # ── Section 2 — Saving tips as accordions ────────────────────
    st.subheader("💡 Personalised saving tips")
    st.caption("Based on your current month's spending patterns.")

    with st.spinner("Generating tips..."):
        tips = get_saving_tips(user_id)

    TIP_ICONS  = ["🔴", "🟠", "🟡"]
    TIP_COLOURS = ["#EF4444", "#F59E0B", "#6C63FF"]

    for i, tip in enumerate(tips):
        headline = tip.get("headline", f"Tip {i + 1}")
        detail   = tip.get("detail", "")
        icon     = TIP_ICONS[i] if i < len(TIP_ICONS) else "💡"
        colour   = TIP_COLOURS[i] if i < len(TIP_COLOURS) else "#6C63FF"

        with st.expander(f"{icon}  **{headline}**", expanded=(i == 0)):
            # Bold any Rs amounts in the detail text
            import re
            bolded = re.sub(
                r"(Rs[\d,]+)",
                r"**\1**",
                detail
            )
            st.markdown(
                f"""
                <div style="
                    border-left: 3px solid {colour};
                    padding: 8px 12px;
                    border-radius: 0 6px 6px 0;
                    background: rgba(255,255,255,0.02);
                ">
                {detail}
                </div>
                """,
                unsafe_allow_html=True
            )

    st.divider()

    # ── Section 3 — Free-form Q&A ─────────────────────────────────
    st.subheader("💬 Ask about your spending")
    st.caption(
        "Ask anything — 'Where am I wasting money?', "
        "'What should I cut first?', "
        "'How close am I to my budget?'"
    )

    question = st.text_input(
        "Your question",
        placeholder="e.g. Where am I wasting the most money?",
        label_visibility="collapsed"
    )

    if st.button("Ask", type="primary") and question.strip():
        with st.spinner("Thinking..."):
            answer = answer_question(user_id, question.strip())

        # Render answer with Rs amounts bolded
        import re
        bolded_answer = re.sub(r"(Rs[\d,]+)", r"**\1**", answer)
        st.markdown(
            f"""
            <div style="
                background: #1A1A2E;
                border: 1px solid #2D2D3F;
                border-radius: 8px;
                padding: 14px 16px;
                font-size: 14px;
                color: #E8E8F0;
                line-height: 1.7;
            ">
            {answer}
            </div>
            """,
            unsafe_allow_html=True
        )