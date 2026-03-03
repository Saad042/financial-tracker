# Expense Tracker

Personal expense tracking web app. All amounts in PKR. Local-first, single-user, SQLite-backed.

## Tech Stack

- **Backend:** Django 6.0, Python 3.12, SQLite
- **Frontend:** Django Templates, Tailwind CSS v4 (standalone via django-tailwind), HTMX
- **Package manager:** uv
- **Dev tools:** django-browser-reload, django-htmx

## Commands

```bash
uv run python manage.py runserver          # Start dev server
uv run python manage.py tailwind start     # Watch & rebuild CSS
uv run python manage.py tailwind build     # One-off CSS build
uv run python manage.py makemigrations     # Generate migrations
uv run python manage.py migrate            # Apply migrations
uv run python manage.py createsuperuser    # Create admin user
uv run python manage.py generate_recurring # Create transactions from active recurring rules
uv run python manage.py export_data        # Export all data to JSON (default: expense_tracker_export.json)
uv run python manage.py import_data <file> # Import data from JSON (full replace, use --yes to skip prompt)
```

Always run commands through `uv run` — the virtualenv is managed by uv.

## Project Layout

```
expense_tracker/     # Django project config (settings, root URLs, wsgi)
accounts/            # Account model (bank/cash), CRUD views
transactions/        # Category + Transaction models, balance signals, CRUD views
loans/               # Loan model, signals, create/detail/repay views
recurring/           # RecurringRule model, CRUD views, generate_recurring command
budgets/             # Budget model, overview/set/copy views with progress bars
reports/             # Report hub, monthly breakdown (Chart.js), income/expense trends
investments/         # Portfolio tracking: Instrument, InstrumentPrice, InvestmentTransaction, ExchangeRate models
tags/                # Tag model (place/group), TransactionTag/LoanTag through models, CRUD + HTMX search
core/                # Dashboard view, shared template tags, export/import commands
theme/               # Tailwind CSS theme app (auto-generated, don't edit manually)
templates/           # Project-level templates (base.html, dashboard, partials)
```

## Architecture Decisions

