import json
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from django.views.generic import TemplateView

from loans.models import Loan
from transactions.models import Category, Transaction


def _parse_month(request):
    """Parse ?month=YYYY-MM from query string, default to current month."""
    raw = request.GET.get("month", "")
    if raw:
        try:
            return date.fromisoformat(raw + "-01")
        except ValueError:
            pass
    return date.today().replace(day=1)


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def _json(data):
    return json.dumps(data, cls=_DecimalEncoder)


class MonthlyBreakdownView(TemplateView):
    template_name = "reports/monthly_breakdown.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month = _parse_month(self.request)
        context["month"] = month
        context["prev_month"] = (month - relativedelta(months=1)).strftime("%Y-%m")
        context["next_month"] = (month + relativedelta(months=1)).strftime("%Y-%m")

        # Current month expenses by parent category
        categories_data = self._get_month_data(month)
        context["categories"] = categories_data

        # Previous month data for comparison
        prev_month_date = month - relativedelta(months=1)
        prev_data = self._get_month_data(prev_month_date)
        context["prev_month_date"] = prev_month_date

        # Total spending
        context["total_spending"] = sum(c["total"] for c in categories_data)
        context["prev_total_spending"] = sum(c["total"] for c in prev_data)

        # Chart data — donut
        context["donut_labels"] = _json([c["name"] for c in categories_data if c["total"] > 0])
        context["donut_amounts"] = _json([c["total"] for c in categories_data if c["total"] > 0])

        # Chart data — comparison bar
        all_names = sorted(set(
            [c["name"] for c in categories_data] +
            [c["name"] for c in prev_data]
        ))
        prev_lookup = {c["name"]: c["total"] for c in prev_data}
        curr_lookup = {c["name"]: c["total"] for c in categories_data}
        context["bar_labels"] = _json(all_names)
        context["bar_current"] = _json([curr_lookup.get(n, Decimal("0")) for n in all_names])
        context["bar_previous"] = _json([prev_lookup.get(n, Decimal("0")) for n in all_names])
        context["bar_prev_label"] = prev_month_date.strftime("%b %Y")
        context["bar_curr_label"] = month.strftime("%b %Y")

        return context

    def _get_month_data(self, month):
        """Get expense breakdown by parent category for a given month."""
        parent_cats = Category.objects.filter(
            type=Category.EXPENSE, parent__isnull=True
        )
        results = []
        for cat in parent_cats:
            category_ids = [cat.id] + list(
                cat.children.values_list("id", flat=True)
            )
            total = (
                Transaction.objects.filter(
                    type=Transaction.EXPENSE,
                    category_id__in=category_ids,
                    date__year=month.year,
                    date__month=month.month,
                ).aggregate(total=Sum("amount"))["total"]
                or Decimal("0")
            )

            # Sub-category breakdown
            subcategories = []
            for child in cat.children.all():
                sub_total = (
                    Transaction.objects.filter(
                        type=Transaction.EXPENSE,
                        category_id=child.id,
                        date__year=month.year,
                        date__month=month.month,
                    ).aggregate(total=Sum("amount"))["total"]
                    or Decimal("0")
                )
                if sub_total > 0:
                    subcategories.append({"name": child.name, "total": sub_total})

            results.append({
                "name": cat.name,
                "total": total,
                "subcategories": sorted(subcategories, key=lambda x: x["total"], reverse=True),
            })

        return sorted(results, key=lambda x: x["total"], reverse=True)


class TrendsView(TemplateView):
    template_name = "reports/trends.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            months = int(self.request.GET.get("months", 6))
        except (ValueError, TypeError):
            months = 6
        if months not in (3, 6, 12):
            months = 6
        context["months"] = months

        today = date.today().replace(day=1)
        labels = []
        income_data = []
        expense_data = []
        net_data = []

        for i in range(months - 1, -1, -1):
            m = today - relativedelta(months=i)
            labels.append(m.strftime("%b %Y"))

            income = (
                Transaction.objects.filter(
                    type=Transaction.INCOME,
                    date__year=m.year,
                    date__month=m.month,
                ).aggregate(total=Sum("amount"))["total"]
                or Decimal("0")
            )
            expense = (
                Transaction.objects.filter(
                    type=Transaction.EXPENSE,
                    date__year=m.year,
                    date__month=m.month,
                ).aggregate(total=Sum("amount"))["total"]
                or Decimal("0")
            )

            income_data.append(income)
            expense_data.append(expense)
            net_data.append(income - expense)

        context["chart_labels"] = _json(labels)
        context["chart_income"] = _json(income_data)
        context["chart_expense"] = _json(expense_data)
        context["chart_net"] = _json(net_data)

        return context


class ReportHubView(TemplateView):
    template_name = "reports/report_hub.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = date.today()
        month_start = today.replace(day=1)

        # Top 5 spending categories this month
        parent_cats = Category.objects.filter(
            type=Category.EXPENSE, parent__isnull=True
        )
        top_spending = []
        for cat in parent_cats:
            category_ids = [cat.id] + list(
                cat.children.values_list("id", flat=True)
            )
            total = (
                Transaction.objects.filter(
                    type=Transaction.EXPENSE,
                    category_id__in=category_ids,
                    date__year=month_start.year,
                    date__month=month_start.month,
                ).aggregate(total=Sum("amount"))["total"]
                or Decimal("0")
            )
            if total > 0:
                top_spending.append({"name": cat.name, "total": total})

        top_spending.sort(key=lambda x: x["total"], reverse=True)
        context["top_spending"] = top_spending[:5]
        context["current_month"] = month_start

        # Total month spending
        context["month_total_spending"] = sum(c["total"] for c in top_spending)

        # Loan summary
        context["total_lent"] = (
            Loan.objects.aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )
        context["outstanding_count"] = Loan.objects.filter(
            status=Loan.OUTSTANDING
        ).count()
        context["repaid_count"] = Loan.objects.filter(
            status=Loan.REPAID
        ).count()
        context["outstanding_amount"] = (
            Loan.objects.filter(status=Loan.OUTSTANDING)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )

        # Recent loans
        context["recent_loans"] = Loan.objects.select_related("account")[:5]

        return context
