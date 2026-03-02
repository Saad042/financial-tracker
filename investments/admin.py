from django.contrib import admin

from .models import Investment


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ["name", "amount", "date", "platform", "account"]
    list_filter = ["platform", "account"]
