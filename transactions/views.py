import csv

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import TransactionFilterForm, TransactionForm, TransferForm
from .models import Category, Transaction


def _apply_transaction_filters(qs, params):
    """Apply filter params (from GET dict) to a Transaction queryset."""
    search = params.get("search", "").strip()
    if search:
        qs = qs.filter(description__icontains=search)

    txn_type = params.get("type", "")
    if txn_type in ("income", "expense", "transfer"):
        qs = qs.filter(type=txn_type)

    category_id = params.get("category", "")
    if category_id:
        # Include the parent category and its children
        qs = qs.filter(
            Q(category_id=category_id) | Q(category__parent_id=category_id)
        )

    account_id = params.get("account", "")
    if account_id:
        qs = qs.filter(Q(account_id=account_id) | Q(transfer_to_id=account_id))

    date_from = params.get("date_from", "")
    if date_from:
        qs = qs.filter(date__gte=date_from)

    date_to = params.get("date_to", "")
    if date_to:
        qs = qs.filter(date__lte=date_to)

    amount_min = params.get("amount_min", "")
    if amount_min:
        qs = qs.filter(amount__gte=amount_min)

    amount_max = params.get("amount_max", "")
    if amount_max:
        qs = qs.filter(amount__lte=amount_max)

    return qs


class TransactionListView(ListView):
    model = Transaction
    template_name = "transactions/transaction_list.html"
    context_object_name = "transactions"
    paginate_by = 25

    def get_queryset(self):
        qs = Transaction.objects.select_related("category", "account", "transfer_to")
        return _apply_transaction_filters(qs, self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = TransactionFilterForm(self.request.GET or None)
        return context

    def get_template_names(self):
        if self.request.htmx:
            return ["transactions/partials/_transaction_table.html"]
        return [self.template_name]


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


class TransactionCSVExportView(View):
    """Export filtered transactions as CSV."""

    def get(self, request):
        qs = Transaction.objects.select_related(
            "category", "category__parent", "account", "transfer_to"
        )
        qs = _apply_transaction_filters(qs, request.GET)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="transactions.csv"'

        writer = csv.writer(response)
        writer.writerow(["Date", "Amount", "Type", "Category", "Sub-category", "Account", "Description"])

        for txn in qs.iterator():
            if txn.category and txn.category.parent:
                category = txn.category.parent.name
                subcategory = txn.category.name
            elif txn.category:
                category = txn.category.name
                subcategory = ""
            else:
                category = ""
                subcategory = ""

            writer.writerow([
                txn.date.isoformat(),
                str(txn.amount),
                txn.get_type_display(),
                category,
                subcategory,
                txn.account.name,
                txn.description,
            ])

        return response


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
