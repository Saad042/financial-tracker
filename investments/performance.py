"""Portfolio performance computation engine.

Computes historical portfolio value and net invested series using
pre-fetched data with bisect-based lookups (3 DB queries total).
"""

from bisect import bisect_right
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from .models import ExchangeRate, InstrumentPrice, InvestmentTransaction


def get_inception_date(user=None):
    """Return the date of the earliest investment transaction, or None."""
    qs = InvestmentTransaction.objects.all()
    if user:
        qs = qs.filter(user=user)
    first = qs.order_by("date").values_list("date", flat=True).first()
    return first


def _get_last_known(sorted_pairs, target_date):
    """Binary search for the last value on or before target_date.

    sorted_pairs: list of (date, value) sorted ascending by date.
    Returns the value or None if no entry exists on or before target_date.
    """
    if not sorted_pairs:
        return None
    dates = [p[0] for p in sorted_pairs]
    idx = bisect_right(dates, target_date) - 1
    if idx < 0:
        return None
    return sorted_pairs[idx][1]


def compute_portfolio_series(start_date, end_date, user=None):
    """Compute portfolio value and net invested series over a date range.

    Returns (dates, portfolio_values, net_invested_values) where each is a
    list. Values are Decimals in PKR.

    Optimization: 3 DB queries total, all lookups done in Python via bisect.
    """
    # 1. Pre-fetch all investment transactions grouped by instrument
    tx_qs = InvestmentTransaction.objects.select_related("instrument")
    if user:
        tx_qs = tx_qs.filter(user=user)
    all_txs = list(
        tx_qs.order_by("date", "created_at")
        .values_list(
            "date",
            "instrument_id",
            "instrument__currency",
            "transaction_type",
            "units",
            "total_amount",
            "brokerage_fee",
            "tax",
        )
    )

    # Group transactions by instrument_id
    txs_by_instrument = defaultdict(list)
    instrument_currencies = {}
    for tx_date, inst_id, currency, tx_type, units, amount, fee, tax in all_txs:
        txs_by_instrument[inst_id].append((tx_date, tx_type, units, amount, fee, tax))
        instrument_currencies[inst_id] = currency

    # 2. Pre-fetch all instrument prices → {instrument_id: [(date, price), ...]}
    prices_by_instrument = defaultdict(list)
    for inst_id, p_date, price in (
        InstrumentPrice.objects.order_by("date")
        .values_list("instrument_id", "date", "price")
    ):
        prices_by_instrument[inst_id].append((p_date, price))

    # 3. Pre-fetch all USD→PKR exchange rates → [(date, rate), ...]
    usd_pkr_rates = list(
        ExchangeRate.objects.filter(from_currency="USD", to_currency="PKR")
        .order_by("date")
        .values_list("date", "rate")
    )

    # Determine sample dates
    total_days = (end_date - start_date).days
    if total_days <= 90:
        # Daily sampling
        sample_dates = [start_date + timedelta(days=i) for i in range(total_days + 1)]
    else:
        # Weekly sampling
        sample_dates = []
        d = start_date
        while d < end_date:
            sample_dates.append(d)
            d += timedelta(days=7)
        # Always include end_date as last point
        if not sample_dates or sample_dates[-1] != end_date:
            sample_dates.append(end_date)

    dates_out = []
    portfolio_values = []
    net_invested_values = []

    for d in sample_dates:
        day_portfolio_value = Decimal("0")
        day_net_invested = Decimal("0")

        for inst_id, txs in txs_by_instrument.items():
            currency = instrument_currencies[inst_id]

            # Historical holdings and net invested as of date d
            holdings = Decimal("0")
            buy_cost = Decimal("0")
            sell_dividend_proceeds = Decimal("0")

            for tx_date, tx_type, units, amount, fee, tax in txs:
                if tx_date > d:
                    break
                if tx_type in (InvestmentTransaction.BUY, InvestmentTransaction.REINVESTMENT):
                    holdings += units
                elif tx_type == InvestmentTransaction.SELL:
                    holdings -= units

                # Net invested: buy costs - (sell + dividend proceeds)
                if tx_type == InvestmentTransaction.BUY:
                    buy_cost += amount + fee + tax
                elif tx_type in (InvestmentTransaction.SELL, InvestmentTransaction.DIVIDEND):
                    sell_dividend_proceeds += amount - fee - tax

            net_cash = buy_cost - sell_dividend_proceeds

            # Portfolio value: holdings × last-known price
            inst_value = Decimal("0")
            if holdings > 0:
                price = _get_last_known(prices_by_instrument.get(inst_id, []), d)
                if price is not None:
                    inst_value = holdings * price

            # Convert to PKR if USD
            if currency == "USD":
                rate = _get_last_known(usd_pkr_rates, d) or Decimal("1")
                inst_value *= rate
                net_cash *= rate

            day_portfolio_value += inst_value
            day_net_invested += net_cash

        dates_out.append(d.isoformat())
        portfolio_values.append(day_portfolio_value)
        net_invested_values.append(day_net_invested)

    return dates_out, portfolio_values, net_invested_values
