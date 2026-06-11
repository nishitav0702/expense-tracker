import os
import datetime
import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import database
from expenses import load_expenses
from auth import CATEGORIES

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL        = "llama-3.3-70b-versatile"   # updated — llama3-8b-8192 decommissioned


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_client():
    if not GROQ_API_KEY:
        return None
    return Groq(api_key=GROQ_API_KEY)


# ── Build spending context ────────────────────────────────────────────────────

def _build_spending_context(user_id: int) -> str:
    """
    Pre-compute a structured summary of the user's spending.
    Injected into every Groq prompt as context.
    Clean numbers = better AI output.
    """
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

    for cat in CATEGORIES:
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


# ── AI calls ──────────────────────────────────────────────────────────────────

def get_weekly_summary(user_id: int) -> str:
    """
    Generate a plain-English summary of the user's spending.
    Cached in session_state - only refreshed on demand.
    """
    cache_key = f"ai_summary_{user_id}"

    if cache_key in st.session_state:
        return st.session_state[cache_key]

    client = _get_client()
    if not client:
        return "AI insights unavailable - add GROQ_API_KEY to your .env file."

    context = _build_spending_context(user_id)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=300,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a friendly personal finance assistant. "
                        "Give concise, specific insights based only on the "
                        "data provided. Use Rs for amounts. "
                        "Never give generic advice - always reference actual numbers. "
                        "Keep response to 3-4 sentences."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Here is my spending data:\n\n{context}\n\n"
                        "Give me a brief summary of how my month is going "
                        "and one specific thing I should watch out for."
                    )
                }
            ]
        )
        result = response.choices[0].message.content.strip()

    except Exception as e:
        result = f"Could not generate summary - {str(e)}"

    st.session_state[cache_key] = result
    return result


def get_saving_tips(user_id: int) -> str:
    """
    Generate 3 specific saving tips based on worst category.
    Cached in session_state.
    """
    cache_key = f"ai_tips_{user_id}"

    if cache_key in st.session_state:
        return st.session_state[cache_key]

    client = _get_client()
    if not client:
        return "AI tips unavailable - add GROQ_API_KEY to your .env file."

    context = _build_spending_context(user_id)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=350,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a personal finance coach. "
                        "Give exactly 3 actionable saving tips. "
                        "Each tip must reference specific amounts from the data. "
                        "No generic advice. Use Rs for amounts. "
                        "Format as a numbered list."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Here is my spending data:\n\n{context}\n\n"
                        "Give me 3 specific tips to reduce my spending "
                        "based on where I am overspending."
                    )
                }
            ]
        )
        result = response.choices[0].message.content.strip()

    except Exception as e:
        result = f"Could not generate tips - {str(e)}"

    st.session_state[cache_key] = result
    return result


def answer_question(user_id: int, question: str) -> str:
    """
    Answer a free-form question about the user's spending.
    Not cached - each question is a fresh call.
    """
    client = _get_client()
    if not client:
        return "AI unavailable - add GROQ_API_KEY to your .env file."

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
                        "Answer questions based only on the spending data provided. "
                        "Be specific and reference actual numbers. "
                        "Use Rs for amounts. Keep answers concise."
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
    st.caption("Powered by Groq · LLaMA 3 · Your data never leaves your session")

    user_id = st.session_state["user_id"]

    from expenses import load_expenses as _le
    if _le(user_id).empty:
        st.info("Add some expenses first - AI needs data to analyse.")
        return

    # ── Summary ───────────────────────────────────────────────────
    st.subheader("📋 Monthly summary")

    col_refresh, _ = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Refresh", help="Fetch a fresh summary from AI"):
            for key in [f"ai_summary_{user_id}", f"ai_tips_{user_id}"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    with st.spinner("Generating summary..."):
        summary = get_weekly_summary(user_id)

    st.info(summary)

    st.divider()

    # ── Saving tips ───────────────────────────────────────────────
    st.subheader("💡 Personalised saving tips")
    st.caption("Based on your current month's spending patterns.")

    with st.spinner("Generating tips..."):
        tips = get_saving_tips(user_id)

    st.success(tips)

    st.divider()

    # ── Free-form Q&A ─────────────────────────────────────────────
    st.subheader("💬 Ask about your spending")
    st.caption(
        "Ask anything - 'Where am I wasting money?', "
        "'How does this month compare to last?', "
        "'What should I cut first?'"
    )

    question = st.text_input(
        "Your question",
        placeholder="e.g. Where am I wasting the most money?",
        label_visibility="collapsed"
    )

    if st.button("Ask", type="primary") and question.strip():
        with st.spinner("Thinking..."):
            answer = answer_question(user_id, question.strip())
        st.write(answer)