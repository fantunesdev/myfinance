from statement.models import Currency
from statement.services.base_service import BaseService


class CurrencyService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Currency."""

    model = Currency
