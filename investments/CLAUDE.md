# investments app

Full investment portfolio tracking with support for Pakistani stocks (PSX), international equities, crypto, and mutual funds. Manual price entry with portfolio calculations.

## Models

### Instrument
- `name`, `ticker` (unique), `instrument_type` (psx_stock/pk_mutual_fund/us_stock/crypto/international_fund), `currency` (PKR/USD), `api_id` (CoinGecko coin ID, e.g. "bitcoin"), `platform`, `notes`, `is_active`, `created_at`
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

## Crypto Price Fetching (crypto_prices.py)

Auto-fetch historical + current crypto prices from CoinGecko's free API for instruments with `api_id` set. Uses `httpx` for HTTP requests. Logs to `investments.crypto_prices` logger (INFO level configured in settings).

- `fetch_crypto_prices(fetch_exchange_rate, stdout, ticker, start_date, end_date)` — main entry point. Iterates crypto instruments with api_id (optionally filtered by ticker), fetches `/coins/{api_id}/market_chart/range` using the instrument's currency as `vs_currency` (PKR or USD). Saves via `update_or_create`. 6-second delay between instruments (free tier rate limit). Auto-caps range to 365 days unless explicit start date given. Also fetches historical USD/PKR rates via tether/PKR for the same date range.
- `start_background_fetch(ticker, start_date, end_date)` / `get_fetch_status()` — daemon thread wrapper with Lock-based status dict for UI polling.
- Management command: `fetch_crypto_prices` with `--ticker`, `--start-date`, `--end-date`, `--no-exchange-rate` flags.
- Free tier limitations: 401 errors on ranges >365 days, 429 on rate limiting. Errors handled per-instrument so one failure doesn't stop others.

## Views

- `PortfolioDashboardView` — summary cards, allocation donut chart, 30-day performance line chart, holdings table
- `PortfolioPerformanceView` — dedicated performance page with date range presets (1M/3M/6M/YTD/All/Custom), dual-line chart (portfolio value vs net invested), summary cards
- `InstrumentListView/CreateView/UpdateView/DetailView` — instrument CRUD
- `InvestmentTransactionListView/CreateView` — filterable transaction list and add form
- `BulkPriceEntryView` — update prices for all active instruments at once. Shows "Fetch Crypto Prices" card with instrument picker and date range fields if crypto instruments with api_id exist. JS polls `fetch_crypto_prices` GET endpoint for status updates.
- `FetchCryptoPricesView` — POST starts background fetch (accepts ticker, start_date, end_date from form), GET returns JSON status for polling
- `PriceImportView` — upload xlsx → preview → confirm import flow. Auto-detects Meezan/MUFAP (13-col, repurchase from col 4) and MCB (4-col, redemption from col 3) formats. Uses `openpyxl` (read_only). Parsing helpers: `parse_price_file`, `_detect_format`, `_parse_meezan`, `_parse_mcb`, `_parse_date`, `_pick_price`. Stores preview as JSON in hidden field between steps. Uses `InstrumentPrice.update_or_create` for idempotent import.
- `PriceHistoryView` — filterable price history
- `ExchangeRateListView` — list + inline add form

## URLs (namespace: `investments`)

- `investments:list` → `/investments/` (portfolio dashboard)
- `investments:performance` → `/investments/performance/` (performance chart page)
- `investments:instrument_list/create/detail/edit` → `/investments/instruments/...`
- `investments:transaction_list/create` → `/investments/transactions/...`
- `investments:bulk_prices` → `/investments/prices/`
- `investments:price_history` → `/investments/prices/history/`
- `investments:price_import` → `/investments/prices/import/`
- `investments:fetch_crypto_prices` → `/investments/fetch-crypto-prices/`
- `investments:exchange_rates` → `/investments/exchange-rates/`

## Notes

- Uses purple accent color throughout.
- Chart.js loaded only on dashboard, instrument detail, and performance templates via `{% block extra_js %}`.
- All templates include dark mode classes.
- Performance page uses historical holdings (units as of each date) not current holdings — more accurate than dashboard's 30-day chart.
