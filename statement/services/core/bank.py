from statement.models import Bank
from statement.services.base_service import BaseService


class BankService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Bank."""

    model = Bank
