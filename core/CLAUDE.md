# core app

Shared utilities and the main dashboard. Has no models of its own.

## Dashboard (views.py)

`DashboardView` at `/` — provides:
- `total_balance` — sum of all account balances
- `accounts` — all accounts for breakdown display
- `month_income`, `month_expenses`, `month_net` — current month aggregates
- `recent_transactions` — last 15 transactions with related objects

Template: `templates/core/dashboard.html`

## Template Tags (templatetags/currency.py)

`|pkr` filter — formats a Decimal/number as "PKR 1,234.56" with comma separators. Handles negatives with a leading minus sign.

Usage: `{% load currency %}` then `{{ amount|pkr }}`

## Project-Level Templates (in `templates/`)

- `templates/base.html` — main layout with nav bar, HTMX script, CSRF token, Tailwind CSS
- `templates/partials/_messages.html` — Django messages display (success/error/warning/info)
- `templates/core/dashboard.html` — dashboard page
