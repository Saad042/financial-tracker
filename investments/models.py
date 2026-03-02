from django.db import models
from django.utils import timezone


class Investment(models.Model):
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateField(default=timezone.now)
    platform = models.CharField(max_length=200, blank=True, default="")
    account = models.ForeignKey(
        "accounts.Account", on_delete=models.PROTECT, related_name="investments"
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.name}: PKR {self.amount}"
