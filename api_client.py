import os
import datetime
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("EXCHANGE_RATE_API_KEY", "")

# Supported currencies — INR is always the base
CURRENCIES = ["INR", "USD", "EUR", "GBP", "AED", "SGD"]

# Fallback rates if API is down — approximate values
# These are hardcoded safety nets, not live rates
FALLBACK_RATES = {
    "INR": 1.0,
    "USD": 83.5,
    "EUR": 90.2,
    "GBP": 105.8,
    "AED": 22.7,
    "SGD": 62.1,
}


def get_exchange_rates() -> dict:
    """
    Fetch live exchange rates from ExchangeRate-API.
    Base currency is INR — so all values are "1 unit of X = Y INR".

    Caching strategy:
    Rates are stored in st.session_state with a timestamp.
    If the cached rates are less than 1 hour old, they're reused.
    This prevents burning through the 1500/month free quota.

    Returns dict: {"USD": 83.5, "EUR": 90.2, ...}
    On failure: returns FALLBACK_RATES and sets a warning flag.
    """
    # ── Check cache first ─────────────────────────────────────────
    cache_key  = "exchange_rates"
    cache_time = "exchange_rates_fetched_at"

    if cache_key in st.session_state and cache_time in st.session_state:
        elapsed = (
            datetime.datetime.now() - st.session_state[cache_time]
        ).seconds
        if elapsed < 3600:  # under 1 hour — use cache
            return st.session_state[cache_key]

    # ── Fetch fresh rates ─────────────────────────────────────────
    if not API_KEY:
        st.session_state["rates_fallback"] = True
        return FALLBACK_RATES

    try:
        # ExchangeRate-API URL format:
        # https://v6.exchangerate-api.com/v6/{key}/latest/INR
        # Returns how many units of every currency = 1 INR
        # We invert: how many INR = 1 unit of foreign currency
        url      = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/INR"
        response = requests.get(url, timeout=5)
        response.raise_for_status()   # raises exception for 4xx/5xx

        data         = response.json()
        raw_rates    = data["conversion_rates"]  # e.g. {"USD": 0.01198, ...}

        # Invert: 1 INR = 0.012 USD → 1 USD = 83.5 INR
        inverted = {
            currency: round(1 / raw_rates[currency], 4)
            for currency in CURRENCIES
            if currency in raw_rates and raw_rates[currency] != 0
        }
        inverted["INR"] = 1.0  # INR to INR is always 1

        # Store in session_state with timestamp
        st.session_state[cache_key]  = inverted
        st.session_state[cache_time] = datetime.datetime.now()
        st.session_state["rates_fallback"] = False

        return inverted

    except requests.exceptions.Timeout:
        st.session_state["rates_fallback"] = True
        return FALLBACK_RATES

    except requests.exceptions.RequestException:
        st.session_state["rates_fallback"] = True
        return FALLBACK_RATES

    except (KeyError, ZeroDivisionError):
        st.session_state["rates_fallback"] = True
        return FALLBACK_RATES


def convert_to_inr(amount: float, currency: str) -> tuple[float, bool]:
    """
    Convert an amount in any supported currency to INR.

    Returns (inr_amount, used_fallback)
    used_fallback=True means live rates were unavailable.
    """
    if currency == "INR":
        return round(amount, 2), False

    rates       = get_exchange_rates()
    used_fallback = st.session_state.get("rates_fallback", False)
    rate        = rates.get(currency, FALLBACK_RATES.get(currency, 1.0))
    inr_amount  = round(amount * rate, 2)

    return inr_amount, used_fallback