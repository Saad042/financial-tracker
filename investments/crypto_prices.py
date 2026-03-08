"""
Fetch crypto prices from CoinGecko's free API.

Entry points:
- fetch_crypto_prices() — synchronous, fetches all crypto instruments with api_id set
- start_background_fetch() / get_fetch_status() — background thread for UI use
"""

import logging
import threading
import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import httpx

from .models import ExchangeRate, Instrument, InstrumentPrice

logger = logging.getLogger("investments.crypto_prices")

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
RATE_LIMIT_DELAY = 6  # seconds between requests (free tier)
FREE_TIER_MAX_DAYS = 365  # CoinGecko free tier limits historical data


def _log(msg, stdout=None, level=logging.INFO):
    logger.log(level, msg)
    if stdout:
        stdout.write(msg)


# ---------------------------------------------------------------------------
# Background fetch state (thread-safe)
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_status = {
    "running": False,
    "progress": "",
    "results": [],
    "error": "",
}


def get_fetch_status():
    with _lock:
        return dict(_status)


def _set_status(**kwargs):
    with _lock:
        _status.update(kwargs)


def start_background_fetch(
    fetch_exchange_rate=True, ticker=None, start_date=None, end_date=None,
    user=None,
):
    """Start fetch in a daemon thread. Returns True if started, False if already running."""
    with _lock:
        if _status["running"]:
            return False
        _status.update(running=True, progress="Starting...", results=[], error="")

    t = threading.Thread(
        target=_background_worker,
        args=(fetch_exchange_rate, ticker, start_date, end_date, user),
        daemon=True,
    )
    t.start()
    return True


def _background_worker(fetch_exchange_rate, ticker, start_date, end_date, user):
    try:
        fetch_crypto_prices(
            fetch_exchange_rate=fetch_exchange_rate,
            stdout=None,
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            user=user,
        )
    except Exception as e:
        logger.exception("Background crypto fetch failed")
        _set_status(error=str(e))
    finally:
        _set_status(running=False)


# ---------------------------------------------------------------------------
# Core fetch logic
# ---------------------------------------------------------------------------


def fetch_crypto_prices(
    fetch_exchange_rate=True,
    stdout=None,
    ticker=None,
    start_date=None,
    end_date=None,
    user=None,
):
    """
    Fetch historical + current prices for crypto instruments with api_id set.

    Args:
        ticker: If set, only fetch for this specific instrument ticker.
        start_date: Override start date (instead of auto-detecting from latest price).
        end_date: Override end date (default: today).
        user: If set, only fetch for instruments belonging to this user.
    """
    qs = Instrument.objects.filter(
        instrument_type=Instrument.CRYPTO,
        is_active=True,
    ).exclude(api_id="")
    if user:
        qs = qs.filter(user=user)

    if ticker:
        qs = qs.filter(ticker__iexact=ticker)

    instruments = list(qs)

    if not instruments:
        suffix = f" for ticker {ticker!r}" if ticker else ""
        msg = f"No crypto instruments with api_id found{suffix}."
        _log(msg, stdout)
        _set_status(progress=msg)
        return

    results = []
    total = len(instruments)
    today = date.today()
    # Track the earliest start date across all fetches for exchange rate range
    rate_start = start_date  # None if not explicitly set
    rate_end = end_date or today

    for idx, inst in enumerate(instruments, 1):
        label = f"[{idx}/{total}] {inst.ticker}"
        msg = f"{label}: fetching prices ({inst.currency})..."
        _log(msg, stdout)
        _set_status(progress=msg)

        try:
            count, fetch_start = _fetch_instrument_prices(
                inst, stdout, start_date, end_date
            )
            if fetch_start and (rate_start is None or fetch_start < rate_start):
                rate_start = fetch_start
            result = f"{label}: {count} price(s) saved"
            results.append(result)
            _log(result, stdout)
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            if code == 401:
                err = (
                    f"{label}: HTTP 401 — CoinGecko free tier limits"
                    f" historical data. Try a shorter date range"
                    f" (max ~{FREE_TIER_MAX_DAYS} days)."
                )
            elif code == 429:
                err = f"{label}: rate limited (HTTP 429). Try again later."
            elif code == 404:
                err = f"{label}: not found (HTTP 404). Check api_id '{inst.api_id}'."
            else:
                err = f"{label}: HTTP {code}"
            results.append(err)
            _log(err, stdout, logging.WARNING)
        except Exception as e:
            err = f"{label}: error — {e}"
            results.append(err)
            _log(err, stdout, logging.ERROR)

        _set_status(results=list(results))

        # Rate limit delay (skip after last instrument)
        if idx < total:
            _log(f"  Waiting {RATE_LIMIT_DELAY}s (rate limit)...", stdout)
            time.sleep(RATE_LIMIT_DELAY)

    # Fetch exchange rate for the same date range as prices
    if fetch_exchange_rate:
        if rate_start is None:
            rate_start = rate_end
        msg = f"Fetching USD/PKR rates ({rate_start} to {rate_end})..."
        _log(msg, stdout)
        _set_status(progress=msg)
        try:
            rate_result = _fetch_usd_pkr_rates(rate_start, rate_end, stdout)
            results.append(rate_result)
        except Exception as e:
            err = f"Exchange rate error: {e}"
            results.append(err)
            _log(err, stdout, logging.ERROR)

    _set_status(progress="Done", results=list(results))
    _log("Done.", stdout)


