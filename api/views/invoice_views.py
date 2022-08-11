from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import transaction_serializer
from balanco.services import fatura_service


class InvoiceYearMonth(APIView):
    def get(self, request, cartao, ano, mes):
        invoice = fatura_service.listar_fatura_ano_mes(ano, mes, cartao, request.user)
        serializer = movimentacao_serializer.MovimentacaoSerializer(invoice, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
