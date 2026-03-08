from datetime import date

from django.core.management.base import BaseCommand

from recurring.models import RecurringRule
from transactions.models import Transaction


class Command(BaseCommand):
    help = "Generate transactions from active recurring rules for the current period."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Target date in YYYY-MM-DD format (defaults to today)",
        )

    def handle(self, *args, **options):
        if options["date"]:
            target_date = date.fromisoformat(options["date"])
        else:
            target_date = date.today()

        rules = RecurringRule.objects.filter(is_active=True).select_related(
            "category", "account"
        )
        created_count = 0

        for rule in rules:
            if rule.frequency == RecurringRule.MONTHLY:
                # Check if transaction already exists for this month
                period_start = target_date.replace(day=1)
                exists = Transaction.objects.filter(
                    recurring_rule=rule,
                    date__year=period_start.year,
                    date__month=period_start.month,
                ).exists()
            else:
                # Annual: check if transaction exists for this year
                exists = Transaction.objects.filter(
                    recurring_rule=rule,
                    date__year=target_date.year,
                ).exists()

            if exists:
                self.stdout.write(f"  Skipped: {rule.name} (already exists)")
                continue

            txn_date = target_date.replace(day=rule.day_of_month)

            Transaction.objects.create(
                user=rule.user,
                date=txn_date,
                amount=rule.amount,
                type=rule.type,
                category=rule.category,
                account=rule.account,
                description=f"[Recurring] {rule.name}",
                recurring_rule=rule,
            )
            created_count += 1
            self.stdout.write(self.style.SUCCESS(f"  Created: {rule.name}"))

        self.stdout.write(
            self.style.SUCCESS(f"\nDone. {created_count} transaction(s) created.")
        )
