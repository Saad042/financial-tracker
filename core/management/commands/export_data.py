import json
from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

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


class DecimalDateEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        return super().default(o)


class Command(BaseCommand):
    help = "Export all app data to JSON file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="expense_tracker_export.json",
            help="Output file path (default: expense_tracker_export.json)",
        )
        parser.add_argument(
            "--user",
            type=str,
            help="Username to export data for (default: all users)",
        )

    def handle(self, *args, **options):
        user_filter = {}
        if options["user"]:
            try:
                user = User.objects.get(username=options["user"])
                user_filter = {"user": user}
                self.stdout.write(f"Exporting data for user: {user.username}")
            except User.DoesNotExist:
                self.stderr.write(f"User not found: {options['user']}")
                return

        data = {
            "meta": {
                "app": "expense_tracker",
                "version": "2.0",
                "exported_at": datetime.now().isoformat(),
            },
            "accounts": list(
                Account.objects.filter(**user_filter).values(
                    "id", "user_id", "name", "account_type", "balance",
                    "created_at", "updated_at",
                )
            ),
            "categories": list(
                Category.objects.values(
                    "id", "name", "type", "parent_id", "is_system",
                )
            ),
            "transactions": list(
                Transaction.objects.filter(**user_filter).values(
                    "id", "user_id", "date", "amount", "type", "category_id",
                    "account_id", "transfer_to_id", "description",
                    "recurring_rule_id", "created_at", "updated_at",
                )
            ),
            "loans": list(
                Loan.objects.filter(**user_filter).values(
                    "id", "user_id", "borrower_name", "amount", "date_lent",
                    "expected_return", "status", "account_id", "notes",
                    "date_repaid", "repaid_to_account_id", "created_at",
                )
            ),
            "loan_repayments": list(
                LoanRepayment.objects.values(
                    "id", "loan_id", "date", "amount", "account_id",
                    "notes", "created_at",
                )
            ),
            "recurring_rules": list(
                RecurringRule.objects.filter(**user_filter).values(
                    "id", "user_id", "name", "amount", "type", "category_id",
                    "account_id", "frequency", "day_of_month",
                    "is_active", "created_at",
                )
            ),
            "budgets": list(
                Budget.objects.filter(**user_filter).values(
                    "id", "user_id", "category_id", "month", "amount",
                )
            ),
            "instruments": list(
                Instrument.objects.filter(**user_filter).values(
                    "id", "user_id", "name", "ticker", "instrument_type", "currency",
                    "api_id", "platform", "notes", "is_active", "created_at",
                )
            ),
            "instrument_prices": list(
                InstrumentPrice.objects.values(
                    "id", "instrument_id", "date", "price", "created_at",
                )
            ),
            "investment_transactions": list(
                InvestmentTransaction.objects.filter(**user_filter).values(
                    "id", "user_id", "date", "instrument_id", "transaction_type",
                    "units", "price_per_unit", "total_amount",
                    "brokerage_fee", "tax", "account_id", "notes",
                    "created_at",
                )
            ),
            "exchange_rates": list(
                ExchangeRate.objects.values(
                    "id", "from_currency", "to_currency", "date",
                    "rate", "created_at",
                )
            ),
            "tags": list(
                Tag.objects.filter(**user_filter).values(
                    "id", "user_id", "name", "tag_type", "color", "description",
                    "is_active", "created_at",
                )
            ),
            "transaction_tags": list(
                TransactionTag.objects.values(
                    "id", "transaction_id", "tag_id", "created_at",
                )
            ),
            "loan_tags": list(
                LoanTag.objects.values(
                    "id", "loan_id", "tag_id", "created_at",
                )
            ),
        }

        output_path = options["output"]
        with open(output_path, "w") as f:
            json.dump(data, f, cls=DecimalDateEncoder, indent=2)

        counts = {k: len(v) for k, v in data.items() if k != "meta"}
        self.stdout.write(self.style.SUCCESS(
            f"Exported to {output_path}: "
            + ", ".join(f"{v} {k}" for k, v in counts.items())
        ))
