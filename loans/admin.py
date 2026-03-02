from django.contrib import admin

from .models import Loan


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["borrower_name", "amount", "date_lent", "status", "account"]
    list_filter = ["status", "account"]
