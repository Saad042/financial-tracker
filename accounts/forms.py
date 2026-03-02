from django import forms

from .models import Account


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ["name", "account_type", "initial_balance"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full rounded-lg border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500",
                "placeholder": "e.g., HBL Savings, Cash",
            }),
            "account_type": forms.Select(attrs={
                "class": "w-full rounded-lg border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500",
            }),
            "initial_balance": forms.NumberInput(attrs={
                "class": "w-full rounded-lg border-gray-300 shadow-sm focus:border-emerald-500 focus:ring-emerald-500",
                "placeholder": "0.00",
                "step": "0.01",
            }),
        }
