from statement.models import Account
from statement.services.base_service import BaseService


class AccountService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Account."""

    model = Account
    user_field = 'user'
