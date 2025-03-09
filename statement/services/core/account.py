from statement.services.base_service import BaseService
from statement.models import Account


class AccountService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Account."""
    model = Account
    user_field = 'user'
