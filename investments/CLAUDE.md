# investments app

Full investment portfolio tracking with support for Pakistani stocks (PSX), international equities, crypto, and mutual funds. Manual price entry with portfolio calculations.

## Models

### Instrument
- `name`, `ticker` (unique), `instrument_type` (psx_stock/pk_mutual_fund/us_stock/crypto/international_fund), `currency` (PKR/USD), `platform`, `notes`, `is_active`, `created_at`
- Properties: `latest_price`, `current_holdings`, `average_cost`, `current_value`, `unrealized_gain_loss`, `realized_gain_loss`

### InstrumentPrice
- `instrument` FK, `date`, `price`, `created_at`
- Unique together: (instrument, date). `get_price(instrument, date)` uses last-known-price logic.

### InvestmentTransaction
- `date`, `instrument` FK, `transaction_type` (buy/sell/reinvestment/dividend), `units`, `price_per_unit`, `total_amount`, `brokerage_fee`, `tax`, `account` FK, `notes`, `created_at`
- `net_amount` property: buy deducts (total + fees + tax), sell/dividend credits (total - fees - tax), reinvestment returns 0

### ExchangeRate
- `from_currency`, `to_currency`, `date`, `rate`, `created_at`
- Unique together: (from_currency, to_currency, date). `get_rate()` uses last-known-rate logic.

## Signals (signals.py)

Balance recalculation on InvestmentTransaction changes (same pattern as loans/transactions):
- `pre_save` captures old account ID
- `post_save` recalculates affected accounts (current + old) — skipped for reinvestments
- `post_delete` recalculates the transaction's account — skipped for reinvestments

## Balance Impact

- **Buy**: deducts `total_amount + brokerage_fee + tax` from account
- **Sell**: credits `total_amount - brokerage_fee - tax` to account
- **Reinvestment**: zero balance impact (adds units and cost basis only, e.g., mutual fund dividend reinvestment)
- **Dividend**: credits `total_amount - brokerage_fee - tax` to account (cash payout, no unit impact)
- Formula: `... - investment_buys + investment_sells + investment_dividends` (reinvestments excluded from balance calc)

## Performance Engine (performance.py)

`compute_portfolio_series(start_date, end_date)` computes historical portfolio value and net invested over a date range. Uses only 3 DB queries total (all transactions, all prices, all USD→PKR rates), then does all lookups in Python via `bisect` binary search. Daily sampling for ≤90 days, weekly for longer ranges. Returns `(dates, portfolio_values, net_invested_values)` in PKR.

Helpers:
- `get_inception_date()` — earliest investment transaction date
- `_get_last_known(sorted_pairs, target_date)` — bisect-based last-known lookup

## Views

- `PortfolioDashboardView` — summary cards, allocation donut chart, 30-day performance line chart, holdings table
- `PortfolioPerformanceView` — dedicated performance page with date range presets (1M/3M/6M/YTD/All/Custom), dual-line chart (portfolio value vs net invested), summary cards
- `InstrumentListView/CreateView/UpdateView/DetailView` — instrument CRUD
- `InvestmentTransactionListView/CreateView` — filterable transaction list and add form
- `BulkPriceEntryView` — update prices for all active instruments at once
- `PriceHistoryView` — filterable price history
- `ExchangeRateListView` — list + inline add form

## URLs (namespace: `investments`)

- `investments:list` → `/investments/` (portfolio dashboard)
- `investments:performance` → `/investments/performance/` (performance chart page)
- `investments:instrument_list/create/detail/edit` → `/investments/instruments/...`
- `investments:transaction_list/create` → `/investments/transactions/...`
- `investments:bulk_prices` → `/investments/prices/`
- `investments:price_history` → `/investments/prices/history/`
- `investments:exchange_rates` → `/investments/exchange-rates/`

## Notes

- Uses purple accent color throughout.
- Chart.js loaded only on dashboard, instrument detail, and performance templates via `{% block extra_js %}`.
- All templates include dark mode classes.
- Performance page uses historical holdings (units as of each date) not current holdings — more accurate than dashboard's 30-day chart.
