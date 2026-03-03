from django.db import migrations


def backfill_repayments(apps, schema_editor):
    """Create a single full-amount LoanRepayment for each existing repaid loan."""
    Loan = apps.get_model("loans", "Loan")
    LoanRepayment = apps.get_model("loans", "LoanRepayment")
    for loan in Loan.objects.filter(status="repaid"):
        if not LoanRepayment.objects.filter(loan=loan).exists():
            LoanRepayment.objects.create(
                loan=loan,
                date=loan.date_repaid or loan.date_lent,
                amount=loan.amount,
                account_id=loan.repaid_to_account_id or loan.account_id,
            )


def reverse_backfill(apps, schema_editor):
    """Remove auto-generated repayment records."""
    # No-op: we can't distinguish backfilled from user-created records
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("loans", "0002_alter_loan_status_loanrepayment"),
    ]

    operations = [
        migrations.RunPython(backfill_repayments, reverse_backfill),
    ]
