from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.serializers.base_serializer import BaseSerializer
from api.views.base_view import BaseView
from statement.models import Category
from statement.services.core.category import CategoryService
from statement.views.core.category import CategoryView as StatementView


class CategoryView(BaseView):
    """
    Classe que gerencia a view das categorias na API.
    """

    model = Category
    service = CategoryService
    serializer = BaseSerializer
    statement_view = StatementView

    @action(detail=False, methods=['get'], url_path='type/(?P<type>\w+)')
    def get_by_type(self, request, type=None):
        """
        Obtém as Categorias de um tipo específico.

        :type: o tipo da categoria (por exemplo, 'entrada' ou 'saida')
        """
        categories = self.service.get_by_type(type)
        if not categories:
            return Response({'detail': 'Categorias não encontradas.'}, status=status.HTTP_404_NOT_FOUND)
        return self._serialize_and_return(categories)

    @action(detail=True, methods=['get'], url_path='subcategories')
    def get_subcategories(self, request, pk=None):
        """
        Obtém as subcategorias de uma categoria específica.

        :category_id: o ID da categoria à qual as subcategorias pertencem.
        """
        category = self.service.get_by_id(pk)
        subcategories = subcategories = category.subcategories.all()
        if not subcategories:
            return Response({'detail': 'Subcategorias não encontradas.'}, status=status.HTTP_404_NOT_FOUND)
        return self._serialize_and_return(subcategories)
