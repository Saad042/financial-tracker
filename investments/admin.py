from django.contrib import admin

from .models import ExchangeRate, Instrument, InstrumentPrice, InvestmentTransaction


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ["ticker", "name", "instrument_type", "currency", "platform", "is_active"]
    list_filter = ["instrument_type", "currency", "is_active"]
    search_fields = ["name", "ticker"]


@admin.register(InstrumentPrice)
class InstrumentPriceAdmin(admin.ModelAdmin):
    list_display = ["instrument", "date", "price"]
    list_filter = ["instrument", "date"]


@admin.register(InvestmentTransaction)
class InvestmentTransactionAdmin(admin.ModelAdmin):
    list_display = ["date", "instrument", "transaction_type", "units", "price_per_unit", "total_amount", "account"]
    list_filter = ["transaction_type", "instrument", "account"]


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ["date", "from_currency", "to_currency", "rate"]
    list_filter = ["from_currency", "to_currency"]
