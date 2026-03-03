from decimal import Decimal

from django.db import models
from django.utils import timezone


class Instrument(models.Model):
    PSX_STOCK = "psx_stock"
    PK_MUTUAL_FUND = "pk_mutual_fund"
    US_STOCK = "us_stock"
    CRYPTO = "crypto"
    INTERNATIONAL_FUND = "international_fund"
    INSTRUMENT_TYPE_CHOICES = [
        (PSX_STOCK, "PSX Stock"),
        (PK_MUTUAL_FUND, "Mutual Fund (PK)"),
        (US_STOCK, "US Stock"),
        (CRYPTO, "Crypto"),
        (INTERNATIONAL_FUND, "International Fund"),
    ]

    PKR = "PKR"
    USD = "USD"
    CURRENCY_CHOICES = [
        (PKR, "PKR"),
        (USD, "USD"),
    ]

    name = models.CharField(max_length=200)
    ticker = models.CharField(max_length=20, unique=True)
    instrument_type = models.CharField(max_length=20, choices=INSTRUMENT_TYPE_CHOICES)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    api_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="CoinGecko coin ID (e.g., bitcoin, ethereum, solana)",
    )
    platform = models.CharField(max_length=200, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.ticker} - {self.name}"

    @property
    def latest_price(self):
        """Most recent price entry for this instrument."""
        price_obj = self.prices.order_by("-date").first()
        return price_obj.price if price_obj else None

    @property
    def latest_price_date(self):
        price_obj = self.prices.order_by("-date").first()
        return price_obj.date if price_obj else None

    @property
    def current_holdings(self):
        """Net units held: total bought + reinvested - total sold."""
        buys = (
            self.transactions.filter(
                transaction_type__in=[InvestmentTransaction.BUY, InvestmentTransaction.REINVESTMENT]
            )
            .aggregate(total=models.Sum("units"))["total"]
            or Decimal("0")
        )
        sells = (
            self.transactions.filter(transaction_type=InvestmentTransaction.SELL)
            .aggregate(total=models.Sum("units"))["total"]
            or Decimal("0")
        )
        return buys - sells

    @property
    def total_units_bought(self):
        return (
            self.transactions.filter(
                transaction_type__in=[InvestmentTransaction.BUY, InvestmentTransaction.REINVESTMENT]
            )
            .aggregate(total=models.Sum("units"))["total"]
            or Decimal("0")
        )

    @property
    def total_cost_basis(self):
        """Total cost of all buys and reinvestments including fees and tax."""
        from django.db.models import F, Sum

        result = (
            self.transactions.filter(
                transaction_type__in=[InvestmentTransaction.BUY, InvestmentTransaction.REINVESTMENT]
            )
            .aggregate(total=Sum(F("total_amount") + F("brokerage_fee") + F("tax")))
        )
        return result["total"] or Decimal("0")

    @property
    def net_cash_invested(self):
        """Net cash deployed: buy costs - sell proceeds - dividend income."""
        from django.db.models import F, Sum

        buys = (
            self.transactions.filter(transaction_type=InvestmentTransaction.BUY)
            .aggregate(total=Sum(F("total_amount") + F("brokerage_fee") + F("tax")))
        )["total"] or Decimal("0")
        cash_returned = (
            self.transactions.filter(
                transaction_type__in=[
                    InvestmentTransaction.SELL,
                    InvestmentTransaction.DIVIDEND,
                ]
            )
            .aggregate(total=Sum(F("total_amount") - F("brokerage_fee") - F("tax")))
        )["total"] or Decimal("0")
        return buys - cash_returned

    @property
    def total_reinvested(self):
        """Total value of dividend reinvestments."""
        return (
            self.transactions.filter(transaction_type=InvestmentTransaction.REINVESTMENT)
            .aggregate(total=models.Sum("total_amount"))["total"]
            or Decimal("0")
        )

    @property
    def total_dividends(self):
        """Total cash dividends received (net of fees and tax)."""
        from django.db.models import F, Sum

        result = (
            self.transactions.filter(transaction_type=InvestmentTransaction.DIVIDEND)
            .aggregate(total=Sum(F("total_amount") - F("brokerage_fee") - F("tax")))
        )
        return result["total"] or Decimal("0")

    @property
    def average_cost(self):
        """Average cost per unit (cost basis / units bought)."""
        units = self.total_units_bought
        if units == 0:
            return Decimal("0")
        return self.total_cost_basis / units

    @property
    def current_value(self):
        """Current value of holdings at latest price."""
        price = self.latest_price
        if price is None:
            return Decimal("0")
        return self.current_holdings * price

    @property
    def unrealized_gain_loss(self):
        """Unrealized gain/loss on current holdings."""
        holdings = self.current_holdings
        if holdings == 0:
            return Decimal("0")
        return self.current_value - (holdings * self.average_cost)

    @property
    def unrealized_gain_loss_percent(self):
        """Unrealized gain/loss as percentage of cost basis for current holdings."""
        holdings = self.current_holdings
        if holdings == 0:
            return Decimal("0")
        cost = holdings * self.average_cost
        if cost == 0:
            return Decimal("0")
        return (self.unrealized_gain_loss / cost) * 100

    @property
    def realized_gain_loss(self):
        """Total realized gain/loss from all sells."""
        from django.db.models import F, Sum

        sells = self.transactions.filter(transaction_type=InvestmentTransaction.SELL)
        if not sells.exists():
            return Decimal("0")
        # Sell proceeds = total_amount - brokerage_fee - tax
        proceeds = (
            sells.aggregate(
                total=Sum(F("total_amount") - F("brokerage_fee") - F("tax"))
            )["total"]
            or Decimal("0")
        )
        # Cost of sold units at average cost at time of sale
        # Simplified: use overall average cost × total units sold
        units_sold = (
            sells.aggregate(total=Sum("units"))["total"] or Decimal("0")
        )
        cost_of_sold = units_sold * self.average_cost
        return proceeds - cost_of_sold


