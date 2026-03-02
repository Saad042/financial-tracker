from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import TransactionForm, TransferForm
from .models import Category, Transaction


class TransactionListView(ListView):
    model = Transaction
    template_name = "transactions/transaction_list.html"
    context_object_name = "transactions"
    paginate_by = 25

    def get_queryset(self):
        return Transaction.objects.select_related("category", "account", "transfer_to")


class TransactionCreateView(CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "transactions/transaction_form.html"
    success_url = reverse_lazy("transactions:list")

    def form_valid(self, form):
        messages.success(self.request, "Transaction added successfully.")
        return super().form_valid(form)


class TransactionUpdateView(UpdateView):
    model = Transaction
    template_name = "transactions/transaction_form.html"
    success_url = reverse_lazy("transactions:list")

    def get_form_class(self):
        if self.object.type == Transaction.TRANSFER:
            return TransferForm
        return TransactionForm

    def get_initial(self):
        initial = super().get_initial()
        if self.object.type == Transaction.TRANSFER:
            initial["from_account"] = self.object.account
            initial["to_account"] = self.object.transfer_to
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Transaction updated successfully.")
        return super().form_valid(form)


class TransactionDeleteView(DeleteView):
    model = Transaction
    template_name = "transactions/transaction_confirm_delete.html"
    success_url = reverse_lazy("transactions:list")

    def form_valid(self, form):
        messages.success(self.request, "Transaction deleted.")
        return super().form_valid(form)


class TransferCreateView(CreateView):
    model = Transaction
    form_class = TransferForm
    template_name = "transactions/transfer_form.html"
    success_url = reverse_lazy("transactions:list")

    def form_valid(self, form):
        messages.success(self.request, "Transfer recorded successfully.")
        return super().form_valid(form)


def category_options(request):
    """HTMX endpoint: return <option> tags filtered by transaction type."""
    txn_type = request.GET.get("type", "")
    categories = Category.objects.none()
    if txn_type in (Category.INCOME, Category.EXPENSE):
        categories = Category.objects.filter(type=txn_type)
    html = render_to_string(
        "transactions/partials/_category_options.html",
        {"categories": categories},
    )
    return HttpResponse(html)
