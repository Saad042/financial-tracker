# accounts app

Manages bank and cash accounts. Each account has a cached balance derived from transactions.

## Model: Account

- `name` (CharField), `account_type` (bank/cash), `balance` (DecimalField, cached), timestamps
- `recalculate_balance()` — aggregates income, expenses, transfers, and outstanding loans. Called by signals (from both `transactions` and `loans` apps), never manually.
- Balance formula: `income - expenses - transfers_out + transfers_in - outstanding_loans`
- **Do not set `balance` directly.** It is always recomputed from transactions and loans.

## Views

- `AccountListView` — card grid of all accounts
- `AccountCreateView` / `AccountUpdateView` — form for name + type
- `AccountDetailView` — account statement showing transactions and incoming transfers

## URLs (namespace: `accounts`)

- `accounts:list` → `/accounts/`
- `accounts:create` → `/accounts/create/`
- `accounts:detail` → `/accounts/<pk>/`
- `accounts:edit` → `/accounts/<pk>/edit/`

## Notes

- Account deletion is admin-only (not exposed in UI) due to `PROTECT` on transaction FKs.
- Templates are in `accounts/templates/accounts/`.
