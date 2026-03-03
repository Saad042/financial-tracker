from django import forms

from .models import Tag

INPUT_CLASS = "w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-emerald-500 focus:ring-emerald-500"


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "tag_type", "color", "description"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "e.g., Grocery Store, Trip to Lahore",
            }),
            "tag_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "color": forms.TextInput(attrs={
                "type": "color",
                "class": "h-10 w-20 rounded-lg border-gray-300 dark:border-gray-600 cursor-pointer",
            }),
            "description": forms.Textarea(attrs={
                "class": INPUT_CLASS,
                "rows": 2,
                "placeholder": "Optional description",
            }),
        }
