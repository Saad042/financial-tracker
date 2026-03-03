# core app

Shared utilities, the main dashboard, and data export/import commands. Has no models of its own.

## Dashboard (views.py)

`DashboardView` at `/` — provides:
- `total_balance` — sum of all account balances
- `accounts` — all accounts for breakdown display
- `month_income`, `month_expenses`, `month_net` — current month aggregates
- `recent_transactions` — last 15 transactions with related objects
- `outstanding_loans_total`, `outstanding_loans_count` — outstanding loan summary
- `total_invested`, `investments_count` — total investment amount and count
- `budget_alerts` — list of budgets at warning (>=80%) or exceeded (>=100%) status for the current month

Template: `templates/core/dashboard.html`

## Template Tags (templatetags/currency.py)

`|pkr` filter — formats a Decimal/number as "PKR 1,234.56" with comma separators. Handles negatives with a leading minus sign.

Usage: `{% load currency %}` then `{{ amount|pkr }}`

## Management Commands

### `export_data`

Exports all app data (accounts, categories, transactions, loans, recurring_rules, budgets, investments, tags, transaction_tags, loan_tags) to a JSON file with a `meta` block containing app version and timestamp. Custom `DecimalDateEncoder` handles Decimal and date serialization.

```bash
uv run python manage.py export_data                        # default: expense_tracker_export.json
uv run python manage.py export_data --output backup.json   # custom path
```

### `import_data`

Full-replace import inside `atomic()`. Deletes all data in reverse dependency order (including TransactionTag, LoanTag, Tag), then bulk-creates from JSON in dependency order. Disconnects transaction, loan, and investment signals during import to avoid per-row balance recalculation, then calls `recalculate_balance()` on all accounts once at the end. Backward compatible — uses `data.get()` for tag keys so older export files without tags still import cleanly.

```bash
uv run python manage.py import_data expense_tracker_export.json        # interactive prompt
uv run python manage.py import_data expense_tracker_export.json --yes  # skip confirmation
```

## Project-Level Templates (in `templates/`)

- `templates/base.html` — main layout with nav bar (desktop + mobile hamburger menu), active link highlighting, HTMX script, CSRF token, Tailwind CSS. Includes dark mode: theme detection script in `<head>` (reads `theme` cookie synchronously), theme toggle button (sun/moon icon cycling Light → Dark → System), cookie-based persistence (1-year expiry). All elements have `dark:` Tailwind variants.
- `templates/partials/_messages.html` — Django messages display (success/error/warning/info) with dark mode variants
- `templates/core/dashboard.html` — dashboard page with dark mode variants
