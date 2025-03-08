from statement.models import Sector
from statement.services.base_service import BaseService

class SectorService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Sector."""
    model = Sector
    field_user = None
