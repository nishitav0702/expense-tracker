import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "expense_tracker.db")


def get_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create all tables if they don't exist. Safe to call on every startup."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    UNIQUE NOT NULL,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            icon     TEXT    DEFAULT '💰',
            user_id  INTEGER REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            amount       REAL    NOT NULL CHECK(amount > 0),
            description  TEXT    DEFAULT '',
            category     TEXT    NOT NULL,
            date         TEXT    NOT NULL,
            currency     TEXT    DEFAULT 'INR',
            amount_inr   REAL    NOT NULL,
            is_recurring INTEGER DEFAULT 0,
            created_at   TEXT    DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            category      TEXT    NOT NULL,
            monthly_limit REAL    NOT NULL CHECK(monthly_limit >= 0),
            month         INTEGER NOT NULL,
            year          INTEGER NOT NULL,
            UNIQUE(user_id, category, month, year)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialised successfully.")


# ── User operations ───────────────────────────────────────────────────────────

def create_user(username: str, email: str, hashed_password: str) -> bool:
    """Insert a new user. Returns True on success, False if username/email exists."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username.strip(), email.strip().lower(), hashed_password)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()  # always closes, whether success or exception

def get_user_by_email(email: str):
    """Return a user row by email, or None if not found."""
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email.strip().lower(),)
    ).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id: int):
    """Return a user row by ID, or None if not found."""
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return user


# ── Expense operations ────────────────────────────────────────────────────────

def add_expense(user_id: int, amount: float, description: str,
                category: str, date: str, currency: str = "INR",
                amount_inr: float = None, is_recurring: int = 0) -> int:
    """Insert a new expense. Returns the new row's ID."""
    if amount_inr is None:
        amount_inr = amount
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO expenses
           (user_id, amount, description, category, date, currency, amount_inr, is_recurring)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, amount, description.strip(), category, date,
         currency, amount_inr, is_recurring)
    )
    expense_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return expense_id


def get_expenses(user_id: int, from_date: str = None,
                 to_date: str = None, categories: list = None):
    """Fetch expenses for a user with optional filters."""
    query = "SELECT * FROM expenses WHERE user_id = ?"
    params = [user_id]

    if from_date:
        query += " AND date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND date <= ?"
        params.append(to_date)
    if categories:
        placeholders = ",".join("?" * len(categories))
        query += f" AND category IN ({placeholders})"
        params.extend(categories)

    query += " ORDER BY date DESC, created_at DESC"

    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def update_expense(expense_id: int, user_id: int, amount: float,
                   description: str, category: str, date: str,
                   currency: str = "INR", amount_inr: float = None) -> bool:
    """Update an expense. user_id check prevents editing someone else's data."""
    if amount_inr is None:
        amount_inr = amount
    conn = get_connection()
    cursor = conn.execute(
        """UPDATE expenses
           SET amount=?, description=?, category=?, date=?,
               currency=?, amount_inr=?
           WHERE id=? AND user_id=?""",
        (amount, description.strip(), category, date,
         currency, amount_inr, expense_id, user_id)
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_expense(expense_id: int, user_id: int) -> bool:
    """Delete an expense. user_id check prevents deleting someone else's data."""
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id)
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ── Budget operations ─────────────────────────────────────────────────────────

def set_budget(user_id: int, category: str,
               monthly_limit: float, month: int, year: int) -> None:
    """Insert or update a budget limit for a category/month/year."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO budgets (user_id, category, monthly_limit, month, year)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(user_id, category, month, year)
           DO UPDATE SET monthly_limit = excluded.monthly_limit""",
        (user_id, category, monthly_limit, month, year)
    )
    conn.commit()
    conn.close()


def get_budgets(user_id: int, month: int, year: int) -> dict:
    """Return a dict of {category: monthly_limit} for the given month/year."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT category, monthly_limit FROM budgets WHERE user_id=? AND month=? AND year=?",
        (user_id, month, year)
    ).fetchall()
    conn.close()
    return {row["category"]: row["monthly_limit"] for row in rows}


if __name__ == "__main__":
    init_db()