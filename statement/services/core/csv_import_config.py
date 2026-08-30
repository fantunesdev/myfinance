from statement.models import CSVImportConfig
from statement.services.base_service import BaseService


class CSVImportConfigService(BaseService):
    """Serviço para gerenciar configurações de importação CSV."""

    model = CSVImportConfig
    user_field = 'user'
