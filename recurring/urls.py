from django.urls import path

from . import views

app_name = "recurring"

urlpatterns = [
    path("", views.RecurringRuleListView.as_view(), name="list"),
    path("add/", views.RecurringRuleCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.RecurringRuleUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.RecurringRuleDeleteView.as_view(), name="delete"),
]
