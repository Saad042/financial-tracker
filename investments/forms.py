from django import forms

from .models import Investment

INPUT_CLASS = "w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-emerald-500 focus:ring-emerald-500"


class InvestmentForm(forms.ModelForm):
    class Meta:
        model = Investment
        fields = ["name", "amount", "date", "platform", "account", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "e.g., Naya Pakistan Certificates",
            }),
            "amount": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "0.00",
                "step": "0.01",
                "min": "0.01",
            }),
            "date": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
            "platform": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "e.g., Meezan Bank, Roshan Digital",
            }),
            "account": forms.Select(attrs={"class": INPUT_CLASS}),
            "notes": forms.Textarea(attrs={
                "class": INPUT_CLASS,
                "rows": 2,
                "placeholder": "Optional notes",
            }),
        }
