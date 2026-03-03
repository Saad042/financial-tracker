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
- `date`, `instrument` FK, `transaction_type` (buy/sell), `units`, `price_per_unit`, `total_amount`, `brokerage_fee`, `tax`, `account` FK, `notes`, `created_at`
- `net_amount` property: buy deducts (total + fees + tax), sell credits (total - fees - tax)

### ExchangeRate
- `from_currency`, `to_currency`, `date`, `rate`, `created_at`
- Unique together: (from_currency, to_currency, date). `get_rate()` uses last-known-rate logic.

## Signals (signals.py)

Balance recalculation on InvestmentTransaction changes (same pattern as loans/transactions):
- `pre_save` captures old account ID
- `post_save` recalculates affected accounts (current + old)
- `post_delete` recalculates the transaction's account

## Balance Impact

- **Buy**: deducts `total_amount + brokerage_fee + tax` from account
- **Sell**: credits `total_amount - brokerage_fee - tax` to account
- Formula: `... - investment_buys + investment_sells`

## Views

- `PortfolioDashboardView` — summary cards, allocation donut chart, performance line chart, holdings table
- `InstrumentListView/CreateView/UpdateView/DetailView` — instrument CRUD
- `InvestmentTransactionListView/CreateView` — filterable transaction list and add form
- `BulkPriceEntryView` — update prices for all active instruments at once
- `PriceHistoryView` — filterable price history
- `ExchangeRateListView` — list + inline add form

## URLs (namespace: `investments`)

- `investments:list` → `/investments/` (portfolio dashboard)
- `investments:instrument_list/create/detail/edit` → `/investments/instruments/...`
- `investments:transaction_list/create` → `/investments/transactions/...`
- `investments:bulk_prices` → `/investments/prices/`
- `investments:price_history` → `/investments/prices/history/`
- `investments:exchange_rates` → `/investments/exchange-rates/`

## Notes

- Uses purple accent color throughout.
- Chart.js loaded only on dashboard and instrument detail templates via `{% block extra_js %}`.
- All templates include dark mode classes.
