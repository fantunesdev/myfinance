from statement.services.base_service import BaseService
from statement.models import AccountType


class AccountTypeService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo AccountType."""
    model = AccountType
