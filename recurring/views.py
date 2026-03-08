from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.mixins import UserScopedMixin

from .forms import RecurringRuleForm
from .models import RecurringRule


class RecurringRuleListView(UserScopedMixin, ListView):
    model = RecurringRule
    template_name = "recurring/rule_list.html"
    context_object_name = "rules"

    def get_queryset(self):
        return super().get_queryset().select_related("category", "account")


class RecurringRuleCreateView(UserScopedMixin, CreateView):
    model = RecurringRule
    form_class = RecurringRuleForm
    template_name = "recurring/rule_form.html"
    success_url = reverse_lazy("recurring:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Recurring rule created successfully.")
        return super().form_valid(form)


class RecurringRuleUpdateView(UserScopedMixin, UpdateView):
    model = RecurringRule
    form_class = RecurringRuleForm
    template_name = "recurring/rule_form.html"
    success_url = reverse_lazy("recurring:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Recurring rule updated successfully.")
        return super().form_valid(form)


class RecurringRuleDeleteView(UserScopedMixin, DeleteView):
    model = RecurringRule
    template_name = "recurring/rule_confirm_delete.html"
    success_url = reverse_lazy("recurring:list")

    def form_valid(self, form):
        messages.success(self.request, "Recurring rule deleted.")
        return super().form_valid(form)
