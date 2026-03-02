from django.urls import path

from . import views

app_name = "budgets"

urlpatterns = [
    path("", views.BudgetOverviewView.as_view(), name="overview"),
    path("set/", views.BudgetSetView.as_view(), name="set"),
    path("copy/", views.BudgetCopyView.as_view(), name="copy"),
]
