from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import transaction_serializer
from api.services import invoice_services


class InvoiceByCardYearAndMonth(APIView):
    def get(self, request, card_id, year, month):
        invoice = invoice_services.get_invoice_by_year_and_month(
            card_id, year, month, request.user
        )
        serializer = transaction_serializer.TransactionSerializer(
            invoice, many=True
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
