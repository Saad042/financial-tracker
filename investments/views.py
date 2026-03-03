import json
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.db.models import F, Sum
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import ExchangeRateForm, InstrumentForm, InvestmentTransactionForm
from .models import (
    ExchangeRate,
    Instrument,
    InstrumentPrice,
    InvestmentTransaction,
)


# ---------------------------------------------------------------------------
# Portfolio Dashboard
# ---------------------------------------------------------------------------


class PortfolioDashboardView(TemplateView):
    template_name = "investments/portfolio_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        instruments = Instrument.objects.filter(is_active=True)
        holdings = []
        total_value_pkr = Decimal("0")
        total_cost_pkr = Decimal("0")
        total_realized_pkr = Decimal("0")
        pkr_exposure = Decimal("0")
        usd_exposure = Decimal("0")
        allocation_by_type = defaultdict(lambda: Decimal("0"))

        for inst in instruments:
            units = inst.current_holdings
            if units <= 0:
                continue

            price = inst.latest_price or Decimal("0")
            value = units * price
            avg_cost = inst.average_cost
            cost_basis = units * avg_cost
            gain_loss = value - cost_basis
            gain_loss_pct = (
                (gain_loss / cost_basis * 100) if cost_basis else Decimal("0")
            )
            realized = inst.realized_gain_loss

            # Convert to PKR for portfolio totals
            if inst.currency == Instrument.USD:
                rate = ExchangeRate.get_rate("USD", "PKR", today) or Decimal("1")
                value_pkr = value * rate
                cost_pkr = cost_basis * rate
                realized_pkr = realized * rate
                usd_exposure += value_pkr
            else:
                value_pkr = value
                cost_pkr = cost_basis
                realized_pkr = realized
                pkr_exposure += value_pkr

            total_value_pkr += value_pkr
            total_cost_pkr += cost_pkr
            total_realized_pkr += realized_pkr
            allocation_by_type[inst.get_instrument_type_display()] += value_pkr

            holdings.append(
                {
                    "instrument": inst,
                    "units": units,
                    "avg_cost": avg_cost,
                    "current_price": price,
                    "current_value": value,
                    "gain_loss": gain_loss,
                    "gain_loss_pct": gain_loss_pct,
                    "value_pkr": value_pkr,
                }
            )

        total_gain_loss = total_value_pkr - total_cost_pkr + total_realized_pkr
        total_gain_loss_pct = (
            (total_gain_loss / total_cost_pkr * 100)
            if total_cost_pkr
            else Decimal("0")
        )

        # Allocation chart data
        allocation_labels = list(allocation_by_type.keys())
        allocation_values = [float(v) for v in allocation_by_type.values()]

        # Performance data (last 30 days of portfolio value)
        performance_dates = []
        performance_values = []
        for i in range(30, -1, -1):
            d = today - timedelta(days=i)
            day_value = Decimal("0")
            for inst in instruments:
                units = inst.current_holdings
                if units <= 0:
                    continue
                price = InstrumentPrice.get_price(inst, d)
                if price is None:
                    continue
                val = units * price
                if inst.currency == Instrument.USD:
                    rate = ExchangeRate.get_rate("USD", "PKR", d) or Decimal("1")
                    val = val * rate
                day_value += val
            performance_dates.append(d.isoformat())
            performance_values.append(float(day_value))

        context.update(
            {
                "holdings": holdings,
                "total_value_pkr": total_value_pkr,
                "total_cost_pkr": total_cost_pkr,
                "total_gain_loss": total_gain_loss,
                "total_gain_loss_pct": total_gain_loss_pct,
                "total_realized_pkr": total_realized_pkr,
                "pkr_exposure": pkr_exposure,
                "usd_exposure": usd_exposure,
                "allocation_labels": json.dumps(allocation_labels),
                "allocation_values": json.dumps(allocation_values),
                "performance_dates": json.dumps(performance_dates),
                "performance_values": json.dumps(performance_values),
            }
        )
        return context


# ---------------------------------------------------------------------------
# Instrument CRUD
# ---------------------------------------------------------------------------


class InstrumentListView(ListView):
    model = Instrument
    template_name = "investments/instrument_list.html"
    context_object_name = "instruments"


class InstrumentCreateView(CreateView):
    model = Instrument
    form_class = InstrumentForm
    template_name = "investments/instrument_form.html"
    success_url = reverse_lazy("investments:instrument_list")

    def form_valid(self, form):
        messages.success(self.request, "Instrument added successfully.")
        return super().form_valid(form)


class InstrumentUpdateView(UpdateView):
    model = Instrument
    form_class = InstrumentForm
    template_name = "investments/instrument_form.html"

    def get_success_url(self):
        return reverse_lazy("investments:instrument_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Instrument updated successfully.")
        return super().form_valid(form)


