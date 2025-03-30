from django.http import Http404
from rest_framework.decorators import action
from rest_framework import status

from api.views.base_view import BaseView
from api.serializers.category import CategorySerializer
from api.serializers.subcategory import SubcategorySerializer
from statement.services.core.category import CategoryService
from statement.views.core.category import CategoryView as StatementView

from rest_framework.response import Response


class CategoryView(BaseView):
    """
    Classe que gerencia a view das categorias na API.
    """

    class_has_user = True
    service = CategoryService
    serializer = CategorySerializer
    statement_view = StatementView

    @action(detail=False, methods=['get'], url_path='type/(?P<type>\w+)')
    def get_by_type(self, request, type=None):
        """
        Obtém as Categorias de um tipo específico.
        
        :type: o tipo da categoria (por exemplo, 'entrada' ou 'saida')
        """
        categories = self.service.get_by_type(type)
        if not categories:
            return Response({"detail": "Categorias não encontradas."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer(categories, many=True)
        return Response({'categories': serializer.data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='subcategories')
    def get_subcategories(self, request, pk=None):
        """
        Obtém as subcategorias de uma categoria específica.
        
        :category_id: o ID da categoria à qual as subcategorias pertencem.
        """
        category = self.service.get_by_id(pk)
        subcategories = subcategories = category.subcategories.all()
        if not subcategories:
            return Response({"detail": "Subcategorias não encontradas."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SubcategorySerializer(subcategories, many=True)
        return Response({'subcategories': serializer.data}, status=status.HTTP_200_OK)
