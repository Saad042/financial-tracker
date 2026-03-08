from django.conf import settings
from django.db import models


class Tag(models.Model):
    PLACE = "place"
    GROUP = "group"
    TYPE_CHOICES = [
        (PLACE, "Place"),
        (GROUP, "Group"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tags",
    )
    name = models.CharField(max_length=100)
    tag_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    color = models.CharField(max_length=7, blank=True, default="")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name", "tag_type"], name="unique_tag_user_name_type"
            ),
        ]
        ordering = ["tag_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_tag_type_display()})"

    @property
    def display_color(self):
        if self.color:
            return self.color
        return "#16a34a" if self.tag_type == self.PLACE else "#9333ea"


class TransactionTag(models.Model):
    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.CASCADE,
        related_name="transaction_tags",
    )
    tag = models.ForeignKey(Tag, on_delete=models.PROTECT, related_name="transaction_tags")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["transaction", "tag"], name="unique_transaction_tag"
            ),
        ]

    def __str__(self):
        return f"{self.transaction} - {self.tag}"


class LoanTag(models.Model):
    loan = models.ForeignKey(
        "loans.Loan",
        on_delete=models.CASCADE,
        related_name="loan_tags",
    )
    tag = models.ForeignKey(Tag, on_delete=models.PROTECT, related_name="loan_tags")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["loan", "tag"], name="unique_loan_tag"
            ),
        ]

    def __str__(self):
        return f"{self.loan} - {self.tag}"
