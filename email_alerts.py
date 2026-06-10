import os
import smtplib
import datetime
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import database

load_dotenv()

GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")


def send_budget_exceeded_email(
    to_email: str,
    username: str,
    category: str,
    spent: float,
    budget: float
) -> bool:
    """
    Send an email when a category exceeds 100% of its budget.
    Returns True if sent successfully, False otherwise.
    """
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return False

    overshoot  = spent - budget
    percentage = (spent / budget * 100) if budget > 0 else 0
    month_name = datetime.date.today().strftime("%B %Y")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"SpendWise Alert — {category} budget exceeded 🚨"
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = to_email

    plain = f"""
Hi {username},

Your {category} budget has been exceeded for {month_name}.

Spent:   ₹{spent:,.0f}
Budget:  ₹{budget:,.0f}
Over by: ₹{overshoot:,.0f} ({percentage:.0f}% used)

Log in to SpendWise to review your expenses.

— SpendWise
    """.strip()

    html = f"""
<html>
<body style="font-family: sans-serif; color: #1A1A2E; padding: 20px;">
    <h2 style="color: #6C63FF;">SpendWise Budget Alert 🚨</h2>
    <p>Hi <strong>{username}</strong>,</p>
    <p>
        Your <strong>{category}</strong> budget has been exceeded
        for <strong>{month_name}</strong>.
    </p>
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px 16px 8px 0; color: #666;">Spent</td>
            <td style="padding: 8px 0;"><strong>₹{spent:,.0f}</strong></td>
        </tr>
        <tr>
            <td style="padding: 8px 16px 8px 0; color: #666;">Budget</td>
            <td style="padding: 8px 0;"><strong>₹{budget:,.0f}</strong></td>
        </tr>
        <tr>
            <td style="padding: 8px 16px 8px 0; color: #666;">Over by</td>
            <td style="padding: 8px 0; color: #e74c3c;">
                <strong>₹{overshoot:,.0f} ({percentage:.0f}% used)</strong>
            </td>
        </tr>
    </table>
    <p>Log in to SpendWise to review your spending.</p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="color: #999; font-size: 12px;">— SpendWise</p>
</body>
</html>
    """.strip()

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())
        return True

    except smtplib.SMTPAuthenticationError:
        print("Email auth failed — check GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env")
        return False

    except smtplib.SMTPException as e:
        print(f"Email send failed: {e}")
        return False


def check_and_alert(user_id: int, to_email: str, username: str) -> list[str]:
    """
    Check all categories for budget overruns and send emails for any
    that have crossed 100% and haven't been alerted yet this session.
    Returns list of categories that triggered an alert.
    """
    from expenses import load_expenses

    today   = datetime.date.today()
    budgets = database.get_budgets(user_id, today.month, today.year)

    if not budgets:
        return []

    # Track which alerts have been sent this session
    alerted_key = f"alerted_categories_{user_id}"
    if alerted_key not in st.session_state:
        st.session_state[alerted_key] = set()

    from_date = today.replace(day=1)
    df        = load_expenses(user_id, from_date=from_date, to_date=today)

    if df.empty:
        return []

    category_totals = df.groupby("category")["amount_inr"].sum()
    triggered       = []

    for category, limit in budgets.items():
        if limit <= 0:
            continue

        spent = float(category_totals.get(category, 0))
        if spent <= limit:
            continue

        if category in st.session_state[alerted_key]:
            continue

        sent = send_budget_exceeded_email(
            to_email=to_email,
            username=username,
            category=category,
            spent=spent,
            budget=limit
        )

        if sent:
            st.session_state[alerted_key].add(category)
            triggered.append(category)

    return triggered