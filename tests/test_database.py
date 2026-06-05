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