def _fetch_instrument_prices(inst, stdout, override_start=None, override_end=None):
    """Fetch and save prices for a single instrument. Returns (count, start_date)."""
    today = date.today()
    end = override_end or today

    # Determine start date
    if override_start:
        start = override_start
    else:
        # Day after latest existing price, or earliest transaction, or 90 days ago
        latest_price = inst.prices.order_by("-date").first()
        if latest_price:
            start = latest_price.date + timedelta(days=1)
        else:
            earliest_tx = inst.transactions.order_by("date").first()
            if earliest_tx:
                start = earliest_tx.date
            else:
                start = today - timedelta(days=90)

    if start > end:
        _log(f"  Already up to date (latest price through {end})", stdout)
        return 0, None

    # Cap range for free tier unless user explicitly set start date
    if not override_start and (end - start).days > FREE_TIER_MAX_DAYS:
        old_start = start
        start = end - timedelta(days=FREE_TIER_MAX_DAYS)
        _log(
            f"  Capping range from {old_start} to {start}"
            f" (free tier max {FREE_TIER_MAX_DAYS} days)",
            stdout,
            logging.WARNING,
        )

    # Use the instrument's currency for vs_currency
    vs_currency = inst.currency.lower()

    # CoinGecko market_chart/range uses UNIX timestamps
    from_ts = int(time.mktime(start.timetuple()))
    to_ts = int(time.mktime((end + timedelta(days=1)).timetuple()))

    url = f"{COINGECKO_BASE}/coins/{inst.api_id}/market_chart/range"
    params = {
        "vs_currency": vs_currency,
        "from": from_ts,
        "to": to_ts,
    }

    _log(f"  Range: {start} to {end} (vs {vs_currency.upper()})", stdout)

    with httpx.Client(timeout=30) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    prices = data.get("prices", [])
    if not prices:
        return 0

    # Group by date (CoinGecko returns multiple points per day for short ranges)
    # Take the last price point for each date
    daily_prices = {}
    for timestamp_ms, price_val in prices:
        d = date.fromtimestamp(timestamp_ms / 1000)
        daily_prices[d] = price_val

    count = 0
    for d, price_val in daily_prices.items():
        try:
            price_decimal = Decimal(str(round(price_val, 4)))
        except (InvalidOperation, ValueError):
            continue
        if price_decimal <= 0:
            continue

        InstrumentPrice.objects.update_or_create(
            instrument=inst,
            date=d,
            defaults={"price": price_decimal},
        )
        count += 1

    return count, start


def _fetch_usd_pkr_rates(start, end, stdout):
    """Fetch USD/PKR rates for a date range using CoinGecko tether/pkr market chart."""
    from_ts = int(time.mktime(start.timetuple()))
    to_ts = int(time.mktime((end + timedelta(days=1)).timetuple()))

    url = f"{COINGECKO_BASE}/coins/tether/market_chart/range"
    params = {
        "vs_currency": "pkr",
        "from": from_ts,
        "to": to_ts,
    }

    _log(f"  Range: {start} to {end}", stdout)

    with httpx.Client(timeout=30) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    prices = data.get("prices", [])
    if not prices:
        return "Exchange rate: no PKR rate data from CoinGecko"

    # Group by date, take last value per day
    daily_rates = {}
    for timestamp_ms, rate_val in prices:
        d = date.fromtimestamp(timestamp_ms / 1000)
        daily_rates[d] = rate_val

    count = 0
    for d, rate_val in daily_rates.items():
        try:
            rate_decimal = Decimal(str(round(rate_val, 4)))
        except (InvalidOperation, ValueError):
            continue
        if rate_decimal <= 0:
            continue

        ExchangeRate.objects.update_or_create(
            from_currency="USD",
            to_currency="PKR",
            date=d,
            defaults={"rate": rate_decimal},
        )
        count += 1

    result = f"USD/PKR: {count} rate(s) saved ({start} to {end})"
    _log(result, stdout)
    return result
