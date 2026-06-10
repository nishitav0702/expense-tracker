import os
import datetime
import numpy as np
import pandas as pd
import joblib
import streamlit as st
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from scipy import stats
import database
from expenses import load_expenses
from auth import CATEGORIES

# Where model files are saved — one per user
MODEL_DIR = os.path.dirname(__file__)


def _model_path(user_id: int) -> str:
    return os.path.join(MODEL_DIR, f"model_user_{user_id}.pkl")


# ── Data guard ────────────────────────────────────────────────────────────────

def has_enough_data(user_id: int, min_expenses: int = 10) -> bool:
    """
    ML features are meaningless on 2-3 rows of data.
    This guard prevents the app from showing garbage predictions
    to new users — a real-world ML engineering consideration.
    """
    all_expenses = load_expenses(user_id)
    return len(all_expenses) >= min_expenses


# ── Feature engineering ───────────────────────────────────────────────────────

def engineer_features(user_id: int, month: int, year: int) -> pd.DataFrame:
    """
    Convert raw expense rows into a feature matrix.
    One row per category.

    This is the most important function in the ML pipeline.
    Raw data (individual transactions) is useless to a model.
    Derived features (velocity, % used, days remaining) are meaningful.

    Returns a DataFrame with columns:
    category | spent | budget | pct_used | daily_velocity |
    days_elapsed | days_remaining | projected_total
    """
    today = datetime.date.today()

    # Days in month
    if month == 12:
        days_in_month = 31
    else:
        last_day = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        days_in_month = last_day.day

    # Days elapsed so far (minimum 1 to avoid division by zero)
    if month == today.month and year == today.year:
        days_elapsed = max(today.day, 1)
    else:
        days_elapsed = days_in_month  # completed month

    days_remaining = max(days_in_month - days_elapsed, 0)

    # Load expenses for this month
    from_date = datetime.date(year, month, 1)
    to_date   = (
        today if (month == today.month and year == today.year)
        else datetime.date(year, month, days_in_month)
    )
    df = load_expenses(user_id, from_date=from_date, to_date=to_date)

    # Load budgets for this month
    budgets = database.get_budgets(user_id, month, year)

    rows = []
    for category in CATEGORIES:
        # Total spent in this category this month
        if df.empty:
            spent = 0.0
        else:
            cat_df = df[df["category"] == category]
            spent  = float(cat_df["amount_inr"].sum())

        budget = float(budgets.get(category, 0.0))

        # Avoid division by zero throughout
        pct_used       = (spent / budget * 100) if budget > 0 else 0.0
        daily_velocity = spent / days_elapsed
        projected      = daily_velocity * days_in_month

        rows.append({
            "category":       category,
            "spent":          spent,
            "budget":         budget,
            "pct_used":       pct_used,
            "daily_velocity": daily_velocity,
            "days_elapsed":   days_elapsed,
            "days_remaining": days_remaining,
            "projected_total": projected,
        })

    return pd.DataFrame(rows)


def _make_label(pct_used: float) -> int:
    """
    Convert percentage used into a risk label.
    0 = Safe, 1 = Warning, 2 = Danger

    These thresholds become the ground truth that trains
    the Logistic Regression model. The model then learns
    to predict these labels from the other features,
    allowing it to generalise beyond just % used.
    """
    if pct_used >= 85:
        return 2  # Danger
    elif pct_used >= 60:
        return 1  # Warning
    else:
        return 0  # Safe


# ── Model training ────────────────────────────────────────────────────────────

def train_risk_model(user_id: int) -> Pipeline | None:
    """
    Train a Logistic Regression risk classifier on the user's
    historical data (all months except the current one).

    Why Pipeline?
    Pipeline chains StandardScaler + LogisticRegression into one object.
    StandardScaler normalises features to the same scale — important
    because pct_used (0-100) and daily_velocity (0-900) are on very
    different scales. Without scaling, the model weights them incorrectly.

    Returns the trained Pipeline, or None if not enough history.
    """
    today = datetime.date.today()
    all_rows = []

    # Collect features from past months (up to 6 months back)
    for offset in range(1, 7):
        month = today.month - offset
        year  = today.year
        if month <= 0:
            month += 12
            year  -= 1

        features = engineer_features(user_id, month, year)
        if features.empty:
            continue

        features["label"] = features["pct_used"].apply(_make_label)
        all_rows.append(features)

    if not all_rows:
        return None

    combined = pd.concat(all_rows, ignore_index=True)

    # Need at least 2 different labels to train a classifier
    if combined["label"].nunique() < 2:
        return None

    feature_cols = ["pct_used", "daily_velocity", "days_elapsed",
                    "days_remaining", "projected_total"]
    X = combined[feature_cols].values
    y = combined["label"].values

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    LogisticRegression(max_iter=1000, random_state=42))
    ])
    model.fit(X, y)

    # Save to disk so we don't retrain on every page load
    joblib.dump(model, _model_path(user_id))
    return model


