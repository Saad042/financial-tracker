# transactions app

Handles categories, income/expense transactions, and inter-account transfers.

## Model: Category

- `name`, `type` (income/expense), `parent` (self-FK for sub-categories), `is_system` (bool)
- Unique constraint on `(name, type, parent)`
- 21 categories pre-seeded via `migrations/0002_seed_categories.py` with `is_system=True`
- `__str__` shows "Parent > Child" for sub-categories

## Model: Transaction

- `date`, `amount` (always positive), `type` (income/expense/transfer)
- `category` FK (nullable — transfers have no category)
- `account` FK — source for expense/transfer, destination for income
- `transfer_to` FK (nullable) — only set when `type="transfer"`
- `description` (optional text)
- `recurring_rule` FK (nullable, `on_delete=SET_NULL`) — links auto-generated transactions back to their `RecurringRule`
- Ordered by `-date, -created_at`

## Signals (signals.py)

Balance recalculation is triggered automatically:
- `pre_save` captures old account IDs (handles edits that change accounts)
- `post_save` recalculates balances on all affected accounts (current + old)
- `post_delete` recalculates balances on the deleted transaction's accounts

Signals are imported in `apps.py` → `ready()`.

## Forms

- `TransactionForm` — for income/expense. Validates category type matches transaction type. Type select has `hx-get` to dynamically filter the category dropdown.
- `TransferForm` — for transfers. Has `from_account`/`to_account` fields. Prevents same-account transfer. Sets `type=TRANSFER` and maps accounts in `save()`.
- `TransactionFilterForm` — plain Form (not ModelForm) for search/filtering on the transaction list. Fields: search, type, category, account, date_from/date_to, amount_min/amount_max.

## Views

- `TransactionListView` — paginated (25) with combinable filters. Returns `_transaction_table.html` partial when `request.htmx` is true (HTMX partial swap). Passes `TransactionFilterForm` in context.
- `TransactionCreateView` / `TransactionUpdateView` — uses `TransactionForm` or `TransferForm` depending on type
- `TransactionDeleteView` — confirmation page
- `TransferCreateView` — separate view for creating transfers
- `TransactionCSVExportView` — exports filtered transactions as CSV. Reuses `_apply_transaction_filters()`.
- `category_options` — HTMX endpoint returning `<option>` tags filtered by type
- `_apply_transaction_filters(qs, params)` — shared helper that applies GET params to a Transaction queryset. Used by list view and CSV export.

## URLs (namespace: `transactions`)

- `transactions:list` → `/transactions/`
- `transactions:create` → `/transactions/add/`
- `transactions:edit` → `/transactions/<pk>/edit/`
- `transactions:delete` → `/transactions/<pk>/delete/`
- `transactions:category_options` → `/transactions/category-options/`
- `transactions:export_csv` → `/transactions/export/csv/`
- Transfer create is at root level: `transfer_create` → `/transfers/add/`

## Templates

- `transactions/templates/transactions/` — list, form, delete confirmation, transfer form
- `transactions/templates/transactions/partials/_category_options.html` — HTMX partial for category dropdown
- `transactions/templates/transactions/partials/_transaction_table.html` — HTMX partial for transaction table + pagination. Pagination links use `{% querystring %}` to preserve filter params, with `hx-get` + `hx-target="#transaction-results"` + `hx-push-url="true"`.

## HTMX Filtering Pattern

The transaction list filter form uses `hx-get` targeting `#transaction-results`. The view detects `request.htmx` and returns only the `_transaction_table.html` partial (no full page layout). Pagination links inside the partial also use HTMX with `hx-push-url="true"` to update the browser URL.
