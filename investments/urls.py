from django.urls import path

from . import views

app_name = "investments"

urlpatterns = [
    path("", views.InvestmentListView.as_view(), name="list"),
    path("add/", views.InvestmentCreateView.as_view(), name="create"),
    path("<int:pk>/", views.InvestmentDetailView.as_view(), name="detail"),
]
