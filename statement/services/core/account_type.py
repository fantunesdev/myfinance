from statement.models import AccountType
from statement.services.base_service import BaseService


class AccountTypeService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo AccountType."""

    model = AccountType
