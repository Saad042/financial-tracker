from django.urls import path

from . import views

app_name = "transactions"

urlpatterns = [
    path("", views.TransactionListView.as_view(), name="list"),
    path("add/", views.TransactionCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.TransactionUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.TransactionDeleteView.as_view(), name="delete"),
    path("category-options/", views.category_options, name="category_options"),
    path("export/csv/", views.TransactionCSVExportView.as_view(), name="export_csv"),
]
