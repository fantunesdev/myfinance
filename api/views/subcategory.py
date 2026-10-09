from rest_framework import status
from rest_framework.response import Response

from api.serializers.subcategory import SubcategorySerializer
from api.views.base_view import BaseView
from statement.models import Subcategory
from statement.services.core.subcategory import SubcategoryService
from statement.views.core.subcategory import SubcategoryView as StatementView


class SubcategoryView(BaseView):
    """
    Classe que gerencia a view das subcategorias na API.
    """

    model = Subcategory
    service = SubcategoryService
    serializer = SubcategorySerializer
    statement_view = StatementView

    def list(self, request):
        user = self._set_user(request)
        instances = self.service.get_all(user)
        serializer = self._get_serializer(instances, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        user = self._set_user(request)
        instance = self.service.get_by_id(pk, user)
        serializer = self._get_serializer(instance, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
