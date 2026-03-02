# investments app

Tracks money invested (log only). Investments deduct from the source account's balance but are excluded from spending reports.

## Model: Investment

- `name` (CharField), `amount` (Decimal), `date` (DateField), `platform` (optional CharField)
- `account` FK — the account the money was invested from
- `notes` (optional text), `created_at`
- Ordered by `-date`

## Signals (signals.py)

Balance recalculation on investment changes (same pattern as `loans/signals.py`):
- `pre_save` captures old account ID
- `post_save` recalculates affected accounts (current + old)
- `post_delete` recalculates the investment's account

Signals are imported in `apps.py` → `ready()`.

## Forms

- `InvestmentForm` (ModelForm) — name, amount, date, platform, account, notes

## Views

- `InvestmentListView` — all investments with total invested summary
- `InvestmentCreateView` — standard create form (purple accent)
- `InvestmentDetailView` — investment info card with grid layout

## URLs (namespace: `investments`)

- `investments:list` → `/investments/`
- `investments:create` → `/investments/add/`
- `investments:detail` → `/investments/<pk>/`

## Notes

- Investments reduce account balance (subtracted in `recalculate_balance()`).
- Balance formula: `income - expenses - transfers_out + transfers_in - loans_out - investments_out`
- Uses purple accent color to distinguish from other sections.
- Templates are in `investments/templates/investments/`.
