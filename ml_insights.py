import os
import datetime
import numpy as np
import pandas as pd
import joblib
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from scipy import stats
import database
from expenses import load_expenses
from auth import CATEGORIES

MODEL_DIR = os.path.dirname(__file__)

COLOUR_MAP = {
    "Food":          "#FF6B6B",
    "Travel":        "#4ECDC4",
    "Shopping":      "#45B7D1",
    "Entertainment": "#96CEB4",
    "Health":        "#FFEAA7",
    "Utilities":     "#DDA0DD",
    "Other":         "#B0B0B0",
}


def _model_path(user_id: int) -> str:
    return os.path.join(MODEL_DIR, f"model_user_{user_id}.pkl")


# ── Data guard ────────────────────────────────────────────────────────────────

def has_enough_data(user_id: int, min_expenses: int = 10) -> bool:
    all_expenses = load_expenses(user_id)
    return len(all_expenses) >= min_expenses


# ── Feature engineering ───────────────────────────────────────────────────────

def engineer_features(user_id: int, month: int, year: int) -> pd.DataFrame:
    today = datetime.date.today()

    if month == 12:
        days_in_month = 31
    else:
        last_day      = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        days_in_month = last_day.day

    if month == today.month and year == today.year:
        days_elapsed = max(today.day, 1)
    else:
        days_elapsed = days_in_month

    days_remaining = max(days_in_month - days_elapsed, 0)

    from_date = datetime.date(year, month, 1)
    to_date   = (
        today if (month == today.month and year == today.year)
        else datetime.date(year, month, days_in_month)
    )

    df      = load_expenses(user_id, from_date=from_date, to_date=to_date)
    budgets = database.get_budgets(user_id, month, year)

    rows = []
    for category in CATEGORIES:
        if df.empty:
            spent = 0.0
        else:
            cat_df = df[df["category"] == category]
            spent  = float(cat_df["amount_inr"].sum())

        budget         = float(budgets.get(category, 0.0))
        pct_used       = (spent / budget * 100) if budget > 0 else 0.0
        daily_velocity = spent / days_elapsed
        projected      = daily_velocity * days_in_month

        rows.append({
            "category":        category,
            "spent":           spent,
            "budget":          budget,
            "pct_used":        pct_used,
            "daily_velocity":  daily_velocity,
            "days_elapsed":    days_elapsed,
            "days_remaining":  days_remaining,
            "projected_total": projected,
        })

    return pd.DataFrame(rows)


def _make_label(pct_used: float) -> int:
    if pct_used >= 85:
        return 2
    elif pct_used >= 60:
        return 1
    else:
        return 0


# ── Model training ────────────────────────────────────────────────────────────

def train_risk_model(user_id: int):
    today    = datetime.date.today()
    all_rows = []

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
    joblib.dump(model, _model_path(user_id))
    return model


def _load_or_train(user_id: int):
    path = _model_path(user_id)
    if os.path.exists(path):
        return joblib.load(path)
    return train_risk_model(user_id)


# ── Risk classification ───────────────────────────────────────────────────────

def predict_risk(user_id: int) -> pd.DataFrame:
    today    = datetime.date.today()
    features = engineer_features(user_id, today.month, today.year)

    feature_cols = ["pct_used", "daily_velocity", "days_elapsed",
                    "days_remaining", "projected_total"]
    X = features[feature_cols].values

    model     = _load_or_train(user_id)
    label_map = {0: "Safe", 1: "Warning", 2: "Danger"}

    if model is not None:
        try:
            predictions   = model.predict(X)
            probabilities = model.predict_proba(X)
            features["risk_label"] = [label_map[p] for p in predictions]
            features["risk_score"] = [
                round(probabilities[i][predictions[i]] * 100, 1)
                for i in range(len(predictions))
            ]
        except Exception:
            features["risk_label"] = features["pct_used"].apply(
                lambda x: label_map[_make_label(x)]
            )
            features["risk_score"] = 100.0
    else:
        features["risk_label"] = features["pct_used"].apply(
            lambda x: label_map[_make_label(x)]
        )
        features["risk_score"] = 100.0

    return features


