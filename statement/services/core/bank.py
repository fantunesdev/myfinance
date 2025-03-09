from statement.services.base_service import BaseService
from statement.models import Bank


class BankService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Bank."""
    model = Bank
