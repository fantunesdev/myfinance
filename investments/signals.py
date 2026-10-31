from django.db.models.signals import (
    post_delete,
    post_save,
    pre_delete,
    pre_save,
)
from django.dispatch import receiver

from investments.events import mark_changed
from investments.models import Asset, Broker, Investment, InvestmentTransaction
from investments.services.transaction import InvestmentTransactionService
from statement.models import Transaction


@receiver(pre_save, sender=Transaction)
def remember_statement_before_investment_sync(
    sender, instance, raw=False, using=None, **kwargs
):
    if raw:
        return
    # Transaction.save already wraps the statement and its signals in atomic().
    # Use the same owner lock as investment writes before reading old funding.
    InvestmentTransactionService.lock_user(instance.user)
    instance.__dict__.pop('_removed_investment_contribution_for', None)
    instance._investment_previous_statement = (
        sender.objects.using(using)
        .select_related('subcategory')
        .filter(pk=instance.pk)
        .first()
        if instance.pk
        else None
    )


@receiver(post_save, sender=Transaction)
def sync_investment_wallet_contribution(
    sender,
    instance,
    raw=False,
    created=False,
    using=None,
    update_fields=None,
    **kwargs
):
    if raw:
        return
    try:
        # A partial save can leave unsaved financial changes on the Python
        # instance. Synchronize only the values actually persisted to the bank.
        current = (
            sender.objects.using(using)
            .select_related('subcategory', 'user')
            .get(pk=instance.pk)
        )
        InvestmentTransactionService.sync_wallet_contribution_from_statement_transaction(
            current,
            previous=getattr(instance, '_investment_previous_statement', None),
            created=created,
        )
    finally:
        instance.__dict__.pop('_investment_previous_statement', None)


@receiver(pre_delete, sender=Transaction)
def protect_unlinked_investment_statement(sender, instance, **kwargs):
    service = InvestmentTransactionService
    if not service._should_sync_statement_transaction(instance):
        return
    if (
        getattr(instance, '_removed_investment_contribution_for', None)
        == instance.pk
    ):
        return
    service.lock_user(instance.user)
    if not service.model.objects.filter(
        statement_transaction_id=instance.pk
    ).exists():
        raise service.unlinked_statement_error(instance)


@receiver(post_save, sender=Asset)
@receiver(post_save, sender=Broker)
@receiver(post_save, sender=Investment)
@receiver(post_save, sender=InvestmentTransaction)
@receiver(post_delete, sender=Asset)
@receiver(post_delete, sender=Broker)
@receiver(post_delete, sender=Investment)
@receiver(post_delete, sender=InvestmentTransaction)
def invalidate_investment_dashboard(sender, instance, raw=False, **kwargs):
    if not raw:
        mark_changed(instance.user_id)
