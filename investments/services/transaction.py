from investments.models import InvestmentTransaction
from investments.services.base import InvestmentBaseService


class InvestmentTransactionService(InvestmentBaseService):
    model = InvestmentTransaction