# ── Spend forecast ────────────────────────────────────────────────────────────

def forecast_month_spend(user_id: int) -> dict:
    today     = datetime.date.today()
    from_date = today.replace(day=1)
    df        = load_expenses(user_id, from_date=from_date, to_date=today)

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
            total_so_far = float(cat_df["amount_inr"].sum()) if not cat_df.empty else 0.0
            daily_avg    = total_so_far / max(today.day, 1)
            forecasts[category] = round(daily_avg * days_in_month, 2)
            continue

        cat_df["date"] = pd.to_datetime(cat_df["date"])
        daily  = cat_df.groupby(cat_df["date"].dt.day)["amount_inr"].sum()
        days   = np.array(daily.index).reshape(-1, 1)
        cumsum = np.cumsum(daily.values)

        model = LinearRegression()
        model.fit(days, cumsum)

        predicted = model.predict([[days_in_month]])[0]
        forecasts[category] = round(max(predicted, 0), 2)

    return forecasts


# ── Anomaly detection ─────────────────────────────────────────────────────────

def check_anomaly(user_id: int, amount: float,
                  category: str) -> tuple[bool, float]:
    all_expenses = load_expenses(user_id, categories=[category])

    if len(all_expenses) < 5:
        return False, 0.0

    amounts = all_expenses["amount_inr"].values

    if amounts.std() == 0:
        return False, 0.0

    z          = float(stats.zscore(np.append(amounts, amount))[-1])
    is_anomaly = abs(z) > 2.0
    return is_anomaly, round(z, 2)


# ── Blind spot detection ──────────────────────────────────────────────────────

def find_blind_spot(user_id: int) -> dict:
    today           = datetime.date.today()
    overspend_count = {cat: 0 for cat in CATEGORIES}
    monthly_summary = []

    for offset in range(0, 6):
        month = today.month - offset
        year  = today.year
        if month <= 0:
            month += 12
            year  -= 1

        budgets  = database.get_budgets(user_id, month, year)
        features = engineer_features(user_id, month, year)

        if features.empty or not budgets:
            continue

        month_label = datetime.date(year, month, 1).strftime("%b %Y")

        for _, row in features.iterrows():
            cat   = row["category"]
            limit = budgets.get(cat, 0)
            if limit > 0 and row["spent"] > limit:
                overspend_count[cat] += 1
                monthly_summary.append({
                    "month":    month_label,
                    "category": cat,
                    "spent":    row["spent"],
                    "budget":   limit,
                    "over_by":  row["spent"] - limit
                })

    max_count = max(overspend_count.values())
    worst     = (
        max(overspend_count, key=lambda c: overspend_count[c])
        if max_count > 0 else None
    )

    return {
        "worst_category":   worst,
        "overspend_counts": overspend_count,
        "monthly_summary":  monthly_summary,
        "max_count":        max_count
    }


# ── Spending trend charts ─────────────────────────────────────────────────────

