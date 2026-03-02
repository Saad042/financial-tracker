from datetime import date
from decimal import Decimal, InvalidOperation

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from transactions.models import Category

from .models import Budget


def _parse_month(request):
    """Parse ?month=YYYY-MM from query string, default to current month."""
    raw = request.GET.get("month", "")
    if raw:
        try:
            return date.fromisoformat(raw + "-01")
        except ValueError:
            pass
    return date.today().replace(day=1)


class BudgetOverviewView(TemplateView):
    template_name = "budgets/budget_overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month = _parse_month(self.request)
        budgets = (
            Budget.objects.filter(month=month)
            .select_related("category")
        )

        context["month"] = month
        context["budgets"] = budgets
        context["prev_month"] = (month - relativedelta(months=1)).strftime("%Y-%m")
        context["next_month"] = (month + relativedelta(months=1)).strftime("%Y-%m")

        total_budgeted = sum(b.amount for b in budgets)
        total_spent = sum(b.spent for b in budgets)
        context["total_budgeted"] = total_budgeted
        context["total_spent"] = total_spent
        context["total_remaining"] = total_budgeted - total_spent

        return context


class BudgetSetView(TemplateView):
    template_name = "budgets/budget_set.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month = _parse_month(self.request)
        context["month"] = month

        # Get top-level expense categories
        categories = Category.objects.filter(type=Category.EXPENSE, parent__isnull=True)
        existing = {
            b.category_id: b.amount
            for b in Budget.objects.filter(month=month)
        }
        context["categories"] = [
            {"category": cat, "amount": existing.get(cat.id, "")}
            for cat in categories
        ]
        return context

    def post(self, request, *args, **kwargs):
        month = _parse_month(request)
        categories = Category.objects.filter(type=Category.EXPENSE, parent__isnull=True)

        count = 0
        for cat in categories:
            raw_amount = request.POST.get(f"amount_{cat.id}", "").strip()
            if raw_amount:
                try:
                    amount = Decimal(raw_amount)
                except InvalidOperation:
                    continue
                if amount > 0:
                    Budget.objects.update_or_create(
                        category=cat,
                        month=month,
                        defaults={"amount": amount},
                    )
                    count += 1
            else:
                # Remove budget if amount is cleared
                Budget.objects.filter(category=cat, month=month).delete()

        messages.success(request, f"Budgets updated ({count} categories).")
        return redirect(f"/budgets/?month={month.strftime('%Y-%m')}")


class BudgetCopyView(View):
    def post(self, request):
        month = _parse_month(request)
        prev_month = month - relativedelta(months=1)

        prev_budgets = Budget.objects.filter(month=prev_month)
        if not prev_budgets.exists():
            messages.warning(request, "No budgets found for the previous month.")
            return redirect(f"/budgets/?month={month.strftime('%Y-%m')}")

        count = 0
        for budget in prev_budgets:
            _, created = Budget.objects.get_or_create(
                category=budget.category,
                month=month,
                defaults={"amount": budget.amount},
            )
            if created:
                count += 1

        messages.success(request, f"Copied {count} budget(s) from {prev_month.strftime('%b %Y')}.")
        return redirect(f"/budgets/?month={month.strftime('%Y-%m')}")
