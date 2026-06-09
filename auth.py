import bcrypt
import streamlit as st
import database

# These are your fixed app categories — used throughout the entire app
CATEGORIES = ["Food", "Travel", "Shopping", "Entertainment", "Health", "Utilities", "Other"]


# ── Password utilities ────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    bcrypt automatically generates a random salt and embeds it in the hash.
    This means even if two users have the same password, their hashes differ.

    Returns a string (decoded from bytes) safe to store in SQLite.
    """
    password_bytes = plain_password.encode("utf-8")   # bcrypt needs bytes, not str
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")                      # store as string in DB


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if a plain-text password matches a stored bcrypt hash.

    bcrypt.checkpw extracts the salt from the stored hash, re-hashes the
    plain password with that same salt, and compares. You never decrypt —
    bcrypt is one-way.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


# ── Session utilities ─────────────────────────────────────────────────────────

def init_session():
    """
    Set up default session_state keys if they don't exist yet.
    Call this at the very top of app.py on every rerun.

    Think of this as declaring your global variables safely.
    """
    defaults = {
        "logged_in": False,
        "user_id": None,
        "username": None,
        "email": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def login_user(user_row) -> None:
    """
    Store user info in session_state after successful login.
    user_row is a sqlite3.Row object from database.get_user_by_email().
    """
    st.session_state["logged_in"] = True
    st.session_state["user_id"]   = user_row["id"]
    st.session_state["username"]  = user_row["username"]
    st.session_state["email"]     = user_row["email"]


def logout_user() -> None:
    """
    Clear all session_state keys and force a rerun.
    This takes the user back to the login page immediately.
    """
    for key in ["logged_in", "user_id", "username", "email"]:
        st.session_state[key] = None
    st.session_state["logged_in"] = False
    st.rerun()


def is_logged_in() -> bool:
    """Convenience check used in app.py to decide which page to show."""
    return st.session_state.get("logged_in", False)


# ── Registration ──────────────────────────────────────────────────────────────

def show_register_form() -> None:
    """
    Render the registration form and handle submission.
    Uses st.form so the whole form submits at once — no partial reruns
    while the user is still typing.
    """
    st.title("Create your SpendWise account")

    with st.form("register_form"):
        username = st.text_input("Username")
        email    = st.text_input("Email address")
        password = st.text_input("Password", type="password",
                                 help="Minimum 8 characters")
        confirm  = st.text_input("Confirm password", type="password")
        submit   = st.form_submit_button("Register")

    if submit:
        # ── Validation ───────────────────────────────────────────
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

        # ── Create user ──────────────────────────────────────────
        hashed = hash_password(password)
        success = database.create_user(username, email, hashed)

        if success:
            st.success("Account created! Please log in.")
        else:
            st.error("That username or email is already registered.")


# ── Login ─────────────────────────────────────────────────────────────────────

def show_login_form() -> None:
    """
    Render the login form and handle submission.
    On success, calls login_user() to populate session_state,
    then st.rerun() to immediately show the dashboard.
    """
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
            # Don't say "email not found" — that leaks info about who's registered
            st.error("Invalid email or password.")
            return

        if not verify_password(password, user["password"]):
            st.error("Invalid email or password.")
            return

        # Credentials are valid — load into session
        login_user(user)
        st.rerun()   # triggers a full rerun — app.py now sees logged_in=True


# ── Settings page ─────────────────────────────────────────────────────────────

def show_settings_page() -> None:
    """
    Let the user set monthly budget limits per category.
    Reads existing budgets from DB and pre-fills the inputs.
    """
    import datetime

    st.header("⚙️ Settings")
    st.subheader("Monthly budgets")
    st.caption("Set how much you want to spend per category this month.")

    user_id = st.session_state["user_id"]
    now     = datetime.datetime.now()

    # Load whatever budgets already exist for this month
    existing = database.get_budgets(user_id, now.month, now.year)

    with st.form("budget_form"):
        budgets = {}
        for category in CATEGORIES:
            current_limit = existing.get(category, 0.0)
            budgets[category] = st.number_input(
                f"{category} (₹)",
                min_value=0.0,
                value=float(current_limit),
                step=100.0,
                key=f"budget_{category}"
            )
        save = st.form_submit_button("Save budgets")

    if save:
        for category, limit in budgets.items():
            database.set_budget(user_id, category, limit, now.month, now.year)
        st.success("Budgets saved successfully!")