def _show_spending_trends(user_id: int) -> None:
    st.subheader("📈 Spending trends")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        view_mode = st.radio(
            "View by",
            ["Weekly", "Monthly"],
            horizontal=True
        )

    with col2:
        selected_cats = st.multiselect(
            "Categories",
            CATEGORIES,
            default=["Food", "Travel", "Utilities"],
            help="Select one or more categories to compare"
        )

    with col3:
        show_budget = st.checkbox("Show budget line", value=True)

    if not selected_cats:
        st.info("Select at least one category to view trends.")
        return

    today     = datetime.date.today()
    from_date = datetime.date(
        today.year if today.month > 2 else today.year - 1,
        today.month - 2 if today.month > 2 else today.month + 10,
        1
    )

    df = load_expenses(user_id, from_date=from_date, to_date=today)

    if df.empty:
        st.info("No data available for the selected period.")
        return

    df["date"] = pd.to_datetime(df["date"])
    df = df[df["category"].isin(selected_cats)]

    if df.empty:
        st.info("No data for selected categories.")
        return

    # ── Build chart data — sorted chronologically ─────────────────
    if view_mode == "Weekly":
        df["week_period"] = df["date"].dt.to_period("W")
        df["week_label"]  = df["date"].dt.to_period("W").apply(
            lambda r: r.start_time.strftime("%d %b")
        )
        grouped = (
            df.groupby(["week_period", "week_label", "category"])["amount_inr"]
            .sum()
            .reset_index()
        )
        grouped = grouped.sort_values("week_period")
        grouped = grouped.drop(columns=["week_period"])
        grouped.columns = ["Period", "Category", "Amount"]
        x_label = "Week starting"

    else:
        df["month_period"] = df["date"].dt.to_period("M")
        df["month_label"]  = df["date"].dt.to_period("M").apply(
            lambda r: r.start_time.strftime("%b %Y")
        )
        grouped = (
            df.groupby(["month_period", "month_label", "category"])["amount_inr"]
            .sum()
            .reset_index()
        )
        grouped = grouped.sort_values("month_period")
        grouped = grouped.drop(columns=["month_period"])
        grouped.columns = ["Period", "Category", "Amount"]
        x_label = "Month"

    # ── Grouped bar chart ─────────────────────────────────────────
    fig = px.bar(
        grouped,
        x="Period",
        y="Amount",
        color="Category",
        barmode="group",
        color_discrete_map=COLOUR_MAP,
        labels={"Amount": "Amount (Rs)", "Period": x_label},
        height=420,
    )

    # ── Budget lines ──────────────────────────────────────────────
    if show_budget:
        budgets = database.get_budgets(user_id, today.month, today.year)
        periods = grouped["Period"].unique().tolist()

        if view_mode == "Monthly" and budgets:
            for cat in selected_cats:
                limit = budgets.get(cat, 0)
                if limit <= 0:
                    continue
                fig.add_trace(go.Scatter(
                    x=periods,
                    y=[limit] * len(periods),
                    mode="lines",
                    name=f"{cat} budget",
                    line=dict(
                        color=COLOUR_MAP.get(cat, "#888888"),
                        width=1.5,
                        dash="dash"
                    ),
                    opacity=0.7,
                    hovertemplate=f"{cat} budget: Rs{limit:,.0f}<extra></extra>"
                ))

        elif view_mode == "Weekly" and budgets:
            for cat in selected_cats:
                limit = budgets.get(cat, 0)
                if limit <= 0:
                    continue
                weekly_target = round(limit / 4.3, 0)
                fig.add_trace(go.Scatter(
                    x=periods,
                    y=[weekly_target] * len(periods),
                    mode="lines",
                    name=f"{cat} weekly target",
                    line=dict(
                        color=COLOUR_MAP.get(cat, "#888888"),
                        width=1.5,
                        dash="dot"
                    ),
                    opacity=0.7,
                    hovertemplate=(
                        f"{cat} weekly target: "
                        f"Rs{weekly_target:,.0f}<extra></extra>"
                    )
                ))

    fig.update_layout(
        margin=dict(t=30, b=20, l=0, r=0),
        legend=dict(orientation="h", yanchor="bottom",
                    y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(200,200,200,0.1)"),
    )
    fig.update_traces(
        selector=dict(type="bar"),
        hovertemplate="<b>%{x}</b><br>Rs%{y:,.0f}"
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Line chart ────────────────────────────────────────────────
    st.caption("Spending trend over time per category")

    fig2 = px.line(
        grouped,
        x="Period",
        y="Amount",
        color="Category",
        markers=True,
        color_discrete_map=COLOUR_MAP,
        labels={"Amount": "Amount (Rs)", "Period": x_label},
        height=300,
    )
    fig2.update_layout(
        margin=dict(t=10, b=20, l=0, r=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=False,
            categoryorder="array",
            categoryarray=grouped["Period"].unique().tolist()
        ),
        yaxis=dict(gridcolor="rgba(200,200,200,0.1)"),
    )
    fig2.update_traces(
        hovertemplate="<b>%{fullData.name}</b>: Rs%{y:,.0f}"
    )
    st.plotly_chart(fig2, use_container_width=True)


# ── Main UI ───────────────────────────────────────────────────────────────────

def show_ml_insights_page() -> None:
    st.header("🤖 ML Insights")

    user_id = st.session_state["user_id"]

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
        if st.button("🔄 Retrain model",
                     help="Retrain on your latest data"):
            train_risk_model(user_id)
            st.success("Model retrained!")
            st.rerun()

    # ── Spending trends ───────────────────────────────────────────
    _show_spending_trends(user_id)

    st.divider()

    # ── Risk labels ───────────────────────────────────────────────
    st.subheader("🚦 Spending risk by category")
    st.caption(
        "Logistic Regression trained on your historical spending — "
        "Safe / Warning / Danger based on pace vs budget."
    )

    risk_df = predict_risk(user_id)

    RISK_ICONS   = {"Safe": "🟢", "Warning": "🟠", "Danger": "🔴"}
    RISK_COLOURS = {"Safe": "normal", "Warning": "inverse", "Danger": "off"}

    cols = st.columns(3)
    for i, (_, row) in enumerate(risk_df.iterrows()):
        with cols[i % 3]:
            icon  = RISK_ICONS.get(row["risk_label"], "⚪")
            label = row["risk_label"]
            st.metric(
                label=f"{icon} {row['category']}",
                value=label,
                delta=f"Rs{row['spent']:,.0f} · {row['pct_used']:.0f}% of budget",
                delta_color=RISK_COLOURS.get(label, "off")
            )

    st.divider()

    # ── Forecast ──────────────────────────────────────────────────
    st.subheader("🔮 Month-end forecast")
    st.caption(
        "Linear Regression on your daily spend trend — "
        "predicts where each category will land by end of month."
    )

    forecasts = forecast_month_spend(user_id)
    today     = datetime.date.today()
    budgets   = database.get_budgets(user_id, today.month, today.year)

    # Forecast bar chart
    forecast_rows = []
    for cat in CATEGORIES:
        predicted = forecasts.get(cat, 0.0)
        limit     = budgets.get(cat, 0.0)
        if predicted == 0 and limit == 0:
            continue
        forecast_rows.append({
            "Category":  cat,
            "Predicted": predicted,
            "Budget":    limit
        })

    if forecast_rows:
        fdf = pd.DataFrame(forecast_rows)
        fdf_melted = fdf.melt(
            id_vars="Category",
            value_vars=["Predicted", "Budget"],
            var_name="Type",
            value_name="Amount"
        )

        fig3 = px.bar(
            fdf_melted,
            x="Category",
            y="Amount",
            color="Type",
            barmode="group",
            color_discrete_map={
                "Predicted": "#6C63FF",
                "Budget":    "#444444"
            },
            labels={"Amount": "Amount (Rs)"},
            height=320,
            text_auto=",.0f"
        )
        fig3.update_layout(
            margin=dict(t=10, b=20, l=0, r=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor="rgba(200,200,200,0.1)"),
        )
        fig3.update_traces(
            textposition="outside",
            textfont=dict(size=9),
            hovertemplate="<b>%{x}</b><br>Rs%{y:,.0f}"
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Metric cards
    cols = st.columns(3)
    for i, category in enumerate(CATEGORIES):
        predicted = forecasts.get(category, 0.0)
        limit     = budgets.get(category, 0.0)

        with cols[i % 3]:
            if limit > 0:
                overshoot = predicted - limit
                delta_str = (
                    f"+Rs{overshoot:,.0f} over budget"
                    if overshoot > 0
                    else f"Rs{abs(overshoot):,.0f} under budget"
                )
                delta_col = "inverse" if overshoot > 0 else "normal"
            else:
                delta_str = "No budget set"
                delta_col = "off"

            st.metric(
                label=category,
                value=f"Rs{predicted:,.0f}",
                delta=delta_str,
                delta_color=delta_col
            )

    st.divider()

    # ── Blind spot ────────────────────────────────────────────────
    st.subheader("📍 Your spending blind spot")

    result    = find_blind_spot(user_id)
    worst     = result["worst_category"]
    counts    = result["overspend_counts"]
    summary   = result["monthly_summary"]
    max_count = result["max_count"]

    risk_df_now        = predict_risk(user_id)
    current_overbudget = risk_df_now[
        (risk_df_now["risk_label"] == "Danger") &
        (risk_df_now["budget"] > 0)
    ]["category"].tolist()

    if worst and max_count >= 1:
        st.error(
            f"📍 **{worst}** is your recurring blind spot — "
            f"you've exceeded this budget in "
            f"**{counts[worst]} month{'s' if counts[worst] > 1 else ''}** "
            f"out of the last 6."
        )

        if summary:
            sdf       = pd.DataFrame(summary)
            sdf_worst = sdf[sdf["category"] == worst]

            if not sdf_worst.empty:
                # Sort chronologically
                sdf_worst = sdf_worst.copy()
                sdf_worst["month_dt"] = pd.to_datetime(
                    sdf_worst["month"], format="%b %Y"
                )
                sdf_worst = sdf_worst.sort_values("month_dt")

                fig4 = px.bar(
                    sdf_worst,
                    x="month",
                    y="over_by",
                    color_discrete_sequence=["#FF6B6B"],
                    labels={
                        "over_by": "Over budget by (Rs)",
                        "month":   "Month"
                    },
                    title=f"{worst} — monthly overspend history",
                    height=250,
                    text_auto=",.0f",
                    category_orders={
                        "month": sdf_worst["month"].tolist()
                    }
                )
                fig4.update_layout(
                    margin=dict(t=40, b=20, l=0, r=0),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    xaxis=dict(showgrid=False),
                    yaxis=dict(gridcolor="rgba(200,200,200,0.1)")
                )
                fig4.update_traces(
                    textposition="outside",
                    textfont=dict(size=9),
                    hovertemplate="<b>%{x}</b><br>Over by Rs%{y:,.0f}"
                )
                st.plotly_chart(fig4, use_container_width=True)

        # All categories overspend count
        count_df = pd.DataFrame([
            {"Category": cat, "Months over budget": cnt}
            for cat, cnt in counts.items()
            if cnt > 0
        ]).sort_values("Months over budget", ascending=False)

        if not count_df.empty:
            st.caption("All categories — months exceeded budget")
            fig5 = px.bar(
                count_df,
                x="Category",
                y="Months over budget",
                color="Category",
                color_discrete_map=COLOUR_MAP,
                height=220,
                text_auto=True
            )
            fig5.update_layout(
                margin=dict(t=10, b=20, l=0, r=0),
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="rgba(200,200,200,0.1)")
            )
            fig5.update_traces(
                textposition="outside",
                textfont=dict(size=10)
            )
            st.plotly_chart(fig5, use_container_width=True)

    elif current_overbudget:
        cats = ", ".join(f"**{c}**" for c in current_overbudget)
        st.warning(
            f"No recurring pattern detected across past months yet, but "
            f"{cats} {'is' if len(current_overbudget) == 1 else 'are'} "
            f"over budget this month — worth watching."
        )
    else:
        st.success(
            "No recurring blind spots and you're within budget "
            "across all categories. Great work!"
        )