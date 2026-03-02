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

## Views

- `TransactionListView` — paginated (25), shows all transactions
- `TransactionCreateView` / `TransactionUpdateView` — uses `TransactionForm` or `TransferForm` depending on type
- `TransactionDeleteView` — confirmation page
- `TransferCreateView` — separate view for creating transfers
- `category_options` — HTMX endpoint returning `<option>` tags filtered by type

## URLs (namespace: `transactions`)

- `transactions:list` → `/transactions/`
- `transactions:create` → `/transactions/add/`
- `transactions:edit` → `/transactions/<pk>/edit/`
- `transactions:delete` → `/transactions/<pk>/delete/`
- `transactions:category_options` → `/transactions/category-options/`
- Transfer create is at root level: `transfer_create` → `/transfers/add/`

## Templates

- `transactions/templates/transactions/` — list, form, delete confirmation, transfer form
- `transactions/templates/transactions/partials/_category_options.html` — HTMX partial for category dropdown
