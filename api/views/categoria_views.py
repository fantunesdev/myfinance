from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import categoria_serializer
from balanco.services import categoria_service
from api.services import categoria_services as categoria_services_api


class CategoriasList(APIView):
    def get(self, request):
        categorias = categoria_service.listar_categorias(request.user)
        serializer = categoria_serializer.CategoriaSerializer(categorias, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CategoriasDetails(APIView):
    def get(self, request, categoria_id):
        categoria = categoria_service.listar_categoria_id(categoria_id, request.user)
        serializer = categoria_serializer.CategoriaSerializer(categoria)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CategoriasTipo(APIView):
    def get(self, request, tipo):
        categorias = categoria_services_api.listar_categoria_tipo(tipo, request.user)
        serializer = categoria_serializer.CategoriaSerializer(categorias, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
