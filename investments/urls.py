from django.urls import path

from . import views

app_name = "investments"

urlpatterns = [
    # Portfolio dashboard
    path("", views.PortfolioDashboardView.as_view(), name="list"),
    # Instruments
    path("instruments/", views.InstrumentListView.as_view(), name="instrument_list"),
    path("instruments/add/", views.InstrumentCreateView.as_view(), name="instrument_create"),
    path("instruments/<int:pk>/", views.InstrumentDetailView.as_view(), name="instrument_detail"),
    path("instruments/<int:pk>/edit/", views.InstrumentUpdateView.as_view(), name="instrument_edit"),
    # Investment transactions
    path("transactions/", views.InvestmentTransactionListView.as_view(), name="transaction_list"),
    path("transactions/add/", views.InvestmentTransactionCreateView.as_view(), name="transaction_create"),
    # Prices
    path("prices/", views.BulkPriceEntryView.as_view(), name="bulk_prices"),
    path("prices/history/", views.PriceHistoryView.as_view(), name="price_history"),
    # Exchange rates
    path("exchange-rates/", views.ExchangeRateListView.as_view(), name="exchange_rates"),
]
