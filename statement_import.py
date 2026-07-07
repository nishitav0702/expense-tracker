import pdfplumber
import pandas as pd
import streamlit as st
import datetime
import re
import database
from auth import CATEGORIES
from expenses import get_all_categories, load_expenses

# ── Keyword categorizer ───────────────────────────────────────────────────────
# Maps keywords found in transaction descriptions to categories.
# Case-insensitive. Add more as needed.

KEYWORD_MAP = {
    "Food": [
        "zomato", "swiggy", "dominos", "pizza", "mcdonald", "kfc",
        "subway", "burger", "restaurant", "cafe", "coffee", "chai",
        "grocery", "bigbasket", "blinkit", "zepto", "dunzo", "instamart",
        "hotel", "dhaba", "food", "eat", "dining", "bakery", "juice"
    ],
    "Travel": [
        "uber", "ola", "rapido", "auto", "cab", "taxi", "petrol",
        "fuel", "hp petrol", "indian oil", "iocl", "bpcl", "shell",
        "metro", "irctc", "railway", "train", "bus", "redbus",
        "makemytrip", "goibibo", "flight", "indigo", "spicejet",
        "airlines", "toll", "parking", "fastag"
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "meesho", "nykaa",
        "snapdeal", "tatacliq", "reliance", "dmart", "big bazaar",
        "shoppers stop", "lifestyle", "westside", "h&m", "zara",
        "decathlon", "croma", "vijay sales", "poorvika"
    ],
    "Entertainment": [
        "netflix", "amazon prime", "hotstar", "disney", "zee5",
        "spotify", "gaana", "youtube premium", "apple music",
        "bookmyshow", "pvr", "inox", "cinepolis", "gaming",
        "steam", "playstation", "xbox"
    ],
    "Health": [
        "pharmacy", "medplus", "apollo pharmacy", "1mg", "netmeds",
        "practo", "doctor", "hospital", "clinic", "lab", "diagnostic",
        "gym", "cult fit", "healthifyme", "medicine", "medical",
        "dental", "optician", "chemist"
    ],
    "Utilities": [
        "electricity", "bescom", "msedcl", "tata power", "adani electricity",
        "water", "bwssb", "gas", "indane", "hp gas", "bharat gas",
        "broadband", "airtel", "jio", "bsnl", "vi ", "vodafone",
        "idea", "recharge", "mobile", "dth", "tatasky", "dish tv",
        "insurance", "lic", "internet"
    ],
    "Other": []   # fallback
}


def categorize_description(description: str,
                            custom_categories: list[str] = None) -> str:
    """
    Match a transaction description to a category using keyword matching.
    Checks default keywords first, returns 'Other' if nothing matches.
    """
    desc_lower = description.lower()

    for category, keywords in KEYWORD_MAP.items():
        if category == "Other":
            continue
        for keyword in keywords:
            if keyword in desc_lower:
                return category

    return "Other"


# ── PDF parsers — one per bank ────────────────────────────────────────────────

def _parse_hdfc(pdf_path) -> pd.DataFrame:
    """
    Parse HDFC bank statement PDF.
    Looks for table with columns:
    Date | Narration | Chq/Ref No | Value Date | Withdrawal Amt | Deposit Amt | Balance
    """
    rows = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or len(row) < 6:
                        continue

                    # Skip header rows
                    if row[0] and ("date" in str(row[0]).lower() or
                                   "narration" in str(row[1]).lower()):
                        continue

                    try:
                        # HDFC format: Date | Narration | Ref | Value Date |
                        #              Withdrawal | Deposit | Balance
                        date_str   = str(row[0]).strip()
                        narration  = str(row[1]).strip()
                        withdrawal = str(row[4]).strip() if row[4] else ""
                        deposit    = str(row[5]).strip() if row[5] else ""

                        # Parse date — HDFC uses DD/MM/YY
                        if not date_str or date_str == "None":
                            continue
                        date = _parse_date(date_str)
                        if not date:
                            continue

                        # Only process debits (withdrawals)
                        withdrawal_clean = _clean_amount(withdrawal)
                        if withdrawal_clean and withdrawal_clean > 0:
                            rows.append({
                                "date":        date,
                                "description": narration,
                                "amount":      withdrawal_clean,
                                "type":        "debit"
                            })

                    except (IndexError, ValueError):
                        continue

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["date", "description", "amount", "type"]
    )


