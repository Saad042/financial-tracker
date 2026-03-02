from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Loan


@receiver(pre_save, sender=Loan)
def capture_old_loan(sender, instance, **kwargs):
    """Store old account ID before save so we can recalculate affected accounts."""
    if instance.pk:
        try:
            old = Loan.objects.get(pk=instance.pk)
            instance._old_account_id = old.account_id
        except Loan.DoesNotExist:
            instance._old_account_id = None
    else:
        instance._old_account_id = None


@receiver(post_save, sender=Loan)
def update_balances_on_loan_save(sender, instance, **kwargs):
    """Recalculate balances for all affected accounts after loan save."""
    from accounts.models import Account

    account_ids = {instance.account_id}

    old_account_id = getattr(instance, "_old_account_id", None)
    if old_account_id:
        account_ids.add(old_account_id)

    for account in Account.objects.filter(id__in=account_ids):
        account.recalculate_balance()


@receiver(post_delete, sender=Loan)
def update_balances_on_loan_delete(sender, instance, **kwargs):
    """Recalculate balances for affected accounts after loan delete."""
    from accounts.models import Account

    for account in Account.objects.filter(id=instance.account_id):
        account.recalculate_balance()
