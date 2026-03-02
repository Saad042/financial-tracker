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
```

Always run commands through `uv run` — the virtualenv is managed by uv.

## Project Layout

```
expense_tracker/     # Django project config (settings, root URLs, wsgi)
accounts/            # Account model (bank/cash), CRUD views
transactions/        # Category + Transaction models, balance signals, CRUD views
core/                # Dashboard view, shared template tags
theme/               # Tailwind CSS theme app (auto-generated, don't edit manually)
templates/           # Project-level templates (base.html, dashboard, partials)
```

## Architecture Decisions

- **Balance caching:** Account.balance is a cached DecimalField, recalculated via Django signals on every transaction save/delete. Never set balance directly — it's derived from transactions.
- **Transfers:** A single Transaction row with `type="transfer"`, `account` = source, `transfer_to` = destination. Not two rows.
- **Categories:** Pre-seeded via data migration (`0002_seed_categories.py`). System categories have `is_system=True`. Categories belong to the `transactions` app.
- **FK safety:** All foreign keys use `on_delete=PROTECT`. Accounts/categories cannot be deleted while transactions reference them.
- **HTMX:** Used for dynamic category dropdown filtering by transaction type. Pattern: `hx-get` on the type select triggers a view that returns `<option>` HTML.

## Conventions

- All templates extend `templates/base.html`
- App templates live in `<app>/templates/<app>/`; partials in a `partials/` subfolder
- Use `{% load currency %}` and the `|pkr` filter to format amounts
- Forms use Tailwind classes applied via widget attrs in the form class
- Views use Django's class-based generic views (ListView, CreateView, etc.)
- URL namespaces: `accounts:list`, `transactions:create`, etc. Transfer create is a root-level name: `transfer_create`

## Build Phases

- **Phase 1 (Foundation):** DONE — accounts, transactions, transfers, dashboard
- **Phase 2 (Extended):** loans, recurring transactions, budgets
- **Phase 3 (Reporting):** charts, search/filter, JSON/CSV export-import
- **Phase 4 (Polish):** budget alerts, responsive tweaks, investments

See `requirements.md` for full spec.
