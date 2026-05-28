import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from investments.services.transaction import InvestmentTransactionService
from statement.models import Transaction

logger = logging.getLogger('myfinance')


@receiver(post_save, sender=Transaction)
def sync_investment_wallet_contribution(sender, instance, **kwargs):
    try:
        InvestmentTransactionService.sync_wallet_contribution_from_statement_transaction(instance)
    except Exception as error:
        logger.warning(
            'Não foi possível sincronizar a transação financeira %s com investimentos: %s',
            getattr(instance, 'id', None),
            error,
        )
