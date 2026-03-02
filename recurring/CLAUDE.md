# recurring app

Defines rules for automatically generating repeating transactions.

## Model: RecurringRule

- `name`, `amount`, `type` (income/expense), `category` FK, `account` FK
- `frequency` (monthly/annual), `day_of_month` (1–28), `is_active` (bool)
- Ordered by `name`

## Forms

- `RecurringRuleForm` (ModelForm) — all fields. Type select reuses HTMX `hx-get="/transactions/category-options/"` for dynamic category filtering. Validates category type matches rule type.

## Views

- `RecurringRuleListView` — table of all rules with status/type badges
- `RecurringRuleCreateView` / `RecurringRuleUpdateView` — create/edit form
- `RecurringRuleDeleteView` — confirmation page (notes that existing transactions are kept)

## URLs (namespace: `recurring`)

- `recurring:list` → `/recurring/`
- `recurring:create` → `/recurring/add/`
- `recurring:edit` → `/recurring/<pk>/edit/`
- `recurring:delete` → `/recurring/<pk>/delete/`

## Management Command

`generate_recurring` — creates transactions from active rules for the current period.
- Accepts optional `--date YYYY-MM-DD` (defaults to today)
- Idempotent: checks if a transaction already exists for the rule in the current month (monthly) or year (annual) before creating
- Sets `description="[Recurring] {rule.name}"` and `recurring_rule=rule` on created transactions

```bash
uv run python manage.py generate_recurring
uv run python manage.py generate_recurring --date 2026-04-01
```

## Notes

- Deleting a rule does NOT delete its previously generated transactions (`on_delete=SET_NULL` on `Transaction.recurring_rule`).
- Templates are in `recurring/templates/recurring/`.
