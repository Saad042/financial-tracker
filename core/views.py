from decimal import Decimal

from django.db.models import DecimalField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.models import Account
from budgets.models import Budget
from investments.models import (
    ExchangeRate,
    Instrument,
    InstrumentPrice,
    InvestmentTransaction,
)
from loans.models import Loan, LoanRepayment
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

        # Active loans (outstanding + partially repaid)
        active_loans = Loan.objects.exclude(status=Loan.REPAID)
        context["loans_active_count"] = active_loans.count()

        loans_total_lent = (
            active_loans.aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        context["loans_total_lent"] = loans_total_lent

        repaid_subquery = (
            LoanRepayment.objects.filter(loan=OuterRef("pk"))
            .values("loan")
            .annotate(total=Sum("amount"))
            .values("total")
        )
        active_annotated = active_loans.annotate(
            total_repaid=Coalesce(
                Subquery(repaid_subquery, output_field=DecimalField()),
                Decimal("0.00"),
            )
        )
        loans_total_repaid = (
            active_annotated.aggregate(total=Sum("total_repaid"))["total"]
            or Decimal("0.00")
        )
        context["loans_total_repaid"] = loans_total_repaid
        context["loans_total_remaining"] = loans_total_lent - loans_total_repaid

        today = now.date()
        context["loans_overdue_count"] = active_loans.filter(
            expected_return__lt=today
        ).count()

        # Portfolio summary
        portfolio_value = Decimal("0.00")
        for inst in Instrument.objects.filter(is_active=True):
            holdings = inst.current_holdings
            if holdings <= 0:
                continue
            price = inst.latest_price
            if price is None:
                continue
            value = holdings * price
            if inst.currency == Instrument.USD:
                rate = ExchangeRate.get_rate("USD", "PKR", today) or Decimal("1")
                value = value * rate
            portfolio_value += value
        context["portfolio_value"] = portfolio_value
        context["has_investments"] = InvestmentTransaction.objects.exists()

        # Budget alerts (warning or exceeded for current month)
        current_month = month_start
        budgets = Budget.objects.filter(month=current_month).select_related("category")
        context["budget_alerts"] = [
            b for b in budgets if b.status in ("warning", "exceeded")
        ]

        return context
