from decimal import Decimal

from django.contrib import messages
from django.db.models import Sum
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from .forms import InvestmentForm
from .models import Investment


class InvestmentListView(ListView):
    model = Investment
    template_name = "investments/investment_list.html"
    context_object_name = "investments"

    def get_queryset(self):
        return Investment.objects.select_related("account")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_invested"] = (
            Investment.objects.aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        return context


class InvestmentCreateView(CreateView):
    model = Investment
    form_class = InvestmentForm
    template_name = "investments/investment_form.html"
    success_url = reverse_lazy("investments:list")

    def form_valid(self, form):
        messages.success(self.request, "Investment recorded successfully.")
        return super().form_valid(form)


class InvestmentDetailView(DetailView):
    model = Investment
    template_name = "investments/investment_detail.html"
    context_object_name = "investment"

    def get_queryset(self):
        return Investment.objects.select_related("account")
