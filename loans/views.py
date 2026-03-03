from decimal import Decimal

from django.contrib import messages
from django.db.models import DecimalField, F, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from tags.models import LoanTag, Tag
from transactions.models import Category, Transaction

from .forms import LoanForm, LoanRepaymentForm
from .models import Loan, LoanRepayment

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
        repaid_subquery = (
            LoanRepayment.objects.filter(loan=OuterRef("pk"))
            .values("loan")
            .annotate(total=Sum("amount"))
            .values("total")
        )
        return (
            Loan.objects.select_related("account", "repaid_to_account")
            .annotate(
                total_repaid=Coalesce(
                    Subquery(repaid_subquery, output_field=DecimalField()),
                    Decimal("0.00"),
                ),
            )
            .annotate(
                annotated_remaining=F("amount") - Coalesce(
                    Subquery(repaid_subquery, output_field=DecimalField()),
                    Decimal("0.00"),
                ),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        non_repaid = Loan.objects.exclude(status=Loan.REPAID)
        context["outstanding_count"] = non_repaid.filter(status=Loan.OUTSTANDING).count()
        context["partially_repaid_count"] = non_repaid.filter(status=Loan.PARTIALLY_REPAID).count()

        # Total remaining across all non-repaid loans
        repaid_subquery = (
            LoanRepayment.objects.filter(loan=OuterRef("pk"))
            .values("loan")
            .annotate(total=Sum("amount"))
            .values("total")
        )
        non_repaid_annotated = non_repaid.annotate(
            total_repaid=Coalesce(
                Subquery(repaid_subquery, output_field=DecimalField()),
                Decimal("0.00"),
            )
        )
        total_lent = non_repaid_annotated.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        total_repaid = non_repaid_annotated.aggregate(total=Sum("total_repaid"))["total"] or Decimal("0.00")
        context["outstanding_total"] = total_lent - total_repaid
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
        loan = self.object

        # Tag context
        lt = LoanTag.objects.filter(loan=loan).select_related("tag")
        context["loan_tags"] = [t.tag for t in lt]

        # Repayment data
        context["repayments"] = loan.repayments.select_related("account").all()
        amount_repaid = loan.amount_repaid
        amount_remaining = loan.amount_remaining
        context["amount_repaid"] = amount_repaid
        context["amount_remaining"] = amount_remaining

        if loan.amount > 0:
            context["progress_percent"] = int((amount_repaid / loan.amount) * 100)
        else:
            context["progress_percent"] = 0

        # Show repayment form if loan is not fully repaid
        if loan.status != Loan.REPAID:
            context["repayment_form"] = LoanRepaymentForm(
                initial={"amount": amount_remaining}
            )

        return context


class LoanRepayView(View):
    def post(self, request, pk):
        loan = get_object_or_404(Loan.objects.exclude(status=Loan.REPAID), pk=pk)
        form = LoanRepaymentForm(request.POST)

        if form.is_valid():
            amount = form.cleaned_data["amount"]
            date = form.cleaned_data["date"]
            account = form.cleaned_data["account"]
            notes = form.cleaned_data["notes"]

            # Validate amount doesn't exceed remaining
            remaining = loan.amount_remaining
            if amount > remaining:
                messages.error(
                    request,
                    f"Repayment amount (PKR {amount}) exceeds remaining balance (PKR {remaining}).",
                )
                return redirect("loans:detail", pk=loan.pk)

            # Create LoanRepayment record
            LoanRepayment.objects.create(
                loan=loan,
                date=date,
                amount=amount,
                account=account,
                notes=notes,
            )

            # Create income transaction
            category = Category.objects.filter(
                name="Loan Repayment Received", type=Category.INCOME
            ).first()
            Transaction.objects.create(
                date=date,
                amount=amount,
                type=Transaction.INCOME,
                category=category,
                account=account,
                description=f"Loan repayment from {loan.borrower_name}",
            )

            # Update loan status
            new_repaid = loan.amount_repaid  # Re-query after creating repayment
            if new_repaid >= loan.amount:
                loan.status = Loan.REPAID
                loan.date_repaid = date
            elif new_repaid > 0:
                loan.status = Loan.PARTIALLY_REPAID
            loan.save()

            messages.success(
                request,
                f"Recorded repayment of PKR {amount} from {loan.borrower_name}.",
            )
            return redirect("loans:detail", pk=loan.pk)

        messages.error(request, "Please correct the errors below.")
        return redirect("loans:detail", pk=loan.pk)


class LoanForgiveView(View):
    def post(self, request, pk):
        loan = get_object_or_404(Loan.objects.exclude(status=Loan.REPAID), pk=pk)

        # Create expense transaction for the full loan amount written off
        category = Category.objects.filter(
            name="Loan Written Off", type=Category.EXPENSE
        ).first()
        Transaction.objects.create(
            date=timezone.now().date(),
            amount=loan.amount_remaining,
            type=Transaction.EXPENSE,
            category=category,
            account=loan.account,
            description=f"Loan to {loan.borrower_name} written off",
        )

        # Mark loan as repaid
        loan.status = Loan.REPAID
        loan.date_repaid = timezone.now().date()
        loan.save()

        messages.success(
            request,
            f"Remaining balance for loan to {loan.borrower_name} has been forgiven.",
        )
        return redirect("loans:detail", pk=loan.pk)
