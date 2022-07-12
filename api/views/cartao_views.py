from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import cartao_serializer
from balanco.services import cartao_service


class CartaoList(APIView):
    def get(self, request):
        cartoes = cartao_service.listar_cartoes(request.user)
        serializer = cartao_serializer.CartaoSerializer(cartoes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CartaoDetails(APIView):
    def get(self, request, cartao_id):
        cartao = cartao_service.listar_cartao_id(cartao_id, request.user)
        serializer = cartao_serializer.CartaoSerializer(cartao)
        return Response(serializer.data, status=status.HTTP_200_OK)
