from django import forms
from django.core.exceptions import ValidationError

from accounts.models import Account
from tags.models import Tag

from .models import Category, Transaction

INPUT_CLASS = "w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-emerald-500 focus:ring-emerald-500"


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["date", "type", "amount", "category", "account", "description"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
            "type": forms.Select(attrs={
                "class": INPUT_CLASS,
                "hx-get": "/transactions/category-options/",
                "hx-target": "#id_category",
                "hx-trigger": "change",
            }),
            "amount": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "0.00",
                "step": "0.01",
                "min": "0.01",
            }),
            "category": forms.Select(attrs={"class": INPUT_CLASS}),
            "account": forms.Select(attrs={"class": INPUT_CLASS}),
            "description": forms.Textarea(attrs={
                "class": INPUT_CLASS,
                "rows": 2,
                "placeholder": "Optional description",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show income/expense choices (not transfer)
        self.fields["type"].choices = [
            (Transaction.INCOME, "Income"),
            (Transaction.EXPENSE, "Expense"),
        ]
        # If editing, filter categories by type; otherwise show all non-transfer
        if self.instance.pk and self.instance.type:
            self.fields["category"].queryset = Category.objects.filter(
                type=self.instance.type
            )
        else:
            self.fields["category"].queryset = Category.objects.all()
        # Filter accounts by user
        if user:
            self.fields["account"].queryset = Account.objects.filter(user=user)

    def clean(self):
        cleaned_data = super().clean()
        txn_type = cleaned_data.get("type")
        category = cleaned_data.get("category")
        if category and txn_type and category.type != txn_type:
            raise ValidationError("Category type must match transaction type.")
        return cleaned_data


class TransactionFilterForm(forms.Form):
    """Filter form for the transaction list — plain Form, not ModelForm."""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Search description…",
        }),
    )
    type = forms.ChoiceField(
        required=False,
        choices=[("", "All types"), ("income", "Income"), ("expense", "Expense"), ("transfer", "Transfer")],
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    category = forms.ModelChoiceField(
        required=False,
        queryset=Category.objects.filter(parent__isnull=True),
        empty_label="All categories",
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    account = forms.ModelChoiceField(
        required=False,
        queryset=Account.objects.none(),
        empty_label="All accounts",
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
    )
    amount_min = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "placeholder": "Min", "step": "0.01", "min": "0"}),
    )
    amount_max = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS, "placeholder": "Max", "step": "0.01", "min": "0"}),
    )
    tag = forms.ModelChoiceField(
        required=False,
        queryset=Tag.objects.none(),
        empty_label="All tags",
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    tag_type = forms.ChoiceField(
        required=False,
        choices=[("", "All tag types"), ("place", "Places"), ("group", "Groups")],
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["account"].queryset = Account.objects.filter(user=user)
            self.fields["tag"].queryset = Tag.objects.filter(user=user, is_active=True)
        else:
            self.fields["account"].queryset = Account.objects.all()
            self.fields["tag"].queryset = Tag.objects.filter(is_active=True)


class TransferForm(forms.ModelForm):
    from_account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
        label="From Account",
    )
    to_account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
        label="To Account",
    )

    class Meta:
        model = Transaction
        fields = ["date", "amount", "description"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": INPUT_CLASS}),
            "amount": forms.NumberInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "0.00",
                "step": "0.01",
                "min": "0.01",
            }),
            "description": forms.Textarea(attrs={
                "class": INPUT_CLASS,
                "rows": 2,
                "placeholder": "Optional description",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            qs = Account.objects.filter(user=user)
        else:
            qs = Account.objects.all()
        self.fields["from_account"].queryset = qs
        self.fields["to_account"].queryset = qs

    def clean(self):
        cleaned_data = super().clean()
        from_account = cleaned_data.get("from_account")
        to_account = cleaned_data.get("to_account")
        if from_account and to_account and from_account == to_account:
            raise ValidationError("Cannot transfer to the same account.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.type = Transaction.TRANSFER
        instance.account = self.cleaned_data["from_account"]
        instance.transfer_to = self.cleaned_data["to_account"]
        if commit:
            instance.save()
        return instance
