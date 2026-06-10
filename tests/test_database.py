import sys
import os
import pytest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import database

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
database.DB_PATH = _tmp.name


@pytest.fixture(autouse=True)
def fresh_db():
    """Drop and recreate all tables before every test."""
    conn = database.get_connection()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("DROP TABLE IF EXISTS budgets")
    conn.execute("DROP TABLE IF EXISTS expenses")
    conn.execute("DROP TABLE IF EXISTS categories")
    conn.execute("DROP TABLE IF EXISTS users")
    conn.commit()
    conn.close()
    database.init_db()
    yield


def test_create_and_fetch_user():
    success = database.create_user("testuser", "test@example.com", "hashed_pw")
    assert success is True
    user = database.get_user_by_email("test@example.com")
    assert user is not None
    assert user["username"] == "testuser"


def test_duplicate_user_returns_false():
    database.create_user("testuser", "test@example.com", "hashed_pw")
    duplicate = database.create_user("testuser", "test@example.com", "hashed_pw")
    assert duplicate is False


def test_add_and_fetch_expense():
    database.create_user("u1", "u1@example.com", "pw")
    user = database.get_user_by_email("u1@example.com")
    uid = user["id"]

    database.add_expense(uid, 250.0, "Lunch", "Food", "2025-06-01")
    expenses = database.get_expenses(uid)
    assert len(expenses) == 1
    assert expenses[0]["amount"] == 250.0
    assert expenses[0]["category"] == "Food"


def test_update_expense():
    database.create_user("u2", "u2@example.com", "pw")
    user = database.get_user_by_email("u2@example.com")
    uid = user["id"]

    eid = database.add_expense(uid, 100.0, "Coffee", "Food", "2025-06-01")
    result = database.update_expense(eid, uid, 120.0, "Coffee+snack", "Food", "2025-06-01")
    assert result is True

    expenses = database.get_expenses(uid)
    assert expenses[0]["amount"] == 120.0


def test_delete_expense():
    database.create_user("u3", "u3@example.com", "pw")
    user = database.get_user_by_email("u3@example.com")
    uid = user["id"]

    eid = database.add_expense(uid, 500.0, "Uber", "Travel", "2025-06-01")
    deleted = database.delete_expense(eid, uid)
    assert deleted is True
    assert len(database.get_expenses(uid)) == 0


def test_filter_by_category():
    database.create_user("u4", "u4@example.com", "pw")
    user = database.get_user_by_email("u4@example.com")
    uid = user["id"]

    database.add_expense(uid, 200.0, "Zomato", "Food", "2025-06-01")
    database.add_expense(uid, 150.0, "Ola", "Travel", "2025-06-02")

    food_only = database.get_expenses(uid, categories=["Food"])
    assert len(food_only) == 1
    assert food_only[0]["category"] == "Food"


def test_set_and_get_budget():
    database.create_user("u5", "u5@example.com", "pw")
    user = database.get_user_by_email("u5@example.com")
    uid = user["id"]

    database.set_budget(uid, "Food", 5000.0, 6, 2025)
    budgets = database.get_budgets(uid, 6, 2025)
    assert budgets["Food"] == 5000.0

def test_password_hash_and_verify():
    """Passwords should hash and verify correctly."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from auth import hash_password, verify_password

    hashed = hash_password("mysecretpassword")

    # Hash should not equal the original
    assert hashed != "mysecretpassword"

    # Correct password should verify
    assert verify_password("mysecretpassword", hashed) is True

    # Wrong password should not verify
    assert verify_password("wrongpassword", hashed) is False


def test_budget_persists_across_calls():
    """Setting a budget and reading it back should return the same value."""
    database.create_user("u6", "u6@example.com", "pw")
    user = database.get_user_by_email("u6@example.com")
    uid = user["id"]

    database.set_budget(uid, "Travel", 3000.0, 6, 2025)
    database.set_budget(uid, "Food", 5000.0, 6, 2025)

    budgets = database.get_budgets(uid, 6, 2025)
    assert budgets["Travel"] == 3000.0
    assert budgets["Food"] == 5000.0


def test_budget_update_overwrites():
    """Updating a budget should overwrite, not duplicate."""
    database.create_user("u7", "u7@example.com", "pw")
    user = database.get_user_by_email("u7@example.com")
    uid = user["id"]

    database.set_budget(uid, "Food", 2000.0, 6, 2025)
    database.set_budget(uid, "Food", 4500.0, 6, 2025)  # update same category

    budgets = database.get_budgets(uid, 6, 2025)
    assert budgets["Food"] == 4500.0  # should be the new value, not old

def test_expense_date_filter():
    """Only expenses within date range should be returned."""
    database.create_user("u8", "u8@example.com", "pw")
    user = database.get_user_by_email("u8@example.com")
    uid = user["id"]

    database.add_expense(uid, 100.0, "Jan expense", "Food", "2025-01-15")
    database.add_expense(uid, 200.0, "Jun expense", "Food", "2025-06-15")

    results = database.get_expenses(uid, from_date="2025-06-01", to_date="2025-06-30")
    assert len(results) == 1
    assert results[0]["description"] == "Jun expense"


def test_expense_multi_category_filter():
    """Filtering by multiple categories should return only those."""
    database.create_user("u9", "u9@example.com", "pw")
    user = database.get_user_by_email("u9@example.com")
    uid = user["id"]

    database.add_expense(uid, 100.0, "Food item",    "Food",    "2025-06-01")
    database.add_expense(uid, 150.0, "Travel item",  "Travel",  "2025-06-01")
    database.add_expense(uid, 200.0, "Health item",  "Health",  "2025-06-01")

    results = database.get_expenses(uid, categories=["Food", "Travel"])
    assert len(results) == 2
    cats = [r["category"] for r in results]
    assert "Health" not in cats


def test_update_nonexistent_expense_returns_false():
    """Updating an expense that doesn't exist should return False."""
    database.create_user("u10", "u10@example.com", "pw")
    user = database.get_user_by_email("u10@example.com")
    uid = user["id"]

    result = database.update_expense(99999, uid, 100.0, "ghost", "Food", "2025-06-01")
    assert result is False


