from django.contrib import admin

from .models import RecurringRule


@admin.register(RecurringRule)
class RecurringRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "amount", "type", "frequency", "day_of_month", "is_active"]
    list_filter = ["type", "frequency", "is_active"]
