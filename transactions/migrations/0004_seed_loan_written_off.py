from django.db import migrations


def seed_loan_written_off(apps, schema_editor):
    Category = apps.get_model("transactions", "Category")
    Category.objects.get_or_create(
        name="Loan Written Off",
        defaults={"type": "expense", "is_system": True},
    )


def remove_loan_written_off(apps, schema_editor):
    Category = apps.get_model("transactions", "Category")
    Category.objects.filter(name="Loan Written Off", is_system=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0003_transaction_recurring_rule"),
    ]

    operations = [
        migrations.RunPython(seed_loan_written_off, remove_loan_written_off),
    ]
