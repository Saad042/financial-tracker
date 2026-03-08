from django import forms

from accounts.models import Account

from .models import ExchangeRate, Instrument, InvestmentTransaction

ACCEPT_XLSX = ".xlsx"

INPUT_CLASS = "w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-emerald-500 focus:ring-emerald-500"


class InstrumentForm(forms.ModelForm):
    class Meta:
        model = Instrument
        fields = [
            "name",
            "ticker",
            "instrument_type",
            "currency",
            "api_id",
            "platform",
            "notes",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "e.g., Pakistan State Oil"}
            ),
            "ticker": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "e.g., PSO, AAPL, BTC"}
            ),
            "instrument_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "currency": forms.Select(attrs={"class": INPUT_CLASS}),
            "api_id": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "e.g., bitcoin, ethereum, solana",
                }
            ),
            "platform": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "e.g., AKD Securities, Binance",
                }
            ),
            "notes": forms.Textarea(
                attrs={"class": INPUT_CLASS, "rows": 2, "placeholder": "Optional notes"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-emerald-600 focus:ring-emerald-500"
                }
            ),
        }


class InvestmentTransactionForm(forms.ModelForm):
    class Meta:
        model = InvestmentTransaction
        fields = [
            "date",
            "instrument",
            "transaction_type",
            "units",
            "price_per_unit",
            "total_amount",
            "brokerage_fee",
            "tax",
            "account",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
            "instrument": forms.Select(attrs={"class": INPUT_CLASS}),
            "transaction_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "units": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "0",
                    "step": "0.000001",
                    "min": "0",
                }
            ),
            "price_per_unit": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "0.00",
                    "step": "0.0001",
                    "min": "0",
                }
            ),
            "total_amount": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "brokerage_fee": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "tax": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "account": forms.Select(attrs={"class": INPUT_CLASS}),
            "notes": forms.Textarea(
                attrs={"class": INPUT_CLASS, "rows": 2, "placeholder": "Optional notes"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["instrument"].queryset = Instrument.objects.filter(user=user, is_active=True)
            self.fields["account"].queryset = Account.objects.filter(user=user)
        else:
            self.fields["instrument"].queryset = Instrument.objects.filter(is_active=True)
        self.fields["total_amount"].required = False
        self.fields["units"].required = False
        self.fields["price_per_unit"].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.transaction_type == InvestmentTransaction.DIVIDEND:
            instance.units = instance.units or 0
            instance.price_per_unit = instance.price_per_unit or 0
        else:
            instance.total_amount = instance.units * instance.price_per_unit
        if commit:
            instance.save()
        return instance


class PriceImportForm(forms.Form):
    instrument = forms.ModelChoiceField(
        queryset=Instrument.objects.none(),
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    file = forms.FileField(
        widget=forms.FileInput(attrs={"class": INPUT_CLASS, "accept": ACCEPT_XLSX}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["instrument"].queryset = Instrument.objects.filter(user=user, is_active=True)
        else:
            self.fields["instrument"].queryset = Instrument.objects.filter(is_active=True)


class ExchangeRateForm(forms.ModelForm):
    class Meta:
        model = ExchangeRate
        fields = ["from_currency", "to_currency", "date", "rate"]
        widgets = {
            "from_currency": forms.Select(
                attrs={"class": INPUT_CLASS},
                choices=[("USD", "USD"), ("PKR", "PKR")],
            ),
            "to_currency": forms.Select(
                attrs={"class": INPUT_CLASS},
                choices=[("PKR", "PKR"), ("USD", "USD")],
            ),
            "date": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
            "rate": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "e.g., 278.50",
                    "step": "0.0001",
                    "min": "0.0001",
                }
            ),
        }
