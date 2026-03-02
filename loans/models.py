from django.db import models
from django.utils import timezone


class Loan(models.Model):
    OUTSTANDING = "outstanding"
    REPAID = "repaid"
    STATUS_CHOICES = [
        (OUTSTANDING, "Outstanding"),
        (REPAID, "Repaid"),
    ]

    borrower_name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date_lent = models.DateField(default=timezone.now)
    expected_return = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=OUTSTANDING)
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
