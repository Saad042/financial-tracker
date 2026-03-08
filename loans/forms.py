from django import forms
from django.utils import timezone

from accounts.models import Account

from .models import Loan

INPUT_CLASS = "w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-emerald-500 focus:ring-emerald-500"


class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ["borrower_name", "amount", "date_lent", "expected_return", "account", "notes"]
        widgets = {
            "borrower_name": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "e.g., Ahmed, Ali",
            }),
            "amount": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "0.00",
                "step": "0.01",
                "min": "0.01",
            }),
            "date_lent": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
            "expected_return": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
            "account": forms.Select(attrs={"class": INPUT_CLASS}),
            "notes": forms.Textarea(attrs={
                "class": INPUT_CLASS,
                "rows": 2,
                "placeholder": "Optional notes",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["account"].queryset = Account.objects.filter(user=user)


class LoanRepaymentForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "0.00",
            "step": "0.01",
            "min": "0.01",
        }),
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
        label="Date",
    )
    account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
        label="Received Into Account",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": INPUT_CLASS,
            "rows": 2,
            "placeholder": "Optional notes",
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get("date"):
            self.initial["date"] = timezone.now().date()
        if user:
            self.fields["account"].queryset = Account.objects.filter(user=user)
        else:
            self.fields["account"].queryset = Account.objects.all()
