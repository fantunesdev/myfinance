from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import subcategoria_serializer
from api.services import subcategoria_services as subcategoria_service_api
from balanco.services import subcategoria_service


class SubcategoriaList(APIView):
    def get(self, request):
        subcategorias = subcategoria_service.listar_subcategorias(request.user)
        serializer = subcategoria_serializer.SubcategoriaSerializer(subcategorias, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SubcategoriaCategoria(APIView):
    def get(self, request, categoria_id):
        subcategorias = subcategoria_service_api.listar_subcategoria_categoria(categoria_id, request.user)
        serializer = subcategoria_serializer.SubcategoriaSerializer(subcategorias, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
