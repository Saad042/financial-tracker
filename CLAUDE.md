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
core/                # Dashboard view, shared template tags
theme/               # Tailwind CSS theme app (auto-generated, don't edit manually)
templates/           # Project-level templates (base.html, dashboard, partials)
```

## Architecture Decisions

- **Balance caching:** Account.balance is a cached DecimalField, recalculated via Django signals on every transaction and loan save/delete. Never set balance directly — it's derived from transactions and loans.
- **Balance formula:** `income - expenses - transfers_out + transfers_in - outstanding_loans`
- **Transfers:** A single Transaction row with `type="transfer"`, `account` = source, `transfer_to` = destination. Not two rows.
- **Loans:** A single Loan row tracks money lent out. Outstanding loans reduce account balance. Repaying creates an income Transaction with "Loan Repayment Received" category.
- **Recurring:** RecurringRule defines repeating transactions. The `generate_recurring` management command creates Transaction rows (idempotent per period). Transaction has a nullable `recurring_rule` FK (`on_delete=SET_NULL`).
- **Budgets:** Budget = (category, month) pair with an amount. Properties compute `spent`, `remaining`, `percent_used`, `status` (safe/warning/exceeded). Budget alerts surface on the dashboard.
- **Categories:** Pre-seeded via data migration (`0002_seed_categories.py`). System categories have `is_system=True`. Categories belong to the `transactions` app.
- **FK safety:** All foreign keys use `on_delete=PROTECT`, except `Transaction.recurring_rule` which uses `SET_NULL` so deleting a rule orphans its transactions.
- **HTMX:** Used for dynamic category dropdown filtering by transaction type. Pattern: `hx-get` on the type select triggers a view that returns `<option>` HTML. Reused in recurring rule form.

## Conventions

- All templates extend `templates/base.html`
- App templates live in `<app>/templates/<app>/`; partials in a `partials/` subfolder
- Use `{% load currency %}` and the `|pkr` filter to format amounts
- Forms use Tailwind classes applied via widget attrs in the form class
- Views use Django's class-based generic views (ListView, CreateView, etc.)
- URL namespaces: `accounts:list`, `transactions:create`, `loans:list`, `recurring:list`, `budgets:overview`, etc. Transfer create is a root-level name: `transfer_create`

## Build Phases

- **Phase 1 (Foundation):** DONE — accounts, transactions, transfers, dashboard
- **Phase 2 (Extended):** DONE — loans, recurring transactions, budgets
- **Phase 3 (Reporting):** charts, search/filter, JSON/CSV export-import
- **Phase 4 (Polish):** budget alerts, responsive tweaks, investments

See `requirements.md` for full spec.
