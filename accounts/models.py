from decimal import Decimal

from django.db import models


class Account(models.Model):
    BANK = "bank"
    CASH = "cash"
    ACCOUNT_TYPE_CHOICES = [
        (BANK, "Bank"),
        (CASH, "Cash"),
    ]

    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPE_CHOICES)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"

    def recalculate_balance(self):
        from transactions.models import Transaction

        income = (
            Transaction.objects.filter(account=self, type=Transaction.INCOME)
            .aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )
        expense = (
            Transaction.objects.filter(account=self, type=Transaction.EXPENSE)
            .aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )
        transfers_out = (
            Transaction.objects.filter(account=self, type=Transaction.TRANSFER)
            .aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )
        transfers_in = (
            Transaction.objects.filter(transfer_to=self, type=Transaction.TRANSFER)
            .aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )

        from loans.models import Loan

        loans_out = (
            Loan.objects.filter(account=self, status=Loan.OUTSTANDING)
            .aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )

        self.balance = income - expense - transfers_out + transfers_in - loans_out
        self.save(update_fields=["balance", "updated_at"])
