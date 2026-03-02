# Expense Tracker — Requirements Document

## Overview

A personal expense tracking web application built with Django and SQLite. Manages multiple bank accounts, tracks spending across defined categories, monitors loans, and records income — all in PKR. Portable across machines by copying the SQLite database file, with additional JSON export/import support.

---

## Tech Stack

### Backend

- **Framework:** Django (Python)
- **Database:** SQLite (single `.db` file for portability)
- **ORM:** Django ORM with migrations
- **Admin:** Django Admin for direct data management and debugging

### Frontend

- **Templating:** Django Templates
- **Styling:** Tailwind CSS
- **Interactivity:** HTMX (dynamic UI without writing JavaScript)
- **Charts:** Chart.js

### Data Portability

- Django management commands for JSON export/import
- SQLite file can be directly copied between machines

---

## Project Structure

```
expense_tracker/
    manage.py
    expense_tracker/         # Project config
        settings.py
        urls.py
        wsgi.py
    accounts/                # Bank accounts and Cash wallet
    transactions/            # Income, expenses, transfers
    loans/                   # Loan tracking
    reports/                 # Dashboard, charts, reporting
    budgets/                 # Budget caps and alerts
    recurring/               # Recurring transaction rules
    core/                    # Shared utilities, management commands
        management/
            commands/
                export_data.py
                import_data.py
        templatetags/
```

---

## Build Phases

### Phase 1 — Foundation

- Project setup (Django, Tailwind, HTMX)
- Data models for accounts and transactions
- Account management (create, edit, view balances)
- Transaction CRUD (add, edit, delete income/expenses)
- Inter-account transfers
- Basic dashboard (total balance, per-account breakdown, recent transactions)

### Phase 2 — Extended Features

- Loan tracking (create, mark as repaid, dashboard widget)
- Recurring transaction rules and auto-generation
- Budgeting (set caps per category, progress bars)

### Phase 3 — Reporting and Data

- Monthly spending breakdown charts
- Month-over-month comparison
- Income vs expense trend charts
- Search and filtering across all transactions
- JSON export/import management commands
- CSV export

### Phase 4 — Polish

- Budget alert indicators (80% and 100% thresholds)
- Quality of life improvements based on real usage
- Investment data capture (log only, excluded from calculations)
- Mobile/tablet responsive tweaks

---

## Core Principles

- **Local-first:** Runs on localhost via `python manage.py runserver`. No external hosting.
- **Portable:** Copy the SQLite `.db` file or use JSON export/import to move data between machines.
- **Single currency:** All amounts in PKR.
- **Quick entry:** Adding a transaction should be fast and frictionless.

---

## Data Models

### Account

| Field | Type | Notes |
|-------|------|-------|
| id | AutoField | Primary key |
| name | CharField | e.g., "HBL Savings", "Cash" |
| account_type | CharField | choices: bank, cash |
| balance | DecimalField | Cached, updated on transaction changes |
| created_at | DateTimeField | Auto-set |
| updated_at | DateTimeField | Auto-set |

### Category

| Field | Type | Notes |
|-------|------|-------|
| id | AutoField | Primary key |
| name | CharField | e.g., "Commuting", "Food" |
| type | CharField | choices: income, expense |
| parent | ForeignKey(self) | Null for top-level, set for sub-categories |
| is_system | BooleanField | True for defaults, false for user-created |

Pre-seed via data migration with all defined categories and sub-categories.

### Transaction

| Field | Type | Notes |
|-------|------|-------|
| id | AutoField | Primary key |
| date | DateField | Defaults to today |
| amount | DecimalField | Always positive |
| type | CharField | choices: income, expense, transfer |
| category | ForeignKey(Category) | |
| account | ForeignKey(Account) | Source for expense/transfer, destination for income |
| transfer_to | ForeignKey(Account) | Null unless type is transfer |
| description | TextField | Optional |
| recurring_rule | ForeignKey(RecurringRule) | Null if one-off |
| created_at | DateTimeField | Auto-set |
| updated_at | DateTimeField | Auto-set |

**Balance computation:** sum of income − sum of expenses − transfers out + transfers in. Cache on Account model and update on transaction create/edit/delete.

### Loan

| Field | Type | Notes |
|-------|------|-------|
| id | AutoField | Primary key |
| borrower_name | CharField | Who you lent money to |
| amount | DecimalField | Total amount lent |
| date_lent | DateField | |
| expected_return | DateField | Nullable |
| status | CharField | choices: outstanding, repaid |
| account | ForeignKey(Account) | Account money was lent from |
| notes | TextField | Optional |
| date_repaid | DateField | Nullable |
| repaid_to_account | ForeignKey(Account) | Nullable |
| created_at | DateTimeField | Auto-set |

