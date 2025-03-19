from statement.models import FixedIncomeSecurity
from statement.services.base_service import BaseService


class FixedIncomeSecurityService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo FixedIncomeSecurity."""

    model = FixedIncomeSecurity
    user_field = 'user'
