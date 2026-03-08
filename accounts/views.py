from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import UserScopedMixin
from transactions.models import Transaction

from .forms import AccountForm
from .models import Account


class AccountListView(UserScopedMixin, ListView):
    model = Account
    template_name = "accounts/account_list.html"
    context_object_name = "accounts"


class AccountCreateView(UserScopedMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = "accounts/account_form.html"
    success_url = reverse_lazy("accounts:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.recalculate_balance()
        messages.success(self.request, "Account created successfully.")
        return response


class AccountUpdateView(UserScopedMixin, UpdateView):
    model = Account
    form_class = AccountForm
    template_name = "accounts/account_form.html"
    success_url = reverse_lazy("accounts:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        if "initial_balance" in form.changed_data:
            self.object.recalculate_balance()
        messages.success(self.request, "Account updated successfully.")
        return response


class AccountDetailView(UserScopedMixin, DetailView):
    model = Account
    template_name = "accounts/account_detail.html"
    context_object_name = "account"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["transactions"] = Transaction.objects.filter(
            account=self.object
        ).select_related("category", "transfer_to")[:50]
        context["incoming_transfers"] = Transaction.objects.filter(
            transfer_to=self.object, type=Transaction.TRANSFER
        ).select_related("account")[:50]
        return context
