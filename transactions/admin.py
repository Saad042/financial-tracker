from django.contrib import admin

from .models import Category, Transaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "parent", "is_system"]
    list_filter = ["type", "is_system"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["date", "type", "amount", "category", "account", "transfer_to"]
    list_filter = ["type", "date", "account"]
    date_hierarchy = "date"
