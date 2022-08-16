from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import transaction_serializer
from api.services import transaction_services


class TransactionByYearAndMonth(APIView):
    def get(self, request, year, month):
        transactions = transaction_services.get_transactions_by_year_and_month(year, month, request.user)
        serializer = transaction_serializer.TransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TransactionYear(APIView):
    def get(self, request, year):
        transactions = transaction_services.get_transactions_by_year(year, request.user)
        serializer = transaction_serializer.TransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
