# loans app

Tracks money lent to others. Non-repaid loans (outstanding + partially_repaid) reduce the source account's balance.

## Model: Loan

- `borrower_name`, `amount`, `date_lent`, `expected_return` (nullable), `status` (outstanding/partially_repaid/repaid)
- `account` FK — the account the money was lent from
- `notes` (optional text), `date_repaid` (nullable), `repaid_to_account` FK (nullable, legacy from full-repay flow)
- Ordered by `-date_lent`
- Computed properties: `amount_repaid` (sum of repayments), `amount_remaining` (amount - amount_repaid)
- Status flow: outstanding → partially_repaid → repaid (auto-updated on repayment)

## Model: LoanRepayment

- `loan` FK (PROTECT), `date`, `amount`, `account` FK (PROTECT, related_name="loan_repayments_received"), `notes`, `created_at`
- Tracks individual partial repayments. Each repayment also creates an income Transaction ("Loan Repayment Received").
- Ordered by `-date, -created_at`

## Signals (signals.py)

Balance recalculation on loan changes (same pattern as transactions):
- `pre_save` captures old account ID
- `post_save` recalculates affected accounts (current + old)
- `post_delete` recalculates the loan's account

Signals are imported in `apps.py` → `ready()`.

## Forms

- `LoanForm` (ModelForm) — for creating loans: borrower_name, amount, date_lent, expected_return, account, notes
- `LoanRepaymentForm` (plain Form) — amount, date, account, notes. For recording partial repayments.

## Views

- `LoanListView` — all loans with annotated `total_repaid` and `annotated_remaining`. Context includes outstanding/partially_repaid counts and total remaining.
- `LoanCreateView` — standard create form. Passes tag context via `_get_loan_tag_context()` and saves tags via `_save_loan_tags()` in `form_valid`.
- `LoanDetailView` — loan info card, progress bar, repayment timeline, inline repayment form (if not repaid), forgive button. Shows tag chips via `loan_tags` context variable.
- `LoanRepayView` (POST only) — records partial repayment: creates LoanRepayment + income Transaction, auto-updates loan status.
- `LoanForgiveView` (POST only) — writes off remaining balance: creates expense Transaction ("Loan Written Off"), marks loan repaid.

## URLs (namespace: `loans`)

- `loans:list` → `/loans/`
- `loans:create` → `/loans/add/`
- `loans:detail` → `/loans/<pk>/`
- `loans:repay` → `/loans/<pk>/repay/`
- `loans:forgive` → `/loans/<pk>/forgive/`

## Notes

- Partial repayments create a Transaction (income) on the repayment account, not the original lending account.
- Forgiving a loan creates an expense Transaction ("Loan Written Off") on the lending account for the remaining amount.
- Balance formula includes both `outstanding` and `partially_repaid` loans via `exclude(status=REPAID)`.
- Templates are in `loans/templates/loans/`. Loan form includes `tags/partials/_tag_input_widget.html`. Loan detail shows tag chips.
- `_save_loan_tags(loan, post_data)` and `_get_loan_tag_context(loan=None)` are helper functions in `views.py` (same pattern as transactions).