def _load_or_train(user_id: int) -> Pipeline | None:
    """
    Load saved model from disk if it exists, otherwise train a new one.
    This means the model only retrains when explicitly called,
    not on every Streamlit rerun.
    """
    path = _model_path(user_id)
    if os.path.exists(path):
        return joblib.load(path)
    return train_risk_model(user_id)


# ── Risk classification ───────────────────────────────────────────────────────

def predict_risk(user_id: int) -> pd.DataFrame:
    """
    Predict risk label for each category for the current month.

    Returns a DataFrame with columns:
    category | spent | budget | pct_used | projected_total |
    risk_label | risk_score
    """
    today    = datetime.date.today()
    features = engineer_features(user_id, today.month, today.year)

    feature_cols = ["pct_used", "daily_velocity", "days_elapsed",
                    "days_remaining", "projected_total"]
    X = features[feature_cols].values

    model = _load_or_train(user_id)

    label_map = {0: "Safe", 1: "Warning", 2: "Danger"}

    if model is not None:
        try:
            predictions  = model.predict(X)
            probabilities = model.predict_proba(X)
            features["risk_label"] = [label_map[p] for p in predictions]
            # Confidence score for the predicted class
            features["risk_score"] = [
                round(probabilities[i][predictions[i]] * 100, 1)
                for i in range(len(predictions))
            ]
        except Exception:
            # Fallback to rule-based if model fails for any reason
            features["risk_label"] = features["pct_used"].apply(
                lambda x: label_map[_make_label(x)]
            )
            features["risk_score"] = 100.0
    else:
        # No historical data — use rules directly
        features["risk_label"] = features["pct_used"].apply(
            lambda x: label_map[_make_label(x)]
        )
        features["risk_score"] = 100.0

    return features


# ── Spend forecast ────────────────────────────────────────────────────────────

def forecast_month_spend(user_id: int) -> dict:
    """
    Use Linear Regression to predict end-of-month total per category.

    How it works:
    X = day numbers (1, 2, 3 ... today)
    y = cumulative spend up to that day

    The model fits a line through these points and extends it to
    day 30/31. The y value at day 30 is the forecast.

    Returns dict: {category: predicted_total}
    """
    today = datetime.date.today()
    from_date = today.replace(day=1)
    df = load_expenses(user_id, from_date=from_date, to_date=today)

    # Days in this month
    if today.month == 12:
        days_in_month = 31
    else:
        days_in_month = (
            datetime.date(today.year, today.month + 1, 1)
            - datetime.timedelta(days=1)
        ).day

    forecasts = {}

    for category in CATEGORIES:
        if df.empty:
            forecasts[category] = 0.0
            continue

        cat_df = df[df["category"] == category].copy()

        if cat_df.empty or len(cat_df) < 2:
            # Not enough data points for regression — use simple projection
            total_so_far = float(cat_df["amount_inr"].sum()) if not cat_df.empty else 0.0
            daily_avg    = total_so_far / max(today.day, 1)
            forecasts[category] = round(daily_avg * days_in_month, 2)
            continue

        # Build daily cumulative spend
        cat_df["date"] = pd.to_datetime(cat_df["date"])
        daily = (
            cat_df.groupby(cat_df["date"].dt.day)["amount_inr"]
            .sum()
        )

        # X = day number, y = cumulative sum up to that day
        days   = np.array(daily.index).reshape(-1, 1)
        cumsum = np.cumsum(daily.values)

        model = LinearRegression()
        model.fit(days, cumsum)

        # Predict at end of month
        predicted = model.predict([[days_in_month]])[0]
        forecasts[category] = round(max(predicted, 0), 2)  # can't be negative

    return forecasts


# ── Anomaly detection ─────────────────────────────────────────────────────────

def check_anomaly(user_id: int, amount: float,
                  category: str) -> tuple[bool, float]:
    """
    Check if a new expense amount is unusually high for this category.
    Uses z-score: how many standard deviations from the mean is this?

    z > 2.0 means the value is in the top ~2.3% — flagged as unusual.

    Returns (is_anomaly: bool, z_score: float)
    """
    all_expenses = load_expenses(user_id, categories=[category])

    if len(all_expenses) < 5:
        # Not enough history to judge — don't flag anything
        return False, 0.0

    amounts = all_expenses["amount_inr"].values

    if amounts.std() == 0:
        return False, 0.0

    z = float(stats.zscore(np.append(amounts, amount))[-1])
    is_anomaly = abs(z) > 2.0

    return is_anomaly, round(z, 2)


# ── Blind spot detection ──────────────────────────────────────────────────────

