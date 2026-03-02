from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ReportHubView.as_view(), name="hub"),
    path("monthly/", views.MonthlyBreakdownView.as_view(), name="monthly"),
    path("trends/", views.TrendsView.as_view(), name="trends"),
]
