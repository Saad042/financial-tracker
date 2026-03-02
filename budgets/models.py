from decimal import Decimal

from django.db import models


class Budget(models.Model):
    category = models.ForeignKey(
        "transactions.Category", on_delete=models.PROTECT, related_name="budgets"
    )
    month = models.DateField(help_text="First day of the month")
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["category", "month"], name="unique_budget_category_month"
            ),
        ]
        ordering = ["-month", "category__name"]

    def __str__(self):
        return f"{self.category.name} - {self.month.strftime('%b %Y')}: PKR {self.amount}"

    @property
    def spent(self):
        from transactions.models import Transaction

        # Sum expenses for this category and its children in the budget month
        category_ids = [self.category_id]
        child_ids = list(
            self.category.children.values_list("id", flat=True)
        )
        category_ids.extend(child_ids)

        total = (
            Transaction.objects.filter(
                type=Transaction.EXPENSE,
                category_id__in=category_ids,
                date__year=self.month.year,
                date__month=self.month.month,
            ).aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )
        return total

    @property
    def remaining(self):
        return self.amount - self.spent

    @property
    def percent_used(self):
        if self.amount == 0:
            return 0
        return min(int((self.spent / self.amount) * 100), 100)

    @property
    def status(self):
        pct = self.percent_used
        if pct >= 100:
            return "exceeded"
        elif pct >= 80:
            return "warning"
        return "safe"
