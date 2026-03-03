import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.db.models import F, Sum
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    ExchangeRateForm,
    InstrumentForm,
    InvestmentTransactionForm,
    PriceImportForm,
)
from .models import (
    ExchangeRate,
    Instrument,
    InstrumentPrice,
    InvestmentTransaction,
)
from .crypto_prices import get_fetch_status, start_background_fetch
from .performance import compute_portfolio_series, get_inception_date


# ---------------------------------------------------------------------------
# Portfolio Dashboard
# ---------------------------------------------------------------------------


class PortfolioDashboardView(TemplateView):
    template_name = "investments/portfolio_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        instruments = Instrument.objects.filter(is_active=True)
        holdings_by_type = defaultdict(list)
        total_value_pkr = Decimal("0")
        net_invested_pkr = Decimal("0")
        total_realized_pkr = Decimal("0")
        pkr_exposure = Decimal("0")
        usd_exposure = Decimal("0")
        allocation_by_type = defaultdict(lambda: Decimal("0"))

        for inst in instruments:
            units = inst.current_holdings
            price = inst.latest_price or Decimal("0")
            value = units * price if units > 0 else Decimal("0")
            avg_cost = inst.average_cost
            cost_basis = units * avg_cost if units > 0 else Decimal("0")
            gain_loss = value - cost_basis
            gain_loss_pct = (
                (gain_loss / cost_basis * 100) if cost_basis else Decimal("0")
            )
            realized = inst.realized_gain_loss
            reinvested = inst.total_reinvested
            dividends = inst.total_dividends

            # Convert to PKR for portfolio totals
            value_pkr = Decimal("0")
            net_cash = inst.net_cash_invested
            if inst.currency == Instrument.USD:
                rate = ExchangeRate.get_rate("USD", "PKR", today) or Decimal("1")
                realized_pkr = realized * rate
                net_cash_pkr = net_cash * rate
            else:
                rate = None
                realized_pkr = realized
                net_cash_pkr = net_cash

            # All instruments contribute to net invested and realized
            net_invested_pkr += net_cash_pkr
            total_realized_pkr += realized_pkr

            if units > 0:
                if rate:  # USD instrument
                    value_pkr = value * rate
                    usd_exposure += value_pkr
                else:
                    value_pkr = value
                    pkr_exposure += value_pkr

                total_value_pkr += value_pkr
                allocation_by_type[inst.get_instrument_type_display()] += value_pkr

            type_label = inst.get_instrument_type_display()
            total_gl = gain_loss + realized + dividends + reinvested

            # Percentage values (relative to total cost basis — all buys + reinvestments)
            total_cost = inst.total_cost_basis
            if total_cost:
                unrealized_pct = gain_loss / total_cost * 100
                realized_pct = realized / total_cost * 100
                reinvested_pct = reinvested / total_cost * 100
                dividends_pct = dividends / total_cost * 100
                total_gl_pct = total_gl / total_cost * 100
            else:
                unrealized_pct = realized_pct = reinvested_pct = Decimal("0")
                dividends_pct = total_gl_pct = Decimal("0")

            holdings_by_type[type_label].append(
                {
                    "instrument": inst,
                    "units": units,
                    "avg_cost": avg_cost,
                    "current_price": price,
                    "current_value": value,
                    "reinvested": reinvested,
                    "unrealized_gl": gain_loss,
                    "realized_gl": realized,
                    "dividends": dividends,
                    "total_gl": total_gl,
                    "reinvested_pct": reinvested_pct,
                    "unrealized_pct": unrealized_pct,
                    "realized_pct": realized_pct,
                    "dividends_pct": dividends_pct,
                    "total_gl_pct": total_gl_pct,
                    "value_pkr": value_pkr,
                }
            )

        # Total G/L = Portfolio Value - Net Invested (captures all cash flows)
        total_gain_loss = total_value_pkr - net_invested_pkr
        total_gain_loss_pct = (
            (total_gain_loss / net_invested_pkr * 100)
            if net_invested_pkr
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
                "holdings_by_type": dict(holdings_by_type),
                "total_value_pkr": total_value_pkr,
                "net_invested_pkr": net_invested_pkr,
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
        if tx_type in ("buy", "sell", "reinvestment", "dividend"):
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
        crypto_instruments = list(
            Instrument.objects.filter(
                instrument_type=Instrument.CRYPTO, is_active=True
            ).exclude(api_id="")
        )
        context["crypto_instruments"] = crypto_instruments
        context["has_crypto_api"] = len(crypto_instruments) > 0
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
# Fetch Crypto Prices
# ---------------------------------------------------------------------------


class FetchCryptoPricesView(View):
    def post(self, request, *args, **kwargs):
        ticker = request.POST.get("ticker", "").strip() or None
        start_date = None
        end_date = None
        if request.POST.get("start_date"):
            start_date = date.fromisoformat(request.POST["start_date"])
        if request.POST.get("end_date"):
            end_date = date.fromisoformat(request.POST["end_date"])

        started = start_background_fetch(
            ticker=ticker, start_date=start_date, end_date=end_date
        )
        if started:
            messages.info(request, "Fetching crypto prices in the background...")
        else:
            messages.warning(request, "A fetch is already in progress.")
        return redirect("investments:bulk_prices")

    def get(self, request, *args, **kwargs):
        return JsonResponse(get_fetch_status())


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


# ---------------------------------------------------------------------------
# Portfolio Performance
# ---------------------------------------------------------------------------


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def _json(data):
    return json.dumps(data, cls=_DecimalEncoder)


# ---------------------------------------------------------------------------
# Price Import from Excel
# ---------------------------------------------------------------------------


def _parse_date(value):
    """Parse a date from string or datetime object."""
    if isinstance(value, date):
        return value
    from datetime import datetime as dt

    text = str(value).strip()
    for fmt in ("%d-%b-%Y", "%d %b %Y", "%d-%B-%Y", "%d %B %Y", "%Y-%m-%d"):
        try:
            return dt.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _pick_price(repurchase_val, nav_val):
    """Prefer repurchase/redemption price; fall back to NAV."""
    try:
        rp = Decimal(str(repurchase_val))
        if rp > 0:
            return rp
    except (TypeError, ValueError, ArithmeticError):
        pass
    try:
        nv = Decimal(str(nav_val))
        if nv > 0:
            return nv
    except (TypeError, ValueError, ArithmeticError):
        pass
    return None


def _detect_format(all_rows):
    """Return 'meezan' or 'mcb' based on header rows, or None."""
    if not all_rows:
        return None
    row0 = all_rows[0]
    if row0 and any(str(c).strip() == "Validity Date" for c in row0 if c):
        return "meezan"
    if len(all_rows) > 1:
        row1 = all_rows[1]
        if row1 and any(str(c).strip() == "Date" for c in row1 if c):
            return "mcb"
    return None


def _parse_meezan(all_rows):
    """Parse Meezan/MUFAP format: header row 0, blank row 1, data from row 2+."""
    rows, errors = [], []
    for i, row in enumerate(all_rows[2:], start=2):
        if not row or not row[3]:
            continue
        d = _parse_date(row[3])
        if d is None:
            errors.append(f"Row {i + 1}: could not parse date '{row[3]}'")
            continue
        price = _pick_price(row[4], row[6])
        if price is None:
            errors.append(f"Row {i + 1}: no valid price found")
            continue
        rows.append((d, price))
    return rows, errors


def _parse_mcb(all_rows):
    """Parse MCB format: title row 0, header row 1, data from row 2+."""
    rows, errors = [], []
    for i, row in enumerate(all_rows[2:], start=2):
        if not row or not row[0]:
            continue
        d = _parse_date(row[0])
        if d is None:
            errors.append(f"Row {i + 1}: could not parse date '{row[0]}'")
            continue
        price = _pick_price(row[3], row[1])
        if price is None:
            errors.append(f"Row {i + 1}: no valid price found")
            continue
        rows.append((d, price))
    return rows, errors


def parse_price_file(uploaded_file):
    """Parse an xlsx file and return (rows, errors)."""
    import openpyxl

    wb = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()

    fmt = _detect_format(all_rows)
    if fmt == "meezan":
        return _parse_meezan(all_rows)
    elif fmt == "mcb":
        return _parse_mcb(all_rows)
    else:
        return [], ["Unrecognized file format. Expected Meezan/MUFAP or MCB format."]


class PriceImportView(TemplateView):
    template_name = "investments/price_import.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", PriceImportForm())
        return context

    def post(self, request, *args, **kwargs):
        # Confirm step
        if request.POST.get("action") == "confirm":
            return self._handle_confirm(request)

        # Upload & preview step
        form = PriceImportForm(request.POST, request.FILES)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        instrument = form.cleaned_data["instrument"]
        uploaded_file = form.cleaned_data["file"]

        rows, errors = parse_price_file(uploaded_file)
        if not rows and errors:
            for err in errors:
                messages.error(request, err)
            return self.render_to_response(self.get_context_data(form=form))

        # Sort rows by date descending for display
        rows.sort(key=lambda r: r[0], reverse=True)

        preview_data = json.dumps(
            [[d.isoformat(), str(p)] for d, p in rows]
        )
        return self.render_to_response(
            self.get_context_data(
                form=form,
                preview_rows=rows,
                preview_data=preview_data,
                instrument=instrument,
                parse_errors=errors,
            )
        )

    def _handle_confirm(self, request):
        instrument_id = request.POST.get("instrument_id")
        preview_json = request.POST.get("preview_data", "[]")

        try:
            instrument = Instrument.objects.get(pk=instrument_id)
        except Instrument.DoesNotExist:
            messages.error(request, "Invalid instrument.")
            return redirect("investments:price_import")

        data = json.loads(preview_json)
        created = updated = 0
        for date_str, price_str in data:
            d = date.fromisoformat(date_str)
            p = Decimal(price_str)
            _, was_created = InstrumentPrice.objects.update_or_create(
                instrument=instrument,
                date=d,
                defaults={"price": p},
            )
            if was_created:
                created += 1
            else:
                updated += 1

        messages.success(
            request,
            f"Imported {created + updated} price(s) for {instrument.ticker}: "
            f"{created} created, {updated} updated.",
        )
        return redirect("investments:bulk_prices")