def test_delete_other_users_expense_returns_false():
    """A user should not be able to delete another user's expense."""
    database.create_user("u11", "u11@example.com", "pw")
    database.create_user("u12", "u12@example.com", "pw")
    user1 = database.get_user_by_email("u11@example.com")
    user2 = database.get_user_by_email("u12@example.com")

    # user1 adds an expense
    eid = database.add_expense(user1["id"], 300.0, "Mine", "Food", "2025-06-01")

    # user2 tries to delete it — should fail
    result = database.delete_expense(eid, user2["id"])
    assert result is False

    # expense should still exist
    expenses = database.get_expenses(user1["id"])
    assert len(expenses) == 1


def test_budgets_multiple_categories():
    """Multiple category budgets should all be stored and retrieved."""
    database.create_user("u13", "u13@example.com", "pw")
    user = database.get_user_by_email("u13@example.com")
    uid = user["id"]

    categories = ["Food", "Travel", "Shopping", "Health"]
    limits     = [5000.0, 3000.0, 4000.0, 1500.0]

    for cat, limit in zip(categories, limits):
        database.set_budget(uid, cat, limit, 6, 2025)

    budgets = database.get_budgets(uid, 6, 2025)

    for cat, limit in zip(categories, limits):
        assert budgets[cat] == limit


def test_expenses_sorted_most_recent_first():
    """get_expenses should return newest expenses first."""
    database.create_user("u14", "u14@example.com", "pw")
    user = database.get_user_by_email("u14@example.com")
    uid = user["id"]

    database.add_expense(uid, 100.0, "Old", "Food", "2025-01-01")
    database.add_expense(uid, 200.0, "New", "Food", "2025-06-15")

    expenses = database.get_expenses(uid)
    assert expenses[0]["description"] == "New"
    assert expenses[1]["description"] == "Old"

def test_has_enough_data_false_when_empty():
    """ML guard should return False when user has no expenses."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from ml_insights import has_enough_data

    database.create_user("u15", "u15@example.com", "pw")
    user = database.get_user_by_email("u15@example.com")
    uid  = user["id"]

    assert has_enough_data(uid) is False


def test_has_enough_data_true_after_ten():
    """ML guard should return True when user has 10+ expenses."""
    from ml_insights import has_enough_data

    database.create_user("u16", "u16@example.com", "pw")
    user = database.get_user_by_email("u16@example.com")
    uid  = user["id"]

    for i in range(10):
        database.add_expense(uid, 100.0, f"exp{i}", "Food", "2025-06-01")

    assert has_enough_data(uid) is True


def test_anomaly_not_flagged_with_little_history():
    """Anomaly check should not flag when fewer than 5 expenses exist."""
    from ml_insights import check_anomaly

    database.create_user("u17", "u17@example.com", "pw")
    user = database.get_user_by_email("u17@example.com")
    uid  = user["id"]

    # Only 3 expenses — below the 5 minimum for anomaly detection
    for i in range(3):
        database.add_expense(uid, 100.0, f"exp{i}", "Food", "2025-06-01")

    is_anomaly, z = check_anomaly(uid, 500.0, "Food")
    assert is_anomaly is False


def test_anomaly_flagged_for_extreme_amount():
    """A very large expense should be flagged as an anomaly."""
    from ml_insights import check_anomaly

    database.create_user("u18", "u18@example.com", "pw")
    user = database.get_user_by_email("u18@example.com")
    uid  = user["id"]

    # Normal expenses around ₹100
    for i in range(10):
        database.add_expense(uid, 100.0 + i, f"normal{i}", "Food", "2025-06-01")

    # ₹50000 should be flagged as extreme
    is_anomaly, z = check_anomaly(uid, 50000.0, "Food")
    assert is_anomaly is True
    assert z > 2.0

def test_convert_inr_to_inr():
    """INR to INR conversion should return the same amount."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    # Mock session_state so api_client doesn't crash outside Streamlit
    import unittest.mock as mock
    with mock.patch("streamlit.session_state", {}):
        from api_client import convert_to_inr
        amount, fallback = convert_to_inr(500.0, "INR")
        assert amount == 500.0


def test_fallback_rates_cover_all_currencies():
    """Every supported currency should have a fallback rate."""
    from api_client import CURRENCIES, FALLBACK_RATES
    for currency in CURRENCIES:
        assert currency in FALLBACK_RATES, f"{currency} missing from FALLBACK_RATES"


def test_email_skips_without_credentials(monkeypatch):
    """Email send should return False gracefully when no credentials set."""
    import email_alerts
    monkeypatch.setattr(email_alerts, "GMAIL_ADDRESS", "")
    monkeypatch.setattr(email_alerts, "GMAIL_APP_PASSWORD", "")

    result = email_alerts.send_budget_exceeded_email(
        to_email="test@example.com",
        username="testuser",
        category="Food",
        spent=6000.0,
        budget=5000.0
    )
    assert result is False