**Loan behavior:** Creating a loan deducts from source account but does NOT create an expense. Marking repaid creates an income transaction (loan repayment received). Excluded from all expense reports.

### RecurringRule

| Field | Type | Notes |
|-------|------|-------|
| id | AutoField | Primary key |
| name | CharField | e.g., "Netflix", "Edhi Foundation" |
| amount | DecimalField | Default amount |
| type | CharField | choices: income, expense |
| category | ForeignKey(Category) | |
| account | ForeignKey(Account) | |
| frequency | CharField | choices: monthly, annual |
| day_of_month | IntegerField | 1–28 recommended |
| is_active | BooleanField | Can be paused |
| created_at | DateTimeField | Auto-set |

Management command checks for pending entries and auto-generates transactions. Users can edit/delete individual occurrences without affecting the rule.

### Budget

| Field | Type | Notes |
|-------|------|-------|
| id | AutoField | Primary key |
| category | ForeignKey(Category) | One budget per category per month |
| month | DateField | First day of the month |
| amount | DecimalField | Cap in PKR |

Progress bars with yellow at 80%, red at 100%. Option to copy last month's budgets forward.

### Investment (data capture only)

| Field | Type | Notes |
|-------|------|-------|
| id | AutoField | Primary key |
| date | DateField | |
| amount | DecimalField | |
| name | CharField | Fund or stock name |
| platform | CharField | Optional |
| account | ForeignKey(Account) | Account debited |
| notes | TextField | Optional |
| created_at | DateTimeField | Auto-set |

Deducts from source account. Excluded from all spending calculations. Future: add `current_value`, `units`, `price_per_unit`.

---

## Expense Categories (pre-seeded)

- **Commuting:** Rideshare, Fuel, Car Maintenance, Parking & Tolls
- **Food:** Dining Out, Groceries
- **Charity:** (user adds specific organizations as sub-categories)
- **Subscriptions:** (user adds specific services as sub-categories)
- **General / Miscellaneous:** Clothing, Electronics, Medical, Home, Gifts, Personal Care (user can add more)

## Income Categories (pre-seeded)

- Salary
- Freelance / Side Income
- Loan Repayment Received
- Other

---

## Dashboard

At-a-glance financial snapshot:

- Total balance across all accounts (with per-account breakdown)
- This month's income vs expenses (net position)
- Spending breakdown by category (Chart.js pie/donut)
- Outstanding loans total and count
- Recent transactions (last 10–15)
- Budget alerts for categories approaching/exceeding limits
- Prominent quick-add transaction button

---

## Reporting and Insights

- Monthly breakdown by category and sub-category
- Month-over-month comparison (bar chart)
- Income vs Expense trend (line chart, selectable range)
- Per-account statements filtered by date range
- Top spending areas ranked
- Loan history with repayment timelines

---

## Data Portability

- **JSON Export** (`python manage.py export_data`): all accounts, categories, transactions, loans, recurring rules, budgets, investments, plus app version and export timestamp.
- **JSON Import** (`python manage.py import_data backup.json`): full replace in v1 (wipes and restores). Future: merge with conflict resolution.
- **CSV Export:** filtered transactions from the UI. Columns: date, amount, type, category, sub-category, account, description.

---

## Search and Filtering

- Keyword search on description and borrower name
- Filters: date range, category/sub-category, account, transaction type, amount range
- Combinable filters
- HTMX-powered instant results

---

## URL Structure

```
/                              Dashboard
/accounts/                     Account list
/accounts/create/              Create account
/accounts/<id>/                Account detail / statement
/accounts/<id>/edit/           Edit account
/transactions/                 Transaction list (search/filter)
/transactions/add/             Add transaction
/transactions/<id>/edit/       Edit transaction
/transactions/<id>/delete/     Delete transaction
/transfers/add/                Inter-account transfer
/loans/                        Loan list
/loans/add/                    Add loan
/loans/<id>/                   Loan detail
/loans/<id>/repay/             Mark as repaid
/recurring/                    Recurring rules list
/recurring/add/                Add rule
/recurring/<id>/edit/          Edit rule
/budgets/                      Budget overview (current month)
/budgets/set/                  Set/edit budgets
/reports/                      Reports hub
/reports/monthly/              Monthly breakdown
/reports/trends/               Trend charts
/investments/                  Investment log
/investments/add/              Add investment
/settings/export/              Export data
/settings/import/              Import data
```

---

## Future Enhancements (Out of Scope for v1)

- Investment portfolio tracking with live prices and gain/loss
- Partial loan repayments
- Receipt photo attachments
- Multi-currency support
- Data merge on import
- Mobile app / PWA
- Recurring transaction notifications/reminders
- Dark mode
- Tagging system for transactions
- Multi-user support