class PortfolioPerformanceView(TemplateView):
    template_name = "investments/portfolio_performance.html"

    RANGE_DAYS = {
        "1m": 30,
        "3m": 90,
        "6m": 180,
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # Parse range parameter
        range_param = self.request.GET.get("range", "6m")
        custom_start = self.request.GET.get("start")
        custom_end = self.request.GET.get("end")

        if custom_start and custom_end:
            try:
                start_date = date.fromisoformat(custom_start)
                end_date = date.fromisoformat(custom_end)
                active_range = "custom"
            except ValueError:
                start_date = today - timedelta(days=180)
                end_date = today
                active_range = "6m"
        elif range_param == "ytd":
            start_date = date(today.year, 1, 1)
            end_date = today
            active_range = "ytd"
        elif range_param == "all":
            inception = get_inception_date()
            start_date = inception if inception else today - timedelta(days=180)
            end_date = today
            active_range = "all"
        elif range_param in self.RANGE_DAYS:
            start_date = today - timedelta(days=self.RANGE_DAYS[range_param])
            end_date = today
            active_range = range_param
        else:
            start_date = today - timedelta(days=180)
            end_date = today
            active_range = "6m"

        # Compute series
        dates, portfolio_values, net_invested_values = compute_portfolio_series(
            start_date, end_date
        )

        # Summary stats
        current_value = portfolio_values[-1] if portfolio_values else Decimal("0")
        net_invested = net_invested_values[-1] if net_invested_values else Decimal("0")
        total_gl = current_value - net_invested
        total_gl_pct = (total_gl / net_invested * 100) if net_invested else Decimal("0")

        # Period change
        start_value = portfolio_values[0] if portfolio_values else Decimal("0")
        period_change = current_value - start_value
        period_change_pct = (
            (period_change / start_value * 100) if start_value else Decimal("0")
        )

        context.update(
            {
                "active_range": active_range,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "chart_dates": _json(dates),
                "chart_portfolio": _json(portfolio_values),
                "chart_net_invested": _json(net_invested_values),
                "current_value": current_value,
                "net_invested": net_invested,
                "total_gl": total_gl,
                "total_gl_pct": total_gl_pct,
                "period_change": period_change,
                "period_change_pct": period_change_pct,
            }
        )
        return context
