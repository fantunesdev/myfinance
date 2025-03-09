from statement.services.base_service import BaseService
from statement.models import Currency


class CurrencyService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Currency."""
    model = Currency