def _parse_sbi(pdf_path) -> pd.DataFrame:
    """
    Parse SBI bank statement PDF.
    Columns: Txn Date | Value Date | Description | Ref No | Debit | Credit | Balance
    """
    rows = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or len(row) < 5:
                        continue

                    if row[0] and ("txn date" in str(row[0]).lower() or
                                   "date" in str(row[0]).lower()):
                        continue

                    try:
                        date_str    = str(row[0]).strip()
                        description = str(row[2]).strip()
                        debit       = str(row[4]).strip() if row[4] else ""

                        date = _parse_date(date_str)
                        if not date:
                            continue

                        debit_clean = _clean_amount(debit)
                        if debit_clean and debit_clean > 0:
                            rows.append({
                                "date":        date,
                                "description": description,
                                "amount":      debit_clean,
                                "type":        "debit"
                            })

                    except (IndexError, ValueError):
                        continue

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["date", "description", "amount", "type"]
    )


def _parse_icici(pdf_path) -> pd.DataFrame:
    """
    Parse ICICI bank statement PDF.
    Columns: Date | Transaction Remarks | Amount (INR) | Dr/Cr | Balance
    """
    rows = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or len(row) < 4:
                        continue

                    if row[0] and "date" in str(row[0]).lower():
                        continue

                    try:
                        date_str    = str(row[0]).strip()
                        description = str(row[1]).strip()
                        amount_str  = str(row[2]).strip()
                        dr_cr       = str(row[3]).strip().upper()

                        date = _parse_date(date_str)
                        if not date:
                            continue

                        # ICICI marks debits as "DR"
                        if "DR" not in dr_cr:
                            continue

                        amount_clean = _clean_amount(amount_str)
                        if amount_clean and amount_clean > 0:
                            rows.append({
                                "date":        date,
                                "description": description,
                                "amount":      amount_clean,
                                "type":        "debit"
                            })

                    except (IndexError, ValueError):
                        continue

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["date", "description", "amount", "type"]
    )


# ── Date and amount helpers ───────────────────────────────────────────────────

def _parse_date(date_str: str) -> datetime.date | None:
    """
    Try multiple Indian bank date formats.
    Returns a datetime.date or None if unparseable.
    """
    formats = [
        "%d/%m/%y",    # HDFC: 15/06/25
        "%d/%m/%Y",    # 15/06/2025
        "%d-%m-%Y",    # 15-06-2025
        "%d-%m-%y",    # 15-06-25
        "%d %b %Y",    # 15 Jun 2025
        "%d %b %y",    # 15 Jun 25
        "%Y-%m-%d",    # ISO format
    ]
    clean = date_str.strip().replace("\n", " ")
    for fmt in formats:
        try:
            return datetime.datetime.strptime(clean, fmt).date()
        except ValueError:
            continue
    return None


def _clean_amount(amount_str: str) -> float | None:
    """
    Clean an amount string to float.
    Handles commas, spaces, currency symbols.
    e.g. "1,23,456.78" → 123456.78
         "Rs 450.00"   → 450.0
    """
    if not amount_str or amount_str in ("None", "-", ""):
        return None
    cleaned = re.sub(r"[^\d.]", "", amount_str)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


# ── Duplicate detection ───────────────────────────────────────────────────────

def find_duplicates(user_id: int,
                    parsed_df: pd.DataFrame) -> list[dict]:
    """
    Check parsed transactions against existing expenses.
    A duplicate is: same date + same amount (within Rs1 tolerance).
    Returns list of duplicate row dicts.
    """
    if parsed_df.empty:
        return []

    existing = load_expenses(user_id)
    if existing.empty:
        return []

    duplicates = []

    for _, row in parsed_df.iterrows():
        match = existing[
            (existing["date"].dt.date == row["date"]) &
            (abs(existing["amount_inr"] - row["amount"]) < 1.0)
        ]
        if not match.empty:
            duplicates.append({
                "date":        row["date"],
                "description": row["description"],
                "amount":      row["amount"]
            })

    return duplicates


