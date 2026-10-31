from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from investments.events import mark_changed
from investments.models import Asset, Broker, Investment, InvestmentTransaction
from investments.services.transaction import InvestmentTransactionService
from statement.models import Transaction


@receiver(post_save, sender=Transaction)
def sync_investment_wallet_contribution(sender, instance, raw=False, **kwargs):
    if not raw:
        InvestmentTransactionService.sync_wallet_contribution_from_statement_transaction(
            instance
        )


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
