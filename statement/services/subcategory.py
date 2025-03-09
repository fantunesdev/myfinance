from statement.services.base_service import BaseService
from statement.models import Subcategory


class SubcategoryService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Subcategory."""
    model = Subcategory
