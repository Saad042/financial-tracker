from django.urls import path

from . import views

app_name = "loans"

urlpatterns = [
    path("", views.LoanListView.as_view(), name="list"),
    path("add/", views.LoanCreateView.as_view(), name="create"),
    path("<int:pk>/", views.LoanDetailView.as_view(), name="detail"),
    path("<int:pk>/repay/", views.LoanRepayView.as_view(), name="repay"),
    path("<int:pk>/forgive/", views.LoanForgiveView.as_view(), name="forgive"),
]
