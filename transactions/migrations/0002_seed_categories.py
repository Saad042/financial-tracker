from django.db import migrations


EXPENSE_CATEGORIES = {
    "Commuting": ["Rideshare", "Fuel", "Car Maintenance", "Parking & Tolls"],
    "Food": ["Dining Out", "Groceries"],
    "Charity": [],
    "Subscriptions": [],
    "General / Miscellaneous": [
        "Clothing",
        "Electronics",
        "Medical",
        "Home",
        "Gifts",
        "Personal Care",
    ],
}

INCOME_CATEGORIES = [
    "Salary",
    "Freelance / Side Income",
    "Loan Repayment Received",
    "Other",
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model("transactions", "Category")

    # Expense categories with sub-categories
    for parent_name, children in EXPENSE_CATEGORIES.items():
        parent = Category.objects.create(
            name=parent_name, type="expense", is_system=True
        )
        for child_name in children:
            Category.objects.create(
                name=child_name, type="expense", parent=parent, is_system=True
            )

    # Income categories (flat)
    for name in INCOME_CATEGORIES:
        Category.objects.create(name=name, type="income", is_system=True)


def remove_seed_categories(apps, schema_editor):
    Category = apps.get_model("transactions", "Category")
    Category.objects.filter(is_system=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, remove_seed_categories),
    ]
