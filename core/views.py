from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.models import Account
from transactions.models import Transaction


class DashboardView(TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        accounts = Account.objects.all()
        context["accounts"] = accounts
        context["total_balance"] = (
            accounts.aggregate(total=Sum("balance"))["total"] or Decimal("0.00")
        )

        # This month's income/expenses
        month_start = now.replace(day=1).date()
        month_txns = Transaction.objects.filter(date__gte=month_start)

        context["month_income"] = (
            month_txns.filter(type=Transaction.INCOME)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        context["month_expenses"] = (
            month_txns.filter(type=Transaction.EXPENSE)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        context["month_net"] = context["month_income"] - context["month_expenses"]

        # Recent transactions
        context["recent_transactions"] = (
            Transaction.objects.select_related("category", "account", "transfer_to")[:15]
        )

        return context
