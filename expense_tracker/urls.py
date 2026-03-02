from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from core.views import DashboardView
from transactions.views import TransferCreateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", DashboardView.as_view(), name="dashboard"),
    path("accounts/", include("accounts.urls")),
    path("transactions/", include("transactions.urls")),
    path("transfers/add/", TransferCreateView.as_view(), name="transfer_create"),
    path("loans/", include("loans.urls")),
    path("recurring/", include("recurring.urls")),
    path("budgets/", include("budgets.urls")),
    path("reports/", include("reports.urls")),
    path("investments/", include("investments.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
