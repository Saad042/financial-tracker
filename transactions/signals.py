from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Transaction


@receiver(pre_save, sender=Transaction)
def capture_old_transaction(sender, instance, **kwargs):
    """Store old state before save so we can recalculate affected accounts."""
    if instance.pk:
        try:
            old = Transaction.objects.get(pk=instance.pk)
            instance._old_account_id = old.account_id
            instance._old_transfer_to_id = old.transfer_to_id
        except Transaction.DoesNotExist:
            instance._old_account_id = None
            instance._old_transfer_to_id = None
    else:
        instance._old_account_id = None
        instance._old_transfer_to_id = None


@receiver(post_save, sender=Transaction)
def update_balances_on_save(sender, instance, **kwargs):
    """Recalculate balances for all affected accounts after save."""
    from accounts.models import Account

    account_ids = set()
    account_ids.add(instance.account_id)
    if instance.transfer_to_id:
        account_ids.add(instance.transfer_to_id)

    old_account_id = getattr(instance, "_old_account_id", None)
    old_transfer_to_id = getattr(instance, "_old_transfer_to_id", None)
    if old_account_id:
        account_ids.add(old_account_id)
    if old_transfer_to_id:
        account_ids.add(old_transfer_to_id)

    for account in Account.objects.filter(id__in=account_ids):
        account.recalculate_balance()


@receiver(post_delete, sender=Transaction)
def update_balances_on_delete(sender, instance, **kwargs):
    """Recalculate balances for affected accounts after delete."""
    from accounts.models import Account

    account_ids = {instance.account_id}
    if instance.transfer_to_id:
        account_ids.add(instance.transfer_to_id)

    for account in Account.objects.filter(id__in=account_ids):
        account.recalculate_balance()
