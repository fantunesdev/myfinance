from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.serializers.base_serializer import BaseSerializer
from api.serializers.subcategory import SubcategorySerializer
from api.views.base_view import BaseView
from api.permissions import AuthenticatedReadStaffWrite
from statement.models import Category
from statement.services.core.category import CategoryService
from statement.services.core.subcategory import SubcategoryService
from statement.views.core.category import CategoryView as StatementView


class CategoryView(BaseView):
    """
    Classe que gerencia a view das categorias na API.
    """

    permission_classes = [AuthenticatedReadStaffWrite]

    model = Category
    service = CategoryService
    serializer = BaseSerializer
    statement_view = StatementView

    @action(detail=False, methods=['get'], url_path=r'type/(?P<type>\w+)')
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
        if request.query_params.get('available_for_entry') == '1':
            subcategories = SubcategoryService.available_for_entry(request.user).filter(category=category)
            serializer = SubcategorySerializer(subcategories, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        subcategories = category.subcategories.all()
        if not subcategories:
            return Response({'detail': 'Subcategorias não encontradas.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = SubcategorySerializer(subcategories, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
