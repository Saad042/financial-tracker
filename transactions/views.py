import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.mixins import UserScopedMixin
from tags.models import Tag, TransactionTag

from .forms import TransactionFilterForm, TransactionForm, TransferForm
from .models import Category, Transaction

INPUT_CLASS = "w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-emerald-500 focus:ring-emerald-500"


def _save_transaction_tags(transaction, post_data):
    """Save tags from POST data for a transaction (full-replace)."""
    TransactionTag.objects.filter(transaction=transaction).delete()
    tag_ids = post_data.getlist("tags")
    if tag_ids:
        tags = Tag.objects.filter(pk__in=tag_ids)
        TransactionTag.objects.bulk_create(
            [TransactionTag(transaction=transaction, tag=tag) for tag in tags]
        )


def _get_tag_context(transaction=None, user=None):
    """Build tag context for transaction forms."""
    context = {"input_class": INPUT_CLASS}
    if transaction and transaction.pk:
        tt = TransactionTag.objects.filter(transaction=transaction).select_related("tag")
        context["existing_place_tags"] = [t.tag for t in tt if t.tag.tag_type == Tag.PLACE]
        context["existing_group_tags"] = [t.tag for t in tt if t.tag.tag_type == Tag.GROUP]
    else:
        context["existing_place_tags"] = []
        context["existing_group_tags"] = []
    return context


def _apply_transaction_filters(qs, params):
    """Apply filter params (from GET dict) to a Transaction queryset."""
    search = params.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(description__icontains=search)
            | Q(transaction_tags__tag__name__icontains=search)
        )

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

    tag_id = params.get("tag", "")
    if tag_id:
        qs = qs.filter(transaction_tags__tag_id=tag_id)

    tag_type = params.get("tag_type", "")
    if tag_type in ("place", "group"):
        qs = qs.filter(transaction_tags__tag__tag_type=tag_type)

    return qs.distinct()


class TransactionListView(UserScopedMixin, ListView):
    model = Transaction
    template_name = "transactions/transaction_list.html"
    context_object_name = "transactions"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            "category", "account", "transfer_to"
        ).prefetch_related("transaction_tags__tag")
        return _apply_transaction_filters(qs, self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = TransactionFilterForm(
            self.request.GET or None, user=self.request.user
        )
        return context

    def get_template_names(self):
        if self.request.htmx:
            return ["transactions/partials/_transaction_table.html"]
        return [self.template_name]


class TransactionCreateView(UserScopedMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "transactions/transaction_form.html"
    success_url = reverse_lazy("transactions:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_tag_context(user=self.request.user))
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        _save_transaction_tags(self.object, self.request.POST)
        messages.success(self.request, "Transaction added successfully.")
        return response


class TransactionUpdateView(UserScopedMixin, UpdateView):
    model = Transaction
    template_name = "transactions/transaction_form.html"
    success_url = reverse_lazy("transactions:list")

    def get_form_class(self):
        if self.object.type == Transaction.TRANSFER:
            return TransferForm
        return TransactionForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if self.object.type == Transaction.TRANSFER:
            initial["from_account"] = self.object.account
            initial["to_account"] = self.object.transfer_to
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_tag_context(self.object, user=self.request.user))
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        _save_transaction_tags(self.object, self.request.POST)
        messages.success(self.request, "Transaction updated successfully.")
        return response


class TransactionDeleteView(UserScopedMixin, DeleteView):
    model = Transaction
    template_name = "transactions/transaction_confirm_delete.html"
    success_url = reverse_lazy("transactions:list")

    def form_valid(self, form):
        messages.success(self.request, "Transaction deleted.")
        return super().form_valid(form)


class TransferCreateView(UserScopedMixin, CreateView):
    model = Transaction
    form_class = TransferForm
    template_name = "transactions/transfer_form.html"
    success_url = reverse_lazy("transactions:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_tag_context(user=self.request.user))
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        _save_transaction_tags(self.object, self.request.POST)
        messages.success(self.request, "Transfer recorded successfully.")
        return response


class TransactionCSVExportView(UserScopedMixin, View):
    """Export filtered transactions as CSV."""

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def get(self, request):
        qs = self.get_queryset().select_related(
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


@login_required
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
