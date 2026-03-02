from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import RecurringRuleForm
from .models import RecurringRule


class RecurringRuleListView(ListView):
    model = RecurringRule
    template_name = "recurring/rule_list.html"
    context_object_name = "rules"

    def get_queryset(self):
        return RecurringRule.objects.select_related("category", "account")


class RecurringRuleCreateView(CreateView):
    model = RecurringRule
    form_class = RecurringRuleForm
    template_name = "recurring/rule_form.html"
    success_url = reverse_lazy("recurring:list")

    def form_valid(self, form):
        messages.success(self.request, "Recurring rule created successfully.")
        return super().form_valid(form)


class RecurringRuleUpdateView(UpdateView):
    model = RecurringRule
    form_class = RecurringRuleForm
    template_name = "recurring/rule_form.html"
    success_url = reverse_lazy("recurring:list")

    def form_valid(self, form):
        messages.success(self.request, "Recurring rule updated successfully.")
        return super().form_valid(form)


class RecurringRuleDeleteView(DeleteView):
    model = RecurringRule
    template_name = "recurring/rule_confirm_delete.html"
    success_url = reverse_lazy("recurring:list")

    def form_valid(self, form):
        messages.success(self.request, "Recurring rule deleted.")
        return super().form_valid(form)
