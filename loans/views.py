from decimal import Decimal

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from tags.models import LoanTag, Tag
from transactions.models import Category, Transaction

from .forms import LoanForm, LoanRepayForm
from .models import Loan

INPUT_CLASS = "w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-emerald-500 focus:ring-emerald-500"


def _save_loan_tags(loan, post_data):
    """Save tags from POST data for a loan (full-replace)."""
    LoanTag.objects.filter(loan=loan).delete()
    tag_ids = post_data.getlist("tags")
    if tag_ids:
        tags = Tag.objects.filter(pk__in=tag_ids)
        LoanTag.objects.bulk_create(
            [LoanTag(loan=loan, tag=tag) for tag in tags]
        )


def _get_loan_tag_context(loan=None):
    """Build tag context for loan forms."""
    context = {"input_class": INPUT_CLASS}
    if loan and loan.pk:
        lt = LoanTag.objects.filter(loan=loan).select_related("tag")
        context["existing_place_tags"] = [t.tag for t in lt if t.tag.tag_type == Tag.PLACE]
        context["existing_group_tags"] = [t.tag for t in lt if t.tag.tag_type == Tag.GROUP]
    else:
        context["existing_place_tags"] = []
        context["existing_group_tags"] = []
    return context


class LoanListView(ListView):
    model = Loan
    template_name = "loans/loan_list.html"
    context_object_name = "loans"

    def get_queryset(self):
        return Loan.objects.select_related("account", "repaid_to_account")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        outstanding = Loan.objects.filter(status=Loan.OUTSTANDING)
        context["outstanding_total"] = (
            outstanding.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        )
        context["outstanding_count"] = outstanding.count()
        return context


class LoanCreateView(CreateView):
    model = Loan
    form_class = LoanForm
    template_name = "loans/loan_form.html"
    success_url = reverse_lazy("loans:list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_loan_tag_context())
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        _save_loan_tags(self.object, self.request.POST)
        messages.success(self.request, "Loan recorded successfully.")
        return response


class LoanDetailView(DetailView):
    model = Loan
    template_name = "loans/loan_detail.html"
    context_object_name = "loan"

    def get_queryset(self):
        return Loan.objects.select_related("account", "repaid_to_account")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.status == Loan.OUTSTANDING:
            context["repay_form"] = LoanRepayForm()
        lt = LoanTag.objects.filter(loan=self.object).select_related("tag")
        context["loan_tags"] = [t.tag for t in lt]
        return context


class LoanRepayView(View):
    def post(self, request, pk):
        loan = get_object_or_404(Loan, pk=pk, status=Loan.OUTSTANDING)
        form = LoanRepayForm(request.POST)

        if form.is_valid():
            repaid_to_account = form.cleaned_data["repaid_to_account"]
            date_repaid = form.cleaned_data["date_repaid"]

            # Mark loan as repaid
            loan.status = Loan.REPAID
            loan.date_repaid = date_repaid
            loan.repaid_to_account = repaid_to_account
            loan.save()

            # Create income transaction for the repayment
            category = Category.objects.filter(
                name="Loan Repayment Received", type=Category.INCOME
            ).first()

            Transaction.objects.create(
                date=date_repaid,
                amount=loan.amount,
                type=Transaction.INCOME,
                category=category,
                account=repaid_to_account,
                description=f"Loan repayment from {loan.borrower_name}",
            )

            messages.success(request, f"Loan from {loan.borrower_name} marked as repaid.")
            return redirect("loans:detail", pk=loan.pk)

        messages.error(request, "Please correct the errors below.")
        return redirect("loans:detail", pk=loan.pk)
