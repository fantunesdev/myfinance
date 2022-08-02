from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import movimentacao_serializer
from balanco.services import movimentacao_service


class MovimentacaoDetails(APIView):
    def get(self, request, ano, mes):
        movimentacoes = movimentacao_service.listar_movimentacoes_ano_mes(ano, mes, request.user)
        serializer = movimentacao_serializer.MovimentacaoSerializer(movimentacoes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