- **Balance caching:** Account.balance is a cached DecimalField, recalculated via Django signals on every transaction, loan, and investment save/delete. Never set balance directly — it's derived from transactions, loans, and investments.
- **Balance formula:** `income - expenses - transfers_out + transfers_in - non_repaid_loans - investment_buys + investment_sells + investment_dividends` (buy/sell/dividend amounts inclusive of fees and tax)
- **Transfers:** A single Transaction row with `type="transfer"`, `account` = source, `transfer_to` = destination. Not two rows.
- **Loans:** A Loan row tracks money lent out. Non-repaid loans (outstanding + partially_repaid) reduce account balance. LoanRepayment model tracks individual partial repayments — each creates an income Transaction ("Loan Repayment Received"). Loan status auto-updates: outstanding → partially_repaid → repaid. Forgiving a loan creates an expense Transaction ("Loan Written Off") for the remaining amount.
- **Recurring:** RecurringRule defines repeating transactions. The `generate_recurring` management command creates Transaction rows (idempotent per period). Transaction has a nullable `recurring_rule` FK (`on_delete=SET_NULL`).
- **Budgets:** Budget = (category, month) pair with an amount. Properties compute `spent`, `remaining`, `percent_used`, `status` (safe/warning/exceeded). Budget alerts surface on the dashboard.
- **Categories:** Pre-seeded via data migration (`0002_seed_categories.py`). System categories have `is_system=True`. Categories belong to the `transactions` app.
- **Tags:** Two tag types — places (where) and groups (linking related transactions). Separate `TransactionTag`/`LoanTag` through models in the `tags` app (not ManyToManyField). Tags are soft-deleted via `is_active=False`. HTMX-powered search + inline creation widget reused across transaction, transfer, and loan forms. Tag names included in transaction search filter. Green accent for places, purple for groups.
- **FK safety:** All foreign keys use `on_delete=PROTECT`, except `Transaction.recurring_rule` which uses `SET_NULL` so deleting a rule orphans its transactions. Tag through models use CASCADE on the transaction/loan FK and PROTECT on the tag FK.
- **HTMX:** Used for dynamic category dropdown filtering by transaction type. Pattern: `hx-get` on the type select triggers a view that returns `<option>` HTML. Reused in recurring rule form. Also used for transaction list filtering — view returns a partial template when `request.htmx` is true.
- **Transaction filtering:** `_apply_transaction_filters(qs, params)` in `transactions/views.py` is a shared helper reused by the list view and CSV export. Filters: search (description + tag name icontains), type, category (parent + children), account, date range, amount range, tag (specific ID), tag_type (place/group). Uses `.distinct()` to avoid M2M join duplicates.
- **Charts:** Chart.js loaded via CDN only on report templates (`{% block extra_js %}`). Not loaded globally. Charts use theme-aware colors (text, grid, borders) detected via `document.documentElement.classList.contains('dark')`.
- **Investments:** Full portfolio tracking with Instrument, InstrumentPrice, InvestmentTransaction, ExchangeRate models. Four transaction types: buy (deducts from account), sell (credits account), reinvestment (adds units/cost basis, zero balance impact), dividend (credits cash payout to account, no unit impact). Portfolio dashboard with Chart.js (allocation donut, 30-day performance line). Holdings table grouped by instrument type with unrealized/realized/dividends/total G/L columns. Bulk price entry for daily manual pricing. Last-known-price/rate logic for historical lookups. USD positions converted to PKR via ExchangeRate for portfolio totals. Uses purple accent color.
- **Portfolio performance:** Dedicated `/investments/performance/` page with flexible date ranges (1M/3M/6M/YTD/All/Custom). Dual-line chart: portfolio value (purple solid) vs net invested (gray dashed). Uses historical holdings per date (not current holdings). Computation engine in `investments/performance.py` uses 3 DB queries + bisect-based lookups. Daily sampling ≤90 days, weekly for longer ranges. Summary cards: portfolio value, net invested, total G/L, period change.
- **Dark mode:** Class-based strategy via `@custom-variant dark` in `theme/static_src/src/styles.css`. Theme preference stored in a `theme` cookie (light/dark/system), read synchronously in `<head>` to prevent flash. Toggle button in nav bar cycles through Light → Dark → System. No Django model needed — pure frontend. All templates use `dark:` Tailwind variants. Form `INPUT_CLASS` constants in each app's `forms.py` include dark variants.
- **JSON export/import:** `export_data` and `import_data` management commands in the `core` app. Exports/imports instruments, instrument_prices, investment_transactions, exchange_rates, tags, transaction_tags, loan_tags, and loan_repayments alongside other models. Import disconnects transaction/loan/investment signals during bulk create, then recalculates all account balances once at the end. Backward compatible — uses `data.get()` for new keys.
- **Mobile nav:** Hamburger menu (below `sm` breakpoint) with all nav links + action buttons. Desktop buttons hidden on mobile.
- **Active nav links:** `request.path` used to highlight current section with `text-emerald-600 font-semibold` (light) / `text-emerald-400` (dark) in both desktop and mobile menus.

## Conventions

- All templates extend `templates/base.html`
- App templates live in `<app>/templates/<app>/`; partials in a `partials/` subfolder
- Use `{% load currency %}` and the `|pkr` filter to format amounts
- Forms use Tailwind classes applied via `INPUT_CLASS` constant in each app's `forms.py` (includes dark mode variants)
- Views use Django's class-based generic views (ListView, CreateView, etc.)
- URL namespaces: `accounts:list`, `transactions:create`, `loans:list`, `recurring:list`, `budgets:overview`, `reports:hub`, `investments:list` (portfolio dashboard), `investments:performance`, `investments:instrument_list`, `investments:transaction_list`, `investments:bulk_prices`, `investments:exchange_rates`, `tags:list`, etc. Transfer create is a root-level name: `transfer_create`

## Build Phases

- **Phase 1 (Foundation):** DONE — accounts, transactions, transfers, dashboard
- **Phase 2 (Extended):** DONE — loans, recurring transactions, budgets
- **Phase 3 (Reporting):** DONE — reports app (Chart.js), transaction search/filter, CSV export, JSON export/import
- **Phase 4 (Polish):** DONE — investments app, mobile hamburger menu, active nav links, responsive grid tweaks
- **Phase 5 (Dark Mode):** DONE — class-based dark mode, theme toggle, cookie persistence, all templates updated
- **Phase 6 (Portfolio):** DONE — full investment portfolio tracking replacing simple investment log

See `requirements.md` for full spec. See `requirements-v2.md` for v2 feature specs.
