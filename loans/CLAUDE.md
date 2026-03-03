# loans app

Tracks money lent to others. Outstanding loans reduce the source account's balance.

## Model: Loan

- `borrower_name`, `amount`, `date_lent`, `expected_return` (nullable), `status` (outstanding/repaid)
- `account` FK — the account the money was lent from
- `notes` (optional text), `date_repaid` (nullable), `repaid_to_account` FK (nullable)
- Ordered by `-date_lent`

## Signals (signals.py)

Balance recalculation on loan changes (same pattern as transactions):
- `pre_save` captures old account ID
- `post_save` recalculates affected accounts (current + old)
- `post_delete` recalculates the loan's account

Signals are imported in `apps.py` → `ready()`.

## Forms

- `LoanForm` (ModelForm) — for creating loans: borrower_name, amount, date_lent, expected_return, account, notes
- `LoanRepayForm` (plain Form) — date_repaid + repaid_to_account. Not a ModelForm because repay also creates a Transaction.

## Views

- `LoanListView` — all loans with outstanding total/count in context
- `LoanCreateView` — standard create form. Passes tag context via `_get_loan_tag_context()` and saves tags via `_save_loan_tags()` in `form_valid`.
- `LoanDetailView` — loan info card + inline repay form (if outstanding). Shows tag chips via `loan_tags` context variable.
- `LoanRepayView` (POST only) — marks loan repaid, creates income Transaction with "Loan Repayment Received" category

## URLs (namespace: `loans`)

- `loans:list` → `/loans/`
- `loans:create` → `/loans/add/`
- `loans:detail` → `/loans/<pk>/`
- `loans:repay` → `/loans/<pk>/repay/`

## Notes

- Repaying a loan creates a Transaction (income) on the `repaid_to_account`, not the original lending account.
- Templates are in `loans/templates/loans/`. Loan form includes `tags/partials/_tag_input_widget.html`. Loan detail shows tag chips.
- `_save_loan_tags(loan, post_data)` and `_get_loan_tag_context(loan=None)` are helper functions in `views.py` (same pattern as transactions).
