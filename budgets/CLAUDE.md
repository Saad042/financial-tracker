# budgets app

Monthly spending budgets per expense category with progress tracking.

## Model: Budget

- `category` FK, `month` (DateField, always first of month), `amount`
- UniqueConstraint on `(category, month)`
- Computed properties (not stored):
  - `spent` — sum of expense transactions for this category + children in the budget month
  - `remaining` — `amount - spent`
  - `percent_used` — integer 0–100
  - `status` — `"safe"` (<80%), `"warning"` (80–99%), `"exceeded"` (>=100%)
- Ordered by `-month, category__name`

## Views

- `BudgetOverviewView` — all budgets for a selected month with progress bars, prev/next month navigation, totals summary, "Copy from Last Month" button
- `BudgetSetView` — form with one amount input per top-level expense category. Uses `update_or_create` to save. Clearing an amount deletes the budget.
- `BudgetCopyView` (POST only) — copies previous month's budgets to current month via `get_or_create` (won't overwrite existing)

Month is passed via `?month=YYYY-MM` query parameter; defaults to current month.

## URLs (namespace: `budgets`)

- `budgets:overview` → `/budgets/`
- `budgets:set` → `/budgets/set/`
- `budgets:copy` → `/budgets/copy/`

## Notes

- Budget alerts (warning + exceeded) are surfaced on the dashboard via `core/views.py`.
- Templates are in `budgets/templates/budgets/`.
- Uses `python-dateutil` (`relativedelta`) for month arithmetic.
