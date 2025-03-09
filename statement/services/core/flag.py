from statement.services.base_service import BaseService
from statement.models import Flag


class FlagService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Flag."""
    model = Flag
