import json
from datetime import date, datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction
from django.db.models.signals import post_delete, post_save, pre_save

from accounts.models import Account
from budgets.models import Budget
from investments.models import (
    ExchangeRate,
    Instrument,
    InstrumentPrice,
    InvestmentTransaction,
)
from loans.models import Loan, LoanRepayment
from recurring.models import RecurringRule
from tags.models import LoanTag, Tag, TransactionTag
from transactions.models import Category, Transaction
from transactions.signals import (
    capture_old_transaction,
    update_balances_on_delete,
    update_balances_on_save,
)


def _parse_value(value, field_name):
    """Parse JSON values back to Python types based on field name patterns."""
    if value is None:
        return None
    if field_name in ("amount", "balance", "units", "price_per_unit", "total_amount", "brokerage_fee", "tax", "rate", "price", "initial_balance"):
        return Decimal(value)
    if field_name in ("date", "date_lent", "expected_return", "date_repaid", "month"):
        if isinstance(value, str):
            return date.fromisoformat(value)
        return value
    if field_name in ("created_at", "updated_at"):
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value
    return value


class Command(BaseCommand):
    help = "Import data from a JSON export file (full replace)"

    def add_arguments(self, parser):
        parser.add_argument("file", help="Path to the JSON export file")
        parser.add_argument(
            "--yes", action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        file_path = options["file"]

        try:
            with open(file_path) as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON: {e}")

        if "meta" not in data:
            raise CommandError("Invalid export file: missing 'meta' key")

        # Show summary
        self.stdout.write(f"Import file: {file_path}")
        self.stdout.write(f"Exported at: {data['meta'].get('exported_at', 'unknown')}")
        for key in ("accounts", "categories", "transactions", "loans", "loan_repayments", "recurring_rules", "budgets", "instruments", "instrument_prices", "investment_transactions", "exchange_rates", "tags", "transaction_tags", "loan_tags"):
            count = len(data.get(key, []))
            self.stdout.write(f"  {key}: {count} records")

        if not options["yes"]:
            confirm = input(
                "\nThis will DELETE all existing data and replace it. Continue? [y/N] "
            )
            if confirm.lower() != "y":
                self.stdout.write("Aborted.")
                return

        # Disconnect transaction/loan signals to avoid per-row balance recalc
        pre_save.disconnect(capture_old_transaction, sender=Transaction)
        post_save.disconnect(update_balances_on_save, sender=Transaction)
        post_delete.disconnect(update_balances_on_delete, sender=Transaction)

        # Also disconnect loan signals if they exist
        from loans import signals as loan_signals
        pre_save.disconnect(loan_signals.capture_old_loan, sender=Loan)
        post_save.disconnect(loan_signals.update_balances_on_loan_save, sender=Loan)
        post_delete.disconnect(loan_signals.update_balances_on_loan_delete, sender=Loan)

        # Disconnect investment transaction signals
        from investments import signals as investment_signals
        pre_save.disconnect(investment_signals.capture_old_investment_transaction, sender=InvestmentTransaction)
        post_save.disconnect(investment_signals.update_balances_on_investment_transaction_save, sender=InvestmentTransaction)
        post_delete.disconnect(investment_signals.update_balances_on_investment_transaction_delete, sender=InvestmentTransaction)

        try:
            with db_transaction.atomic():
                # Delete in reverse dependency order
                TransactionTag.objects.all().delete()
                LoanTag.objects.all().delete()
                LoanRepayment.objects.all().delete()
                Budget.objects.all().delete()
                InvestmentTransaction.objects.all().delete()
                InstrumentPrice.objects.all().delete()
                ExchangeRate.objects.all().delete()
                Instrument.objects.all().delete()
                Transaction.objects.all().delete()
                RecurringRule.objects.all().delete()
                Loan.objects.all().delete()
                Tag.objects.all().delete()
                Category.objects.all().delete()
                Account.objects.all().delete()

                # Restore in dependency order
                self._bulk_create(Account, data.get("accounts", []))
                self._bulk_create(Category, data.get("categories", []))
                self._bulk_create(Tag, data.get("tags", []))
                self._bulk_create(RecurringRule, data.get("recurring_rules", []))
                self._bulk_create(Transaction, data.get("transactions", []))
                self._bulk_create(Loan, data.get("loans", []))
                self._bulk_create(LoanRepayment, data.get("loan_repayments", []))
                self._bulk_create(Budget, data.get("budgets", []))
                self._bulk_create(Instrument, data.get("instruments", []))
                self._bulk_create(InstrumentPrice, data.get("instrument_prices", []))
                self._bulk_create(ExchangeRate, data.get("exchange_rates", []))
                self._bulk_create(InvestmentTransaction, data.get("investment_transactions", []))
                self._bulk_create(TransactionTag, data.get("transaction_tags", []))
                self._bulk_create(LoanTag, data.get("loan_tags", []))

                # Recalculate all account balances once
                for account in Account.objects.all():
                    account.recalculate_balance()

        finally:
            # Reconnect signals
            pre_save.connect(capture_old_transaction, sender=Transaction)
            post_save.connect(update_balances_on_save, sender=Transaction)
            post_delete.connect(update_balances_on_delete, sender=Transaction)

            pre_save.connect(loan_signals.capture_old_loan, sender=Loan)
            post_save.connect(loan_signals.update_balances_on_loan_save, sender=Loan)
            post_delete.connect(loan_signals.update_balances_on_loan_delete, sender=Loan)

            pre_save.connect(investment_signals.capture_old_investment_transaction, sender=InvestmentTransaction)
            post_save.connect(investment_signals.update_balances_on_investment_transaction_save, sender=InvestmentTransaction)
            post_delete.connect(investment_signals.update_balances_on_investment_transaction_delete, sender=InvestmentTransaction)

        self.stdout.write(self.style.SUCCESS("Import completed successfully."))

    def _bulk_create(self, model, records):
        """Create model instances from a list of dicts."""
        if not records:
            return
        instances = []
        for record in records:
            parsed = {}
            for key, value in record.items():
                parsed[key] = _parse_value(value, key)
            instances.append(model(**parsed))
        model.objects.bulk_create(instances)
        self.stdout.write(f"  Imported {len(instances)} {model.__name__} records")
