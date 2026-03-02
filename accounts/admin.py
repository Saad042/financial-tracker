from django.contrib import admin

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["name", "account_type", "balance", "updated_at"]
    list_filter = ["account_type"]
    readonly_fields = ["balance", "created_at", "updated_at"]
