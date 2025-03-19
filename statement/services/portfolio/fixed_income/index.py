from statement.models import Index
from statement.services.base_service import BaseService


class IndexService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Index."""

    model = Index
    user_field = 'user'