class InstrumentPrice(models.Model):
    instrument = models.ForeignKey(
        Instrument, on_delete=models.CASCADE, related_name="prices"
    )
    date = models.DateField()
    price = models.DecimalField(max_digits=14, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        unique_together = [("instrument", "date")]

    def __str__(self):
        return f"{self.instrument.ticker} @ {self.price} on {self.date}"

    @classmethod
    def get_price(cls, instrument, target_date):
        """Get price for instrument on or before the given date (last known price)."""
        price_obj = (
            cls.objects.filter(instrument=instrument, date__lte=target_date)
            .order_by("-date")
            .first()
        )
        return price_obj.price if price_obj else None


class InvestmentTransaction(models.Model):
    BUY = "buy"
    SELL = "sell"
    REINVESTMENT = "reinvestment"
    DIVIDEND = "dividend"
    TRANSACTION_TYPE_CHOICES = [
        (BUY, "Buy"),
        (SELL, "Sell"),
        (REINVESTMENT, "Reinvestment"),
        (DIVIDEND, "Dividend"),
    ]

    date = models.DateField(default=timezone.now)
    instrument = models.ForeignKey(
        Instrument, on_delete=models.PROTECT, related_name="transactions"
    )
    transaction_type = models.CharField(max_length=12, choices=TRANSACTION_TYPE_CHOICES)
    units = models.DecimalField(max_digits=14, decimal_places=6)
    price_per_unit = models.DecimalField(max_digits=14, decimal_places=4)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    brokerage_fee = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0")
    )
    tax = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="investment_transactions",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.units} {self.instrument.ticker}"

    @property
    def net_amount(self):
        """Net cash impact: buy deducts, sell/dividend credits, reinvestment zero."""
        if self.transaction_type == self.REINVESTMENT:
            return Decimal("0")
        if self.transaction_type == self.BUY:
            return self.total_amount + self.brokerage_fee + self.tax
        else:  # sell or dividend
            return self.total_amount - self.brokerage_fee - self.tax


class ExchangeRate(models.Model):
    from_currency = models.CharField(max_length=3)
    to_currency = models.CharField(max_length=3)
    date = models.DateField()
    rate = models.DecimalField(max_digits=14, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        unique_together = [("from_currency", "to_currency", "date")]

    def __str__(self):
        return f"1 {self.from_currency} = {self.rate} {self.to_currency} on {self.date}"

    @classmethod
    def get_rate(cls, from_currency, to_currency, target_date):
        """Get exchange rate on or before the given date (last known rate)."""
        if from_currency == to_currency:
            return Decimal("1")
        rate_obj = (
            cls.objects.filter(
                from_currency=from_currency,
                to_currency=to_currency,
                date__lte=target_date,
            )
            .order_by("-date")
            .first()
        )
        return rate_obj.rate if rate_obj else None
