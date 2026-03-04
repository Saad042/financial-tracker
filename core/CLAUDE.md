# core app

Shared utilities, the main dashboard, and data export/import commands. Has no models of its own.

## Dashboard (views.py)

`DashboardView` at `/` — provides:
- `total_balance` — sum of all account balances
- `accounts` — all accounts for breakdown display
- `month_income`, `month_expenses`, `month_net` — current month aggregates
- `savings_rate` — (income - expenses) / income × 100 for current month
- `last_month_income`, `last_month_expenses` — previous month aggregates
- `income_change_pct`, `expense_change_pct` — month-over-month percentage change (None if no prior month data)
- `recent_transactions` — last 15 transactions with related objects
- `loans_active_count`, `loans_total_lent`, `loans_total_repaid`, `loans_total_remaining`, `loans_overdue_count` — active loan summary
- `overdue_loans` — up to 5 overdue loan objects (annotated with `total_repaid`) for detail display with borrower name, due date, remaining amount
- `portfolio_value` — total portfolio value in PKR (matches PortfolioDashboardView: active instruments × latest prices, USD converted via ExchangeRate)
- `net_invested_pkr` — net cash deployed across all instruments (buys - sells - dividends) in PKR
- `total_gain_loss`, `total_gain_loss_pct` — portfolio value minus net invested
- `total_realized_pkr` — sum of realized gain/loss across all instruments in PKR
- `has_investments` — boolean, true if any InvestmentTransaction exists
- `net_worth` — total_balance + loans_total_remaining + portfolio_value (estimated net worth)
- `top_categories` — top 5 expense categories this month (name + total)
- `budget_alerts` — list of budgets at warning (>=80%) or exceeded (>=100%) status for the current month
- `pending_recurring` — active RecurringRule objects not yet generated this period (same idempotency check as `generate_recurring` command)

Template: `templates/core/dashboard.html`

## Template Tags (templatetags/currency.py)

`|pkr` filter — formats a Decimal/number as "PKR 1,234.56" with comma separators. Handles negatives with a leading minus sign.

Usage: `{% load currency %}` then `{{ amount|pkr }}`

## Management Commands

### `export_data`

Exports all app data (accounts, categories, transactions, loans, loan_repayments, recurring_rules, budgets, instruments, instrument_prices, investment_transactions, exchange_rates, tags, transaction_tags, loan_tags) to a JSON file with a `meta` block containing app version and timestamp. Custom `DecimalDateEncoder` handles Decimal and date serialization.

```bash
uv run python manage.py export_data                        # default: expense_tracker_export.json
uv run python manage.py export_data --output backup.json   # custom path
```

### `import_data`

Full-replace import inside `atomic()`. Deletes all data in reverse dependency order (including InvestmentTransaction, InstrumentPrice, ExchangeRate, Instrument, TransactionTag, LoanTag, Tag), then bulk-creates from JSON in dependency order. Disconnects transaction, loan, and investment transaction signals during import to avoid per-row balance recalculation, then calls `recalculate_balance()` on all accounts once at the end. Backward compatible — uses `data.get()` for new keys so older export files still import cleanly.

```bash
uv run python manage.py import_data expense_tracker_export.json        # interactive prompt
uv run python manage.py import_data expense_tracker_export.json --yes  # skip confirmation
```

## Project-Level Templates (in `templates/`)

- `templates/base.html` — main layout with nav bar (desktop + mobile hamburger menu), active link highlighting, HTMX script, CSRF token, Tailwind CSS. Includes dark mode: theme detection script in `<head>` (reads `theme` cookie synchronously), theme toggle button (sun/moon icon cycling Light → Dark → System), cookie-based persistence (1-year expiry). All elements have `dark:` Tailwind variants.
- `templates/partials/_messages.html` — Django messages display (success/error/warning/info) with dark mode variants
- `templates/core/dashboard.html` — dashboard page with dark mode variants
