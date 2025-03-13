from statement.models import Card
from statement.services.base_service import BaseService


class CardService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Card."""

    model = Card
    user_field = 'user'
