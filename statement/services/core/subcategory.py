from statement.services.base_service import BaseService
from statement.models import Subcategory


class SubcategoryService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Subcategory."""
    model = Subcategory

    @staticmethod
    def get_by_category(category_id):
        """
        Obtém as subcategorias de uma categoria
        """
        return Subcategory.objects.select_related('category').filter(category=category_id)
