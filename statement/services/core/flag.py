from statement.models import Flag
from statement.services.base_service import BaseService


class FlagService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Flag."""

    model = Flag
