"""Data migration: assign all existing rows to the first superuser."""

from django.db import migrations


def assign_default_user(apps, schema_editor):
    User = apps.get_model("auth", "User")
    admin = User.objects.filter(is_superuser=True).order_by("pk").first()
    if admin is None:
        admin = User.objects.order_by("pk").first()
    if admin is None:
        # No users exist — nothing to migrate
        return

    for model_path in [
        ("accounts", "Account"),
        ("transactions", "Transaction"),
        ("loans", "Loan"),
        ("recurring", "RecurringRule"),
        ("budgets", "Budget"),
        ("tags", "Tag"),
        ("investments", "Instrument"),
        ("investments", "InvestmentTransaction"),
    ]:
        Model = apps.get_model(*model_path)
        Model.objects.filter(user__isnull=True).update(user=admin)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_account_user"),
        ("transactions", "0005_transaction_user"),
        ("loans", "0004_loan_user"),
        ("recurring", "0002_recurringrule_user"),
        ("budgets", "0002_remove_budget_unique_budget_category_month_and_more"),
        ("tags", "0002_remove_tag_unique_tag_name_type_tag_user_and_more"),
        ("investments", "0006_instrument_user_investmenttransaction_user_and_more"),
        ("core", "__first__"),
    ]

    operations = [
        migrations.RunPython(assign_default_user, migrations.RunPython.noop),
    ]
