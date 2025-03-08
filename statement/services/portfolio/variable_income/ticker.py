from statement.models import Ticker
from statement.services.base_service import BaseService

class TickerService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Ticker."""
    model = Ticker
    field_user = None