class InstrumentDetailView(DetailView):
    model = Instrument
    template_name = "investments/instrument_detail.html"
    context_object_name = "instrument"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        inst = self.object
        context["prices"] = inst.prices.all()[:30]
        context["transactions"] = inst.transactions.select_related("account").all()[:30]
        context["holdings"] = inst.current_holdings
        context["avg_cost"] = inst.average_cost
        context["current_value"] = inst.current_value
        context["unrealized_gl"] = inst.unrealized_gain_loss
        context["unrealized_gl_pct"] = inst.unrealized_gain_loss_percent
        context["realized_gl"] = inst.realized_gain_loss

        # Price chart data
        prices = list(
            inst.prices.order_by("date").values_list("date", "price")[:90]
        )
        context["price_dates"] = json.dumps([p[0].isoformat() for p in prices])
        context["price_values"] = json.dumps([float(p[1]) for p in prices])
        return context


# ---------------------------------------------------------------------------
# Investment Transactions
# ---------------------------------------------------------------------------


class InvestmentTransactionListView(ListView):
    model = InvestmentTransaction
    template_name = "investments/transaction_list.html"
    context_object_name = "transactions"

    def get_queryset(self):
        qs = InvestmentTransaction.objects.select_related("instrument", "account")
        instrument_id = self.request.GET.get("instrument")
        if instrument_id:
            qs = qs.filter(instrument_id=instrument_id)
        tx_type = self.request.GET.get("type")
        if tx_type in ("buy", "sell"):
            qs = qs.filter(transaction_type=tx_type)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["instruments"] = Instrument.objects.filter(is_active=True)
        context["selected_instrument"] = self.request.GET.get("instrument", "")
        context["selected_type"] = self.request.GET.get("type", "")
        return context


class InvestmentTransactionCreateView(CreateView):
    model = InvestmentTransaction
    form_class = InvestmentTransactionForm
    template_name = "investments/transaction_form.html"
    success_url = reverse_lazy("investments:transaction_list")

    def form_valid(self, form):
        messages.success(self.request, "Transaction recorded successfully.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Bulk Price Entry
# ---------------------------------------------------------------------------


class BulkPriceEntryView(TemplateView):
    template_name = "investments/bulk_price_entry.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        selected_date = self.request.GET.get("date", today.isoformat())
        context["selected_date"] = selected_date

        instruments = Instrument.objects.filter(is_active=True)
        instrument_data = []
        for inst in instruments:
            # Get existing price for selected date
            existing = InstrumentPrice.objects.filter(
                instrument=inst, date=selected_date
            ).first()
            # Get yesterday's price as placeholder
            yesterday_price = InstrumentPrice.get_price(
                inst, today - timedelta(days=1)
            )
            instrument_data.append(
                {
                    "instrument": inst,
                    "existing_price": existing.price if existing else "",
                    "placeholder": str(yesterday_price) if yesterday_price else "",
                }
            )
        context["instrument_data"] = instrument_data
        return context

    def post(self, request, *args, **kwargs):
        date = request.POST.get("price_date", timezone.now().date().isoformat())
        instruments = Instrument.objects.filter(is_active=True)
        count = 0
        for inst in instruments:
            price_val = request.POST.get(f"price_{inst.pk}", "").strip()
            if price_val:
                InstrumentPrice.objects.update_or_create(
                    instrument=inst,
                    date=date,
                    defaults={"price": Decimal(price_val)},
                )
                count += 1
        messages.success(request, f"Updated prices for {count} instrument(s).")
        return redirect(f"{reverse_lazy('investments:bulk_prices')}?date={date}")


# ---------------------------------------------------------------------------
# Price History
# ---------------------------------------------------------------------------


class PriceHistoryView(ListView):
    model = InstrumentPrice
    template_name = "investments/price_history.html"
    context_object_name = "prices"
    paginate_by = 50

    def get_queryset(self):
        qs = InstrumentPrice.objects.select_related("instrument")
        instrument_id = self.request.GET.get("instrument")
        if instrument_id:
            qs = qs.filter(instrument_id=instrument_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["instruments"] = Instrument.objects.filter(is_active=True)
        context["selected_instrument"] = self.request.GET.get("instrument", "")
        return context


# ---------------------------------------------------------------------------
# Exchange Rates
# ---------------------------------------------------------------------------


class ExchangeRateListView(ListView):
    model = ExchangeRate
    template_name = "investments/exchange_rate_list.html"
    context_object_name = "rates"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = ExchangeRateForm()
        return context

    def post(self, request, *args, **kwargs):
        form = ExchangeRateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Exchange rate added.")
            return redirect("investments:exchange_rates")
        # Re-render with errors
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        context["form"] = form
        return self.render_to_response(context)
