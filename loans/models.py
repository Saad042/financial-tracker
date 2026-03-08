from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Loan(models.Model):
    OUTSTANDING = "outstanding"
    PARTIALLY_REPAID = "partially_repaid"
    REPAID = "repaid"
    STATUS_CHOICES = [
        (OUTSTANDING, "Outstanding"),
        (PARTIALLY_REPAID, "Partially Repaid"),
        (REPAID, "Repaid"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loans",
    )
    borrower_name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date_lent = models.DateField(default=timezone.now)
    expected_return = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=OUTSTANDING)
    account = models.ForeignKey(
        "accounts.Account", on_delete=models.PROTECT, related_name="loans"
    )
    notes = models.TextField(blank=True, default="")
    date_repaid = models.DateField(null=True, blank=True)
    repaid_to_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="loan_repayments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_lent"]

    def __str__(self):
        return f"Loan to {self.borrower_name}: PKR {self.amount}"

    @property
    def amount_repaid(self):
        return (
            self.repayments.aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

    @property
    def amount_remaining(self):
        return self.amount - self.amount_repaid


class LoanRepayment(models.Model):
    loan = models.ForeignKey(
        Loan, on_delete=models.PROTECT, related_name="repayments"
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="loan_repayments_received",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"Repayment of PKR {self.amount} for {self.loan}"
