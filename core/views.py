from datetime import timedelta
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
    InvestmentTransaction,
)
from loans.models import Loan, LoanRepayment
from recurring.models import RecurringRule
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
        today = now.date()
        month_start = now.replace(day=1).date()
        month_txns = Transaction.objects.filter(date__gte=month_start)

        month_income = (
            month_txns.filter(type=Transaction.INCOME)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        month_expenses = (
            month_txns.filter(type=Transaction.EXPENSE)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        context["month_income"] = month_income
        context["month_expenses"] = month_expenses
        context["month_net"] = month_income - month_expenses

        # Savings rate
        context["savings_rate"] = (
            ((month_income - month_expenses) / month_income * 100)
            if month_income
            else Decimal("0")
        )

        # Last month's income/expenses for month-over-month comparison
        last_month_end = month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        last_month_txns = Transaction.objects.filter(
            date__gte=last_month_start, date__lte=last_month_end
        )
        last_income = (
            last_month_txns.filter(type=Transaction.INCOME)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        last_expenses = (
            last_month_txns.filter(type=Transaction.EXPENSE)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        context["last_month_income"] = last_income
        context["last_month_expenses"] = last_expenses
        context["income_change_pct"] = (
            ((month_income - last_income) / last_income * 100)
            if last_income
            else None
        )
        context["expense_change_pct"] = (
            ((month_expenses - last_expenses) / last_expenses * 100)
            if last_expenses
            else None
        )

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

        # Overdue loan details
        overdue_loans = active_annotated.filter(expected_return__lt=today)
        context["loans_overdue_count"] = overdue_loans.count()
        context["overdue_loans"] = overdue_loans[:5]

        # Portfolio summary (matches PortfolioDashboardView logic)
        portfolio_value = Decimal("0.00")
        net_invested_pkr = Decimal("0.00")
        total_realized_pkr = Decimal("0.00")
        for inst in Instrument.objects.filter(is_active=True):
            holdings = inst.current_holdings
            price = inst.latest_price or Decimal("0")
            value = holdings * price if holdings > 0 else Decimal("0")
            net_cash = inst.net_cash_invested
            realized = inst.realized_gain_loss

            if inst.currency == Instrument.USD:
                rate = ExchangeRate.get_rate("USD", "PKR", today) or Decimal("1")
                net_cash_pkr = net_cash * rate
                realized_pkr = realized * rate
                value_pkr = value * rate if holdings > 0 else Decimal("0")
            else:
                net_cash_pkr = net_cash
                realized_pkr = realized
                value_pkr = value

            net_invested_pkr += net_cash_pkr
            total_realized_pkr += realized_pkr
            if holdings > 0:
                portfolio_value += value_pkr

        total_gain_loss = portfolio_value - net_invested_pkr
        total_gain_loss_pct = (
            (total_gain_loss / net_invested_pkr * 100)
            if net_invested_pkr
            else Decimal("0")
        )
        context["portfolio_value"] = portfolio_value
        context["net_invested_pkr"] = net_invested_pkr
        context["total_gain_loss"] = total_gain_loss
        context["total_gain_loss_pct"] = total_gain_loss_pct
        context["total_realized_pkr"] = total_realized_pkr
        context["has_investments"] = InvestmentTransaction.objects.exists()

        # Net Worth: cash + receivables + investments
        context["net_worth"] = (
            context["total_balance"]
            + context["loans_total_remaining"]
            + portfolio_value
        )

        # Top expense categories this month
        context["top_categories"] = (
            Transaction.objects.filter(
                type=Transaction.EXPENSE,
                date__gte=month_start,
                category__isnull=False,
            )
            .values("category__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:5]
        )

        # Budget alerts (warning or exceeded for current month)
        current_month = month_start
        budgets = Budget.objects.filter(month=current_month).select_related("category")
        context["budget_alerts"] = [
            b for b in budgets if b.status in ("warning", "exceeded")
        ]

        # Upcoming recurring transactions (active rules not yet generated this period)
        pending_rules = []
        for rule in RecurringRule.objects.filter(is_active=True).select_related(
            "category", "account"
        ):
            if rule.frequency == RecurringRule.MONTHLY:
                already = Transaction.objects.filter(
                    recurring_rule=rule,
                    date__year=month_start.year,
                    date__month=month_start.month,
                ).exists()
            else:
                already = Transaction.objects.filter(
                    recurring_rule=rule,
                    date__year=today.year,
                ).exists()
            if not already:
                pending_rules.append(rule)
        context["pending_recurring"] = pending_rules

        return context
