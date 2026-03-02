from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from transactions.models import Transaction

from .forms import AccountForm
from .models import Account


class AccountListView(ListView):
    model = Account
    template_name = "accounts/account_list.html"
    context_object_name = "accounts"


class AccountCreateView(CreateView):
    model = Account
    form_class = AccountForm
    template_name = "accounts/account_form.html"
    success_url = reverse_lazy("accounts:list")

    def form_valid(self, form):
        messages.success(self.request, "Account created successfully.")
        return super().form_valid(form)


class AccountUpdateView(UpdateView):
    model = Account
    form_class = AccountForm
    template_name = "accounts/account_form.html"
    success_url = reverse_lazy("accounts:list")

    def form_valid(self, form):
        messages.success(self.request, "Account updated successfully.")
        return super().form_valid(form)


class AccountDetailView(DetailView):
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