# ── Main import UI ────────────────────────────────────────────────────────────

def show_import_page() -> None:
    st.header("📥 Import Bank Statement")
    st.caption(
        "Upload your bank statement PDF — transactions are auto-categorized "
        "and shown for review before importing."
    )

    user_id      = st.session_state["user_id"]
    all_cats     = get_all_categories(user_id)

    # ── Step 1: Bank selection + file upload ──────────────────────
    col1, col2 = st.columns(2)

    with col1:
        bank = st.selectbox(
            "Select your bank",
            ["HDFC Bank", "SBI", "ICICI Bank"],
            help="Choose the bank that issued this statement"
        )

    with col2:
        uploaded_file = st.file_uploader(
            "Upload statement PDF",
            type=["pdf"],
            help="Download from your bank's net banking portal"
        )

    if not uploaded_file:
        # Show instructions when no file uploaded
        st.divider()
        st.markdown(
            """
            <div style="
                background: rgba(14,33,160,0.2);
                border: 1px dashed rgba(177,83,215,0.4);
                border-radius: 14px;
                padding: 1.5rem 2rem;
                margin-top: 1rem;
            ">
                <div style="font-family:'Libre Baskerville',serif;
                            font-size:1rem; color:#F0F0FF;
                            margin-bottom:1rem;">
                    How to download your statement
                </div>
                <div style="font-family:Inter,sans-serif;
                            font-size:0.85rem; color:#9090B8;
                            line-height:2;">
                    <b style="color:#C8C8E8;">HDFC:</b>
                    Net Banking → Accounts → Account Statement →
                    Select period → Download PDF<br>
                    <b style="color:#C8C8E8;">SBI:</b>
                    YONO App or Net Banking → Account Statement →
                    Download as PDF<br>
                    <b style="color:#C8C8E8;">ICICI:</b>
                    Net Banking → Accounts → Statement of Account →
                    View/Download
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # ── Step 2: Parse the PDF ─────────────────────────────────────
    with st.spinner(f"Reading your {bank} statement..."):
        try:
            import tempfile, os

            # Save uploaded file to a temp path for pdfplumber
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".pdf"
            ) as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            if bank == "HDFC Bank":
                parsed_df = _parse_hdfc(tmp_path)
            elif bank == "SBI":
                parsed_df = _parse_sbi(tmp_path)
            else:
                parsed_df = _parse_icici(tmp_path)

            os.unlink(tmp_path)

        except Exception as e:
            st.error(
                f"Could not read the PDF — {str(e)}. "
                "Make sure you uploaded the correct bank's statement."
            )
            return

    if parsed_df.empty:
        st.error(
            "No transactions found in this PDF. "
            "The statement format may have changed — "
            "try downloading a fresh copy from net banking."
        )
        return

    # ── Step 3: Auto-categorize ───────────────────────────────────
    parsed_df["category"] = parsed_df["description"].apply(
        lambda d: categorize_description(d, all_cats)
    )
    parsed_df = parsed_df.sort_values("date").reset_index(drop=True)

    st.success(
        f"✅ Found **{len(parsed_df)} transactions** — "
        f"₹{parsed_df['amount'].sum():,.0f} total · "
        f"{parsed_df['date'].min()} to {parsed_df['date'].max()}"
    )

    # ── Step 4: Duplicate check ───────────────────────────────────
    duplicates = find_duplicates(user_id, parsed_df)

    skip_duplicates = False
    if duplicates:
        st.warning(
            f"⚠️ **{len(duplicates)} possible duplicate(s)** found — "
            f"these transactions appear to already exist in SpendWise."
        )

        with st.expander("View duplicates", expanded=True):
            dup_df = pd.DataFrame(duplicates)
            dup_df["date"]   = dup_df["date"].astype(str)
            dup_df["amount"] = dup_df["amount"].apply(
                lambda x: f"₹{x:,.2f}"
            )
            st.dataframe(dup_df, use_container_width=True, hide_index=True)

        col_y, col_n = st.columns(2)
        with col_y:
            skip_duplicates = st.radio(
                "How to handle duplicates?",
                ["Skip duplicates", "Import everything"],
                index=0
            ) == "Skip duplicates"

    # ── Step 5: Preview and edit ──────────────────────────────────
    st.divider()
    st.subheader("Review & edit before importing")
    st.caption(
        "Change any category using the dropdown. "
        "Uncheck rows you don't want to import."
    )

    # Store editable state in session_state
    if "import_df" not in st.session_state or \
       st.session_state.get("import_file_name") != uploaded_file.name:
        st.session_state["import_df"]        = parsed_df.copy()
        st.session_state["import_file_name"] = uploaded_file.name
        st.session_state["import_include"]   = [True] * len(parsed_df)

    edited_df = st.session_state["import_df"]
    include   = st.session_state["import_include"]

    # Group by category for cleaner display
    categories_in_data = edited_df["category"].unique().tolist()

    for cat in sorted(categories_in_data):
        cat_mask = edited_df["category"] == cat
        cat_rows = edited_df[cat_mask]

        with st.expander(
            f"**{cat}** — {len(cat_rows)} transactions · "
            f"₹{cat_rows['amount'].sum():,.0f}",
            expanded=True
        ):
            for idx in cat_rows.index:
                row      = edited_df.loc[idx]
                col_chk, col_date, col_desc, col_amt, col_cat = \
                    st.columns([0.5, 1.2, 3, 1.2, 1.8])

                with col_chk:
                    include[idx] = st.checkbox(
                        "",
                        value=include[idx],
                        key=f"inc_{idx}",
                        label_visibility="collapsed"
                    )
                with col_date:
                    st.caption(str(row["date"]))
                with col_desc:
                    st.caption(row["description"][:50])
                with col_amt:
                    st.caption(f"₹{row['amount']:,.0f}")
                with col_cat:
                    new_cat = st.selectbox(
                        "",
                        all_cats,
                        index=all_cats.index(row["category"])
                        if row["category"] in all_cats else 0,
                        key=f"cat_{idx}",
                        label_visibility="collapsed"
                    )
                    edited_df.at[idx, "category"] = new_cat

    st.session_state["import_include"] = include

    # ── Step 6: Import confirmation ───────────────────────────────
    st.divider()

    selected_count = sum(include)
    selected_df    = edited_df[include]

    # Remove duplicates if user chose to skip
    if skip_duplicates and duplicates:
        dup_keys = {
            (d["date"], round(d["amount"]))
            for d in duplicates
        }
        selected_df = selected_df[
            ~selected_df.apply(
                lambda r: (r["date"], round(r["amount"])) in dup_keys,
                axis=1
            )
        ]

    final_count  = len(selected_df)
    final_amount = selected_df["amount"].sum() if not selected_df.empty else 0

    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.markdown(
            f"<div style='font-family:Inter,sans-serif; "
            f"font-size:0.9rem; color:#C8C8E8; padding-top:8px;'>"
            f"Ready to import <b style='color:#F0F0FF'>"
            f"{final_count} transactions</b> · "
            f"<b style='color:#F375C2'>₹{final_amount:,.0f}</b> total"
            f"</div>",
            unsafe_allow_html=True
        )
    with col_btn:
        import_btn = st.button(
            "Import now",
            type="primary",
            use_container_width=True,
            disabled=final_count == 0
        )

    if import_btn:
        if selected_df.empty:
            st.error("No transactions selected to import.")
            return

        inserted = 0
        for _, row in selected_df.iterrows():
            try:
                database.add_expense(
                    user_id=user_id,
                    amount=row["amount"],
                    description=row["description"],
                    category=row["category"],
                    date=str(row["date"]),
                    currency="INR",
                    amount_inr=row["amount"]
                )
                inserted += 1
            except Exception:
                continue

        # Clear import state
        for key in ["import_df", "import_file_name", "import_include"]:
            if key in st.session_state:
                del st.session_state[key]

        st.success(
            f"🎉 **{inserted} transactions imported successfully!** "
            f"₹{final_amount:,.0f} added across "
            f"{selected_df['category'].nunique()} categories. "
            f"Go to Dashboard to see your updated spending."
        )
        st.balloons()