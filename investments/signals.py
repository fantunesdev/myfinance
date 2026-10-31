from django.db.models.signals import post_save
from django.dispatch import receiver
from investments.services.transaction import InvestmentTransactionService
from statement.models import Transaction


@receiver(post_save, sender=Transaction)
def sync_investment_wallet_contribution(sender, instance, raw=False, **kwargs):
    if not raw:
        InvestmentTransactionService.sync_wallet_contribution_from_statement_transaction(instance)
