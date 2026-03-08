from django import forms
from django.core.exceptions import ValidationError

from accounts.models import Account

from .models import RecurringRule

INPUT_CLASS = "w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-emerald-500 focus:ring-emerald-500"


class RecurringRuleForm(forms.ModelForm):
    class Meta:
        model = RecurringRule
        fields = ["name", "amount", "type", "category", "account", "frequency", "day_of_month", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "e.g., Monthly Salary, Netflix",
            }),
            "amount": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "0.00",
                "step": "0.01",
                "min": "0.01",
            }),
            "type": forms.Select(attrs={
                "class": INPUT_CLASS,
                "hx-get": "/transactions/category-options/",
                "hx-target": "#id_category",
                "hx-trigger": "change",
            }),
            "category": forms.Select(attrs={"class": INPUT_CLASS}),
            "account": forms.Select(attrs={"class": INPUT_CLASS}),
            "frequency": forms.Select(attrs={"class": INPUT_CLASS}),
            "day_of_month": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "min": "1",
                "max": "28",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-emerald-600 focus:ring-emerald-500",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from transactions.models import Category

        if self.instance.pk and self.instance.type:
            self.fields["category"].queryset = Category.objects.filter(
                type=self.instance.type
            )
        else:
            self.fields["category"].queryset = Category.objects.all()
        if user:
            self.fields["account"].queryset = Account.objects.filter(user=user)

    def clean(self):
        cleaned_data = super().clean()
        rule_type = cleaned_data.get("type")
        category = cleaned_data.get("category")
        if category and rule_type and category.type != rule_type:
            raise ValidationError("Category type must match rule type.")
        return cleaned_data
