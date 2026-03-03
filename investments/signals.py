from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import InvestmentTransaction


@receiver(pre_save, sender=InvestmentTransaction)
def capture_old_investment_transaction(sender, instance, **kwargs):
    """Store old account ID before save so we can recalculate affected accounts."""
    if instance.pk:
        try:
            old = InvestmentTransaction.objects.get(pk=instance.pk)
            instance._old_account_id = old.account_id
        except InvestmentTransaction.DoesNotExist:
            instance._old_account_id = None
    else:
        instance._old_account_id = None


@receiver(post_save, sender=InvestmentTransaction)
def update_balances_on_investment_transaction_save(sender, instance, **kwargs):
    """Recalculate balances for all affected accounts after investment transaction save."""
    from accounts.models import Account

    account_ids = {instance.account_id}

    old_account_id = getattr(instance, "_old_account_id", None)
    if old_account_id:
        account_ids.add(old_account_id)

    for account in Account.objects.filter(id__in=account_ids):
        account.recalculate_balance()


@receiver(post_delete, sender=InvestmentTransaction)
def update_balances_on_investment_transaction_delete(sender, instance, **kwargs):
    """Recalculate balances for affected accounts after investment transaction delete."""
    from accounts.models import Account

    for account in Account.objects.filter(id=instance.account_id):
        account.recalculate_balance()
