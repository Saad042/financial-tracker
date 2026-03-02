from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class RecurringRule(models.Model):
    INCOME = "income"
    EXPENSE = "expense"
    TYPE_CHOICES = [
        (INCOME, "Income"),
        (EXPENSE, "Expense"),
    ]

    MONTHLY = "monthly"
    ANNUAL = "annual"
    FREQUENCY_CHOICES = [
        (MONTHLY, "Monthly"),
        (ANNUAL, "Annual"),
    ]

    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category = models.ForeignKey(
        "transactions.Category", on_delete=models.PROTECT
    )
    account = models.ForeignKey(
        "accounts.Account", on_delete=models.PROTECT, related_name="recurring_rules"
    )
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default=MONTHLY)
    day_of_month = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text="Day of month (1-28)",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"
