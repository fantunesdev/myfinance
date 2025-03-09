from statement.services.base_service import BaseService
from statement.models import Subcategory


class SubcategoryService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Subcategory."""
    model = Subcategory

    def get_by_category(self, category_id):
        return Subcategory.objects.select_related('category').filter(category=category_id)