def find_blind_spot(user_id: int) -> str | None:
    """
    Find the category that has exceeded its budget most often
    across all historical months.

    Pure pandas — no ML needed here.
    Just counts how many months each category went over budget.

    Returns the worst category name, or None if not enough data.
    """
    today       = datetime.date.today()
    overspend_count = {cat: 0 for cat in CATEGORIES}

    for offset in range(1, 7):
        month = today.month - offset
        year  = today.year
        if month <= 0:
            month += 12
            year  -= 1

        budgets  = database.get_budgets(user_id, month, year)
        features = engineer_features(user_id, month, year)

        if features.empty or not budgets:
            continue

        for _, row in features.iterrows():
            cat    = row["category"]
            limit  = budgets.get(cat, 0)
            if limit > 0 and row["spent"] > limit:
                overspend_count[cat] += 1

    # Return category with most overspends, if any happened
    max_count = max(overspend_count.values())
    if max_count == 0:
        return None

    return max(overspend_count, key=lambda c: overspend_count[c])


# ── Streamlit UI ──────────────────────────────────────────────────────────────

def show_ml_insights_page() -> None:
    """
    Render the ML Insights page.
    Shows risk labels, forecasts, and blind spot — all in one place.
    """
    st.header("🤖 ML Insights")

    user_id = st.session_state["user_id"]

    # ── Data guard ────────────────────────────────────────────────
    if not has_enough_data(user_id):
        all_exp = load_expenses(user_id)
        count   = len(all_exp)
        st.info(
            f"You have **{count} expense{'s' if count != 1 else ''}** logged. "
            f"ML insights activate after **10 expenses**. "
            f"Add {10 - count} more to unlock this page."
        )
        st.progress(count / 10)
        return

    # ── Retrain button ────────────────────────────────────────────
    col_title, col_btn = st.columns([4, 1])
    with col_btn:
        if st.button("🔄 Retrain model", help="Retrain on your latest data"):
            train_risk_model(user_id)
            st.success("Model retrained!")
            st.rerun()

    # ── Risk labels ───────────────────────────────────────────────
    st.subheader("Spending risk by category")
    st.caption(
        "Predicted by a Logistic Regression model trained on your "
        "historical spending patterns."
    )

    risk_df = predict_risk(user_id)

    RISK_ICONS = {"Safe": "🟢", "Warning": "🟠", "Danger": "🔴"}
    RISK_COLOURS = {"Safe": "normal", "Warning": "inverse", "Danger": "off"}

    # Display in a 3-column grid
    cols = st.columns(3)
    for i, (_, row) in enumerate(risk_df.iterrows()):
        with cols[i % 3]:
            icon  = RISK_ICONS.get(row["risk_label"], "⚪")
            label = row["risk_label"]
            st.metric(
                label=f"{icon} {row['category']}",
                value=label,
                delta=f"₹{row['spent']:,.0f} spent · {row['pct_used']:.0f}% of budget",
                delta_color=RISK_COLOURS.get(label, "off")
            )

    st.divider()

    # ── Spend forecast ────────────────────────────────────────────
    st.subheader("Month-end forecast")
    st.caption(
        "Linear Regression on your daily spend trend "
        "this month — predicts where each category will land."
    )

    forecasts = forecast_month_spend(user_id)
    today     = datetime.date.today()
    budgets   = database.get_budgets(user_id, today.month, today.year)

    cols = st.columns(3)
    for i, category in enumerate(CATEGORIES):
        predicted = forecasts.get(category, 0.0)
        limit     = budgets.get(category, 0.0)

        with cols[i % 3]:
            if limit > 0:
                overshoot = predicted - limit
                delta_str = (
                    f"+₹{overshoot:,.0f} over budget"
                    if overshoot > 0
                    else f"₹{abs(overshoot):,.0f} under budget"
                )
                delta_col = "inverse" if overshoot > 0 else "normal"
            else:
                delta_str = "No budget set"
                delta_col = "off"

            st.metric(
                label=category,
                value=f"₹{predicted:,.0f}",
                delta=delta_str,
                delta_color=delta_col
            )

    st.divider()

   # ── Blind spot ────────────────────────────────────────────────
    st.subheader("Your spending blind spot")

    blind_spot = find_blind_spot(user_id)

    # Also check current month overbudget categories
    today    = datetime.date.today()
    budgets  = database.get_budgets(user_id, today.month, today.year)
    risk_df  = predict_risk(user_id)

    current_overbudget = risk_df[
        (risk_df["risk_label"] == "Danger") & (risk_df["budget"] > 0)
    ]["category"].tolist()

    if blind_spot:
        st.error(
            f"📍 **{blind_spot}** is your recurring blind spot — "
            f"you've exceeded this budget more consistently than any "
            f"other category over the past 6 months."
        )
    elif current_overbudget:
        cats = ", ".join(f"**{c}**" for c in current_overbudget)
        st.warning(
            f"⚠️ No recurring pattern yet (not enough history), but "
            f"{cats} {'is' if len(current_overbudget) == 1 else 'are'} "
            f"already over budget this month — worth watching."
        )
    else:
        st.success(
            "No recurring blind spots detected and you're within "
            "budget across all categories this month. Great work!"
        